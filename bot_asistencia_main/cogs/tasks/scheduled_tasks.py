"""Tareas programadas del bot: métricas, sincronización, reportes automáticos"""

import discord
from discord.ext import commands, tasks
import aiohttp
import datetime
import logging
import database as db
from utils import LIMA_TZ, format_timedelta, es_domingo
from bot.config.constants import (
    HORA_FIN_RECUPERACION,
    HORA_GRACIA_RECUPERACION,
    HORA_SALIDA_OFICIAL,
    HORA_GRACIA_SALIDA,
)


class BotMetrics:
    """Clase para rastrear métricas del bot"""
    def __init__(self):
        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        self.events_processed_today = 0
        self.last_reset_day = self.start_time.day

    def increment_event_count(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        if now.day != self.last_reset_day:
            self.events_processed_today = 0
            self.last_reset_day = now.day
        self.events_processed_today += 1

    def get_uptime(self):
        return datetime.datetime.now(datetime.timezone.utc) - self.start_time


async def update_bot_status(bot, status: str):
    """Envía una actualización de estado al backend."""
    backend_url = getattr(bot, '_backend_url', None)
    backend_key = getattr(bot, '_backend_api_key', None)
    if not backend_url or not backend_key:
        return

    headers = {"Authorization": f"Bearer {backend_key}"}
    payload = {"status": status}
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.post(f"{backend_url}/status/", json=payload) as response:
                if response.status == 200:
                    logging.info(f"Estado del bot actualizado a '{status}' en el backend.")
                else:
                    logging.error(f"Error al actualizar el estado del bot: {response.status}")
        except aiohttp.ClientConnectorError as e:
            logging.error(f"No se pudo conectar al backend para actualizar estado: {e}")


class ScheduledTasks(commands.Cog):
    """Cog para tareas programadas: métricas, sincronización y reportes"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.metrics = BotMetrics()
        bot.metrics = self.metrics

    def cog_unload(self):
        self.send_metrics_to_backend.cancel()
        self.sync_google_sheets_task.cancel()
        self.auto_reporte_diario_task.cancel()
        self.auto_registro_horario_task.cancel()
        self.auto_cierre_recuperacion.cancel()
        self.auto_salida_asistencia.cancel()

    # --- Eventos para conteo de métricas ---

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        self.metrics.increment_event_count()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        self.metrics.increment_event_count()

    # --- Tarea: Enviar Métricas al Backend (cada 1 min) ---

    @tasks.loop(minutes=1)
    async def send_metrics_to_backend(self):
        backend_url = getattr(self.bot, '_backend_url', None)
        backend_key = getattr(self.bot, '_backend_api_key', None)
        if not backend_url or not backend_key:
            return

        uptime_delta = self.metrics.get_uptime()
        now_lima = datetime.datetime.now()

        payload = {
            "resumen": {
                "servidores_conectados": len(self.bot.guilds),
                "eventos_procesados_hoy": self.metrics.events_processed_today,
                "uptime_porcentaje": 99.9,
                "ultima_sincronizacion": now_lima.isoformat()
            },
            "estado": {
                "status": "online",
                "uptime_dias": uptime_delta.days,
                "latencia_ms": round(self.bot.latency * 1000, 2),
                "ultima_conexion": now_lima.isoformat()
            },
            "servers": [
                {
                    "server_id": guild.id,
                    "server_name": guild.name,
                    "miembros": guild.member_count,
                    "canales": len(guild.channels),
                    "status": "conectado"
                } for guild in self.bot.guilds
            ]
        }

        headers = {
            "Authorization": f"Bearer {backend_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.post(f"{backend_url}/metrics/", json=payload) as response:
                    if response.status == 200:
                        logging.info("Métricas enviadas exitosamente al backend.")
                    else:
                        logging.error(f"Error al enviar métricas: {response.status} - {await response.text()}")
            except aiohttp.ClientConnectorError as e:
                logging.error(f"No se pudo conectar al backend para enviar métricas: {e}")
            except Exception as e:
                logging.error(f"Ocurrió un error inesperado al enviar métricas: {e}")

    @send_metrics_to_backend.before_loop
    async def before_send_metrics(self):
        await self.bot.wait_until_ready()

    # --- Tarea: Sincronización con Google Sheets (cada 10 min) ---

    @tasks.loop(minutes=10)
    async def sync_google_sheets_task(self):
        logging.info("↻ Iniciando sincronización periódica con Google Sheets...")
        from google_sheets import sync_practicantes_to_db, export_report_to_sheet
        await sync_practicantes_to_db()
        await export_report_to_sheet()

    @sync_google_sheets_task.before_loop
    async def before_sync_sheets(self):
        await self.bot.wait_until_ready()

    # --- Tarea: Auto-salida de asistencia (14:15 Lima) ---

    @tasks.loop(time=[datetime.time(hour=14, minute=15, tzinfo=LIMA_TZ)])
    async def auto_salida_asistencia(self):
        """Cierra todas las asistencias sin salida a las 14:15. Marca hora_salida = 14:00 y levanta reporte."""
        if es_domingo():
            return

        logging.info("🔒 Ejecutando auto-salida de asistencia (14:15)...")

        fecha_hoy = datetime.datetime.now(LIMA_TZ).date()

        # 1. Buscar asistencias sin salida hoy
        query_pendientes = """
        SELECT a.id, a.practicante_id, p.id_discord, p.nombre_completo
        FROM asistencia a
        JOIN practicante p ON p.id = a.practicante_id
        WHERE a.fecha = $1
          AND a.hora_entrada IS NOT NULL
          AND a.hora_salida IS NULL
        """
        registros = await db.fetch_all(query_pendientes, fecha_hoy)

        if not registros:
            logging.info("✅ No hay asistencias pendientes de cierre.")
            return

        for reg in registros:
            try:
                # 2. Notificar por DM (El cierre en BD lo hace el backend Java a las 14:17)
                user = self.bot.get_user(reg['id_discord']) or await self.bot.fetch_user(reg['id_discord'])
                if user:
                    try:
                        await user.send(
                            f"🚨 **Salida registrada automáticamente**\n"
                            f"No marcaste tu salida antes de las 14:15hs.\n"
                            f"Se registró tu salida a las **14:00** y se levantó un reporte por AFK.\n"
                            f"Contactá con el administrador si fue un error."
                        )
                    except discord.Forbidden:
                        logging.warning(f"No se pudo enviar DM a {reg['nombre_completo']}")

                logging.info(f"⚠️ Alerta de auto-salida enviada a {reg['nombre_completo']}")

            except Exception as e:
                logging.error(f"Error procesando alerta de asistencia para usuario ID {reg['id']}: {e}")

        logging.info(f"🔒 Alertas de auto-salida enviadas. {len(registros)} usuarios notificados.")

    @auto_salida_asistencia.before_loop
    async def before_auto_salida(self):
        await self.bot.wait_until_ready()

    # --- Tarea: Reporte Diario Automático (cada 15 min, después de 2:30 PM) ---

    @tasks.loop(minutes=15)
    async def auto_reporte_diario_task(self):
        ahora = datetime.datetime.now(LIMA_TZ)
        if ahora.hour < 14 or es_domingo():
            return

        fecha_hoy = ahora.date()

        # 1. Verificar si ya se envió hoy
        ya_enviado = await db.fetch_one(
            "SELECT 1 FROM reportes_enviados WHERE fecha = $1", fecha_hoy
        )
        if ya_enviado:
            return

        # 2. Verificar si hay salidas pendientes
        pendientes = await db.fetch_one(
            "SELECT COUNT(*) as count FROM asistencia WHERE fecha = $1 AND hora_entrada IS NOT NULL AND hora_salida IS NULL",
            fecha_hoy
        )

        if pendientes and pendientes['count'] > 0:
            logging.info(f"⏳ Reporte diario: {pendientes['count']} salidas pendientes. Postergando...")
            return

        # 3. Si no hay pendientes, generar y enviar reporte
        canal_reportes_id = 1468317880553574420
        canal = self.bot.get_channel(canal_reportes_id)

        if not canal:
            logging.error(f"❌ No se encontró el canal de reportes {canal_reportes_id}")
            return

        logging.info("📊 Todos han salido. Enviando reporte diario automático...")

        asistencias = await db.fetch_all("""
        SELECT p.nombre_completo, a.hora_entrada, a.hora_salida, a.estado
        FROM practicante p
        JOIN asistencia a ON p.id = a.practicante_id AND a.fecha = $1
        ORDER BY a.hora_entrada ASC
        """, fecha_hoy)

        if not asistencias:
            return

        embed = discord.Embed(
            title=f"📋 Reporte Diario de Asistencia - {fecha_hoy.strftime('%d/%m/%Y')}",
            description="Todos los practicantes del turno han registrado su salida.",
            color=discord.Color.gold(),
            timestamp=ahora
        )

        emoji_map = {'temprano': '✅', 'tarde': '⚠️', 'sobreHora': '🔴', 'falto': '❌', 'clases': '📚'}
        lista_resumen = ""
        first_field = True
        for asis in asistencias:
            entrada = format_timedelta(asis['hora_entrada'])
            salida = format_timedelta(asis['hora_salida'])
            emoji = emoji_map.get(asis['estado'], '❓')
            linea = f"• {emoji} **{asis['nombre_completo']}**: {entrada} - {salida} ({asis['estado']})\n"
            if len(lista_resumen) + len(linea) > 1024:
                embed.add_field(
                    name="Resumen de hoy" if first_field else "\u200b",
                    value=lista_resumen.rstrip(),
                    inline=False
                )
                lista_resumen = ""
                first_field = False
            lista_resumen += linea

        if lista_resumen:
            embed.add_field(
                name="Resumen de hoy" if first_field else "\u200b",
                value=lista_resumen.rstrip(),
                inline=False
            )
        elif first_field:
            embed.add_field(name="Resumen de hoy", value="Sin registros", inline=False)
        embed.set_footer(text="Cierre de jornada automático")

        await canal.send(content="🔔 <@615932763161362636>, el reporte diario ya está listo.", embed=embed)

        # 4. Marcar como enviado
        await db.execute_query(
            "INSERT INTO reportes_enviados (fecha) VALUES ($1)", fecha_hoy
        )
        logging.info(f"✅ Reporte diario del {fecha_hoy} enviado correctamente.")

    @auto_reporte_diario_task.before_loop
    async def before_reporte_diario(self):
        await self.bot.wait_until_ready()

    # --- Tarea: Registro Horario Automático (9 AM, 12 PM, 2 PM) ---

    @tasks.loop(time=[
        datetime.time(hour=9, minute=0, tzinfo=LIMA_TZ),
        datetime.time(hour=12, minute=0, tzinfo=LIMA_TZ),
        datetime.time(hour=14, minute=0, tzinfo=LIMA_TZ),
    ])
    async def auto_registro_horario_task(self):
        if es_domingo():
            return

        fecha_actual = datetime.datetime.now(LIMA_TZ).date()
        canal = self.bot.get_channel(1473020479332945940)
        if not canal:
            logging.error("❌ No se encontró el canal para registro horario automático")
            return

        # 1. A tiempo (temprano)
        a_tiempo = await db.fetch_all("""
        SELECT p.nombre_completo, a.hora_entrada
        FROM asistencia a JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = $1 AND a.estado = 'temprano'
        ORDER BY a.hora_entrada
        """, fecha_actual)

        # 2. Tardanza
        tardanza = await db.fetch_all("""
        SELECT p.nombre_completo, a.hora_entrada
        FROM asistencia a JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = $1 AND a.estado = 'tarde'
        ORDER BY a.hora_entrada
        """, fecha_actual)

        # 3. Sobre hora
        fuera = await db.fetch_all("""
        SELECT p.nombre_completo, a.hora_entrada
        FROM asistencia a JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = $1 AND a.estado = 'sobreHora'
        ORDER BY a.hora_entrada
        """, fecha_actual)

        def format_hora(t):
            if t is None:
                return "---"
            if isinstance(t, datetime.timedelta):
                total = int(t.total_seconds())
                return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
            if isinstance(t, datetime.time):
                return t.strftime('%H:%M')
            return str(t)

        def agregar_lista_paginada(embed, registros):
            if not registros:
                embed.add_field(name="\u200b", value="*Ninguno*", inline=False)
                return
            chunk = ""
            for r in registros:
                linea = f"• **{r['nombre_completo']}** — {format_hora(r['hora_entrada'])}\n"
                if len(chunk) + len(linea) > 1024:
                    embed.add_field(name="\u200b", value=chunk.rstrip(), inline=False)
                    chunk = ""
                chunk += linea
            if chunk:
                embed.add_field(name="\u200b", value=chunk.rstrip(), inline=False)

        hora_actual = datetime.datetime.now(LIMA_TZ).strftime('%I:%M %p')

        embed_verde = discord.Embed(
            title=f"✅ Llegaron a tiempo - {fecha_actual.strftime('%d/%m/%Y')}",
            description=f"Practicantes que llegaron antes de las 8:10 a.m. ({len(a_tiempo)})",
            color=discord.Color.green()
        )
        agregar_lista_paginada(embed_verde, a_tiempo)

        embed_naranja = discord.Embed(
            title=f"🟠 Tardanza - {fecha_actual.strftime('%d/%m/%Y')}",
            description=f"Practicantes que llegaron entre 8:11 y 9:00 a.m. ({len(tardanza)})",
            color=discord.Color.orange()
        )
        agregar_lista_paginada(embed_naranja, tardanza)

        embed_rojo = discord.Embed(
            title=f"🔴 Sobre hora - {fecha_actual.strftime('%d/%m/%Y')}",
            description=f"Practicantes que llegaron después de las 9:00 a.m. ({len(fuera)})",
            color=discord.Color.red()
        )
        agregar_lista_paginada(embed_rojo, fuera)

        await canal.send(
            content=f"📊 **Registro Horario Automático** — {hora_actual}",
            embeds=[embed_verde, embed_naranja, embed_rojo]
        )
        logging.info(f"✅ Registro horario automático enviado a las {hora_actual}")

    @auto_registro_horario_task.before_loop
    async def before_registro_horario(self):
        await self.bot.wait_until_ready()

    # --- Tarea: Cierre Automático de Recuperaciones (20:20 Lima) ---

    @tasks.loop(time=[datetime.time(hour=20, minute=20, tzinfo=LIMA_TZ)])
    async def auto_cierre_recuperacion(self):
        """Cierra todas las recuperaciones abiertas del día a las 20:20.
        Marca hora_salida = 20:00 y levanta reporte afk_salida."""
        if es_domingo():
            return

        logging.info("🔒 Ejecutando cierre automático de recuperaciones...")

        fecha_hoy = datetime.datetime.now(LIMA_TZ).date()

        # 1. Obtener todos los registros abiertos del día
        registros = await db.fetch_all("""
        SELECT r.id, r.practicante_id, p.id_discord, p.nombre_completo
        FROM recuperacion r
        JOIN practicante p ON p.id = r.practicante_id
        WHERE r.fecha = $1 AND r.estado = 'abierto'
        """, fecha_hoy)

        if not registros:
            logging.info("✅ No hay recuperaciones abiertas para cerrar.")
            return

        for reg in registros:
            try:
                # 2. Notificar por DM (El cierre en BD lo hace el backend Java a las 20:22)
                user = self.bot.get_user(reg['id_discord']) or await self.bot.fetch_user(reg['id_discord'])
                if user:
                    try:
                        await user.send(
                            f"🚨 **Tu recuperación fue cerrada automáticamente.**\n"
                            f"No registraste tu salida antes de las 20:20hs.\n"
                            f"Se registraron tus horas hasta las **20:00**.\n"
                            f"Se levantó un reporte por AFK."
                        )
                    except discord.Forbidden:
                        logging.warning(f"No se pudo enviar DM a {reg['nombre_completo']}")

                logging.info(f"⚠️ Alerta de cierre de recuperación enviada a {reg['nombre_completo']}")

            except Exception as e:
                logging.error(f"Error procesando alerta de recuperación para usuario ID {reg['id']}: {e}")

        logging.info(f"🔒 Alertas de cierre automático enviadas. {len(registros)} usuarios notificados.")

    @auto_cierre_recuperacion.before_loop
    async def before_cierre_recuperacion(self):
        await self.bot.wait_until_ready()

    # --- Iniciar todas las tareas cuando el cog se carga ---

    async def cog_load(self):
        self.send_metrics_to_backend.start()
        self.sync_google_sheets_task.start()
        self.auto_reporte_diario_task.start()
        self.auto_registro_horario_task.start()
        self.auto_cierre_recuperacion.start()
        self.auto_salida_asistencia.start()
        logging.info("✅ Tareas programadas iniciadas.")


async def setup(bot):
    await bot.add_cog(ScheduledTasks(bot))

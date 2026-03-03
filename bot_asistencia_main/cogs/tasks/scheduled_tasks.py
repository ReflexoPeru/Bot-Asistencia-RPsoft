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
    HORA_CIERRE_REAL,
    MAX_ADVERTENCIAS_CONSECUTIVAS,
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
        # Guardar referencia en el bot para acceso desde main()
        bot.metrics = self.metrics

    def cog_unload(self):
        self.send_metrics_to_backend.cancel()
        self.sync_google_sheets_task.cancel()
        self.auto_reporte_diario_task.cancel()
        self.auto_registro_horario_task.cancel()
        self.auto_cierre_recuperacion.cancel()

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

    # --- Tarea: Reporte Diario Automático (cada 15 min, después de 2:30 PM) ---

    @tasks.loop(minutes=15)
    async def auto_reporte_diario_task(self):
        ahora = datetime.datetime.now(LIMA_TZ)
        if ahora.hour < 14 or es_domingo():
            return

        fecha_hoy = ahora.date()

        # 1. Verificar si ya se envió hoy
        query_check = "SELECT 1 FROM reportes_enviados WHERE fecha = %s"
        ya_enviado = await db.fetch_one(query_check, (fecha_hoy,))
        if ya_enviado:
            return

        # 2. Verificar si hay salidas pendientes
        query_pendientes = "SELECT COUNT(*) as count FROM asistencia WHERE fecha = %s AND hora_entrada IS NOT NULL AND hora_salida IS NULL"
        pendientes = await db.fetch_one(query_pendientes, (fecha_hoy,))

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

        query_asistencia = """
        SELECT p.nombre_completo, a.hora_entrada, a.hora_salida, ea.estado
        FROM practicante p
        JOIN asistencia a ON p.id = a.practicante_id AND a.fecha = %s
        JOIN estado_asistencia ea ON a.estado_id = ea.id
        ORDER BY a.hora_entrada ASC
        """
        asistencias = await db.fetch_all(query_asistencia, (fecha_hoy,))

        if not asistencias:
            return

        embed = discord.Embed(
            title=f"📋 Reporte Diario de Asistencia - {fecha_hoy.strftime('%d/%m/%Y')}",
            description="Todos los practicantes del turno han registrado su salida.",
            color=discord.Color.gold(),
            timestamp=ahora
        )

        lista_resumen = ""
        first_field = True
        for asis in asistencias:
            entrada = format_timedelta(asis['hora_entrada'])
            salida = format_timedelta(asis['hora_salida'])
            linea = f"• **{asis['nombre_completo']}**: {entrada} - {salida} ({asis['estado']})\n"
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

        # 4. Marcar como enviado en la BD
        await db.execute_query("INSERT INTO reportes_enviados (fecha) VALUES (%s)", (fecha_hoy,))
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

        # 1. A tiempo (estado_id = 1 = Presente)
        query_a_tiempo = """
        SELECT p.nombre_completo, a.hora_entrada
        FROM asistencia a JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = %s AND a.estado_id = 1
        ORDER BY a.hora_entrada
        """
        a_tiempo = await db.fetch_all(query_a_tiempo, (fecha_actual,))

        # 2. Tardanza (estado_id = 2, hora_entrada <= 09:00)
        query_tardanza = """
        SELECT p.nombre_completo, a.hora_entrada
        FROM asistencia a JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = %s AND a.estado_id = 2 AND a.hora_entrada <= '09:00:00'
        ORDER BY a.hora_entrada
        """
        tardanza = await db.fetch_all(query_tardanza, (fecha_actual,))

        # 3. Fuera del límite (hora_entrada > 09:00)
        query_fuera = """
        SELECT p.nombre_completo, a.hora_entrada
        FROM asistencia a JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = %s AND a.hora_entrada > '09:00:00'
        ORDER BY a.hora_entrada
        """
        fuera = await db.fetch_all(query_fuera, (fecha_actual,))

        def format_hora(td):
            if td is None:
                return "---"
            total_seconds = int(td.total_seconds()) if hasattr(td, 'total_seconds') else 0
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"

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
            title=f"🟠 Llegaron con tardanza - {fecha_actual.strftime('%d/%m/%Y')}",
            description=f"Practicantes que llegaron entre 8:10 y 9:00 a.m. ({len(tardanza)})",
            color=discord.Color.orange()
        )
        agregar_lista_paginada(embed_naranja, tardanza)

        embed_rojo = discord.Embed(
            title=f"🔴 Llegaron fuera del límite 9:00 - {fecha_actual.strftime('%d/%m/%Y')}",
            description=f"Practicantes que llegaron después de las 9:00 a.m. ({len(fuera)})",
            color=discord.Color.red()
        )
        agregar_lista_paginada(embed_rojo, fuera)

        await canal.send(content=f"📊 **Registro Horario Automático** — {hora_actual}", embeds=[embed_verde, embed_naranja, embed_rojo])
        logging.info(f"✅ Registro horario automático enviado a las {hora_actual}")

    @auto_registro_horario_task.before_loop
    async def before_registro_horario(self):
        await self.bot.wait_until_ready()

    # --- Tarea: Cierre Automático de Recuperaciones (20:20 Lima) ---

    @tasks.loop(time=[datetime.time(hour=HORA_CIERRE_REAL.hour, minute=HORA_CIERRE_REAL.minute, tzinfo=LIMA_TZ)])
    async def auto_cierre_recuperacion(self):
        """Cierra todas las recuperaciones abiertas del día a las 20:20."""
        if es_domingo():
            return

        logging.info("🔒 Ejecutando cierre automático de recuperaciones...")

        # 1. Obtener todos los registros abiertos del día
        query_abiertos = """
        SELECT ar.id, ar.practicante_id, p.id_discord, p.nombre_completo
        FROM asistencia_recuperacion ar
        JOIN practicante p ON p.id = ar.practicante_id
        WHERE ar.fecha_recuperacion = CURDATE()
          AND ar.estado = 'abierto'
        """
        registros = await db.fetch_all(query_abiertos)

        if not registros:
            logging.info("✅ No hay recuperaciones abiertas para cerrar.")
            return

        hora_cierre_str = HORA_FIN_RECUPERACION.strftime('%H:%M')

        for reg in registros:
            rec_id = reg['id']
            practicante_id = reg['practicante_id']
            discord_id = reg['id_discord']
            nombre = reg['nombre_completo']

            try:
                # 2. Cerrar registro con hora_salida = 20:00
                await db.execute_query(
                    "UPDATE asistencia_recuperacion SET hora_salida = %s WHERE id = %s",
                    (HORA_FIN_RECUPERACION, rec_id)
                )

                # 3. Sumar advertencia
                await db.execute_query(
                    "UPDATE practicante SET advertencias = advertencias + 1 WHERE id = %s",
                    (practicante_id,)
                )

                # 4. Obtener valor actualizado
                prac = await db.fetch_one(
                    "SELECT advertencias FROM practicante WHERE id = %s",
                    (practicante_id,)
                )
                advertencias = prac['advertencias'] if prac else 1

                # 5. Enviar DM según cantidad de advertencias
                user = self.bot.get_user(discord_id) or await self.bot.fetch_user(discord_id)

                if advertencias >= MAX_ADVERTENCIAS_CONSECUTIVAS:
                    # Invalidar registro y resetear contador
                    await db.execute_query(
                        "UPDATE asistencia_recuperacion SET estado = 'invalidado' WHERE id = %s",
                        (rec_id,)
                    )
                    await db.execute_query(
                        "UPDATE practicante SET advertencias = 0 WHERE id = %s",
                        (practicante_id,)
                    )

                    if user:
                        try:
                            await user.send(
                                f"❌ **Horas de recuperación invalidadas**\n"
                                f"Acumulaste {MAX_ADVERTENCIAS_CONSECUTIVAS} advertencias consecutivas "
                                f"por no cerrar tu recuperación a tiempo.\n"
                                f"Las horas de recuperación de hoy **no serán contabilizadas**.\n"
                                f"Contactá con el administrador si creés que es un error."
                            )
                        except discord.Forbidden:
                            logging.warning(f"No se pudo enviar DM a {nombre} ({discord_id})")

                    logging.warning(f"❌ Recuperación invalidada para {nombre} (3 advertencias)")
                else:
                    # Marcar como válido pero con advertencia
                    await db.execute_query(
                        "UPDATE asistencia_recuperacion SET estado = 'valido' WHERE id = %s",
                        (rec_id,)
                    )

                    if user:
                        try:
                            await user.send(
                                f"🚨 **Tu recuperación fue cerrada automáticamente.**\n"
                                f"No registraste tu salida antes de las {HORA_CIERRE_REAL.strftime('%H:%M')}hs.\n"
                                f"⏱️ Se registraron tus horas hasta las {hora_cierre_str}hs.\n"
                                f"⚠️ Advertencia ({advertencias}/{MAX_ADVERTENCIAS_CONSECUTIVAS}). "
                                f"Si acumulás {MAX_ADVERTENCIAS_CONSECUTIVAS} advertencias consecutivas, "
                                f"tus horas de recuperación serán invalidadas."
                            )
                        except discord.Forbidden:
                            logging.warning(f"No se pudo enviar DM a {nombre} ({discord_id})")

                    logging.info(f"⚠️ Recuperación cerrada para {nombre} — Advertencia {advertencias}/{MAX_ADVERTENCIAS_CONSECUTIVAS}")

            except Exception as e:
                logging.error(f"Error cerrando recuperación ID {rec_id} para {nombre}: {e}")

        logging.info(f"🔒 Cierre automático completado. {len(registros)} registros procesados.")

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
        logging.info("✅ Tareas programadas iniciadas.")


async def setup(bot):
    await bot.add_cog(ScheduledTasks(bot))

"""Tareas automáticas relacionadas a asistencia diaria."""

import datetime
import logging
import discord
from discord.ext import tasks
import database as db
from utils import LIMA_TZ, format_timedelta, es_domingo


class AutoAsistenciaTasks:
    """Tareas de auto-salida, reporte diario y registro horario."""

    @tasks.loop(time=[datetime.time(hour=14, minute=15, tzinfo=LIMA_TZ)])
    async def auto_salida_asistencia(self):
        """Notifica auto-salida a quienes no marcaron salida antes de 14:15.
        El cierre real en BD lo realiza el backend Java."""
        if es_domingo():
            return

        logging.info("🔒 Ejecutando auto-salida de asistencia (14:15)...")

        fecha_hoy = datetime.datetime.now(LIMA_TZ).date()

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
                user = self.bot.get_user(reg['id_discord']) or await self.bot.fetch_user(reg['id_discord'])
                if user:
                    try:
                        await user.send(
                            "🚨 **Salida registrada automáticamente**\n"
                            "No marcaste tu salida antes de las 14:15hs.\n"
                            "Se registró tu salida a las **14:00** y se levantó un reporte por AFK.\n"
                            "Contactá con el administrador si fue un error."
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

    @tasks.loop(minutes=15)
    async def auto_reporte_diario_task(self):
        ahora = datetime.datetime.now(LIMA_TZ)
        if ahora.hour < 14 or es_domingo():
            return

        fecha_hoy = ahora.date()

        ya_enviado = await db.fetch_one(
            "SELECT 1 FROM reportes_enviados WHERE fecha = $1", fecha_hoy
        )
        if ya_enviado:
            return

        pendientes = await db.fetch_one(
            "SELECT COUNT(*) as count FROM asistencia WHERE fecha = $1 AND hora_entrada IS NOT NULL AND hora_salida IS NULL",
            fecha_hoy
        )

        if pendientes and pendientes['count'] > 0:
            logging.info(f"⏳ Reporte diario: {pendientes['count']} salidas pendientes. Postergando...")
            return

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

        await db.execute_query(
            "INSERT INTO reportes_enviados (fecha) VALUES ($1)", fecha_hoy
        )
        logging.info(f"✅ Reporte diario del {fecha_hoy} enviado correctamente.")

    @auto_reporte_diario_task.before_loop
    async def before_reporte_diario(self):
        await self.bot.wait_until_ready()

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

        a_tiempo = await db.fetch_all("""
        SELECT p.nombre_completo, a.hora_entrada
        FROM asistencia a JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = $1 AND a.estado = 'temprano'
        ORDER BY a.hora_entrada
        """, fecha_actual)

        tardanza = await db.fetch_all("""
        SELECT p.nombre_completo, a.hora_entrada
        FROM asistencia a JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = $1 AND a.estado = 'tarde'
        ORDER BY a.hora_entrada
        """, fecha_actual)

        fuera = await db.fetch_all("""
        SELECT p.nombre_completo, a.hora_entrada
        FROM asistencia a JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = $1 AND a.estado = 'sobreHora'
        ORDER BY a.hora_entrada
        """, fecha_actual)

        faltas = await db.fetch_all("""
        SELECT p.nombre_completo, a.hora_entrada
        FROM asistencia a JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = $1 AND a.estado = 'falto'
        ORDER BY p.nombre_completo
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

        embed_gris = discord.Embed(
            title=f"❌ Faltas - {fecha_actual.strftime('%d/%m/%Y')}",
            description=f"Practicantes que no marcaron asistencia ({len(faltas)})",
            color=discord.Color.dark_grey()
        )
        agregar_lista_paginada(embed_gris, faltas)

        embeds_to_send = [embed_verde, embed_naranja, embed_rojo, embed_gris]

        await canal.send(
            content=f"📊 **Registro Horario Automático** — {hora_actual}",
            embeds=embeds_to_send
        )
        logging.info(f"✅ Registro horario automático enviado a las {hora_actual}")

    @auto_registro_horario_task.before_loop
    async def before_registro_horario(self):
        await self.bot.wait_until_ready()

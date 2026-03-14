"""Tarea automática para cierre de recuperaciones."""

import datetime
import logging
import discord
from discord.ext import tasks
import database as db
from utils import LIMA_TZ, es_domingo


class AutoRecuperacionTasks:
    """Cierra recuperaciones abiertas y notifica por DM."""

    @tasks.loop(time=[datetime.time(hour=20, minute=20, tzinfo=LIMA_TZ)])
    async def auto_cierre_recuperacion(self):
        """Cierra todas las recuperaciones abiertas del día a las 20:20.
        El cierre en BD lo realiza el backend Java a las 20:22."""
        if es_domingo():
            return

        logging.info("🔒 Ejecutando cierre automático de recuperaciones...")

        fecha_hoy = datetime.datetime.now(LIMA_TZ).date()

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
                user = self.bot.get_user(reg['id_discord']) or await self.bot.fetch_user(reg['id_discord'])
                if user:
                    try:
                        await user.send(
                            "🚨 **Tu recuperación fue cerrada automáticamente.**\n"
                            "No registraste tu salida antes de las 20:20hs.\n"
                            "Se registraron tus horas hasta las **20:00**.\n"
                            "Se levantó un reporte por AFK."
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

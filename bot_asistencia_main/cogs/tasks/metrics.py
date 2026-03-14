"""Métricas del bot y envío periódico al backend."""

import datetime
import logging
import aiohttp
import discord
from discord.ext import tasks, commands


class BotMetrics:
    """Contador simple de eventos y uptime."""

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


class MetricsTasks:
    """Listeners y tarea periódica de métricas."""

    metrics: BotMetrics

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

    # Listeners que actualizan el contador
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        self.metrics.increment_event_count()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        self.metrics.increment_event_count()

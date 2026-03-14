"""Tareas programadas del bot (ensamblador)."""

import logging
from discord.ext import commands

from .metrics import BotMetrics, MetricsTasks
from .sync_sheets import SyncSheetsTasks
from .auto_asistencia import AutoAsistenciaTasks
from .auto_recuperacion import AutoRecuperacionTasks


class ScheduledTasks(MetricsTasks, SyncSheetsTasks, AutoAsistenciaTasks, AutoRecuperacionTasks, commands.Cog):
    """Cog para tareas programadas: métricas, sincronización y reportes."""

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

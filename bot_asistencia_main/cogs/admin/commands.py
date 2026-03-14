"""Módulo administrativo para gestión de asistencia (ensamblador)."""

from discord.ext import commands

# Submódulos de comandos
from .dashboard import DashboardCommands
from .retiros import RetirosCommands
from .reportes import ReportesCommands
from .configuracion import ConfiguracionCommands
from .historial import HistorialCommands


class Admin(
    DashboardCommands,
    RetirosCommands,
    ReportesCommands,
    ConfiguracionCommands,
    HistorialCommands,
    commands.GroupCog,
    name="admin",
):
    """Cog para comandos administrativos ensamblado a partir de módulos."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot



async def setup(bot):
    await bot.add_cog(Admin(bot))

"""Ensamblador del Cog de asistencia."""

from discord.ext import commands

from .entrada_salida import EntradaSalidaCommands
from .estado import EstadoCommands
from .historial import HistorialCommands


class Asistencia(
    EntradaSalidaCommands,
    EstadoCommands,
    HistorialCommands,
    commands.GroupCog,
    name="asistencia",
):
    """Cog para gestionar comandos de asistencia como subcomandos agrupados."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot



async def setup(bot):
    await bot.add_cog(Asistencia(bot))

"""Comandos del módulo de faltas"""

import discord
from discord import app_commands, Embed, Color
from discord.ext import commands
from utils import obtener_practicante, canal_permitido
import database as db
import logging


class Faltas(commands.GroupCog, name="faltas"):
    """Cog para gestionar comandos de faltas"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name='ver', description="Ver tus faltas injustificadas")
    async def ver(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        discord_id = interaction.user.id
        practicante_id = await obtener_practicante(interaction, discord_id, usar_followup=True)
        if not practicante_id:
            return

        # Contar faltas (estado = 'falto')
        query_faltas = """
        SELECT COUNT(*) AS total FROM asistencia
        WHERE practicante_id = $1 AND estado = 'falto'
        """
        resultado = await db.fetch_one(query_faltas, practicante_id)
        total_faltas = resultado['total'] if resultado else 0

        # Últimas 5 faltas
        query_ultimas = """
        SELECT fecha FROM asistencia
        WHERE practicante_id = $1 AND estado = 'falto'
        ORDER BY fecha DESC
        LIMIT 5
        """
        ultimas = await db.fetch_all(query_ultimas, practicante_id)

        # Contar reportes de falta
        query_reportes = """
        SELECT COUNT(*) AS total FROM reporte
        WHERE practicante_id = $1 AND tipo = 'falta'
        """
        rep = await db.fetch_one(query_reportes, practicante_id)
        total_reportes = rep['total'] if rep else 0

        embed = Embed(
            title="📋 Faltas Injustificadas",
            color=Color.red() if total_faltas > 0 else Color.green()
        )
        embed.add_field(name="📊 Total de faltas", value=str(total_faltas), inline=True)
        embed.add_field(name="📝 Reportes de falta", value=str(total_reportes), inline=True)

        if ultimas:
            fechas_str = "\n".join([f"• {f['fecha'].strftime('%d/%m/%Y')}" for f in ultimas])
            embed.add_field(name="📅 Últimas faltas", value=fechas_str, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Faltas(bot))

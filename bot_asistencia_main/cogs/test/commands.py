"""Módulo de pruebas administrativas sin restricciones"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
import database as db
import logging
from utils import obtener_practicante, LIMA_TZ

@app_commands.default_permissions(administrator=True)
class Test(commands.GroupCog, name="test"):
    """Comandos de prueba exclusivos para admins (sin restricciones de horario)"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name='asistencia', description="Forzar entrada/salida de prueba (Admins solo, 24/7)")
    @app_commands.describe(
        accion="Entrada o Salida",
        id_discord="ID de Discord del practicante (opcional, por defecto tú)",
        estado="Estado manual (temprano, tarde, sobreHora, clases)"
    )
    @app_commands.choices(accion=[
        app_commands.Choice(name="Entrada", value="entrada"),
        app_commands.Choice(name="Salida", value="salida")
    ])
    async def test_asistencia(self, interaction: discord.Interaction, accion: str, id_discord: str = None, estado: str = "temprano"):
        await interaction.response.defer(ephemeral=True)

        target_id = int(id_discord) if id_discord else interaction.user.id
        ahora = datetime.now(LIMA_TZ)
        fecha_actual = ahora.date()
        hora_actual = ahora.time().replace(microsecond=0)

        practicante_id = await obtener_practicante(interaction, target_id, usar_followup=True)
        if not practicante_id:
            return

        if accion == "entrada":
            query = """
            INSERT INTO asistencia (practicante_id, estado, fecha, hora_entrada)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (practicante_id, fecha) DO UPDATE SET
                hora_entrada = EXCLUDED.hora_entrada,
                estado = EXCLUDED.estado
            """
            await db.execute_query(query, practicante_id, estado, fecha_actual, hora_actual)
            await interaction.followup.send(
                f"✅ [TEST] Entrada registrada para <@{target_id}> a las {hora_actual.strftime('%H:%M')} ({estado}).",
                ephemeral=True
            )
        
        else:  # salida
            query = """
            UPDATE asistencia SET hora_salida = $1
            WHERE practicante_id = $2 AND fecha = $3 AND hora_salida IS NULL
            """
            await db.execute_query(query, hora_actual, practicante_id, fecha_actual)
            await interaction.followup.send(
                f"✅ [TEST] Salida registrada para <@{target_id}> a las {hora_actual.strftime('%H:%M')}.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Test(bot))

from datetime import datetime
import discord
from discord import app_commands, Embed, Color
import database as db
from utils import obtener_practicante


class EstadoCommands:
    """Comandos para consultar estado del día del practicante."""

    @app_commands.command(name='estado', description="Ver tu estado de asistencia de hoy")
    async def estado(self, interaction: discord.Interaction):
        from utils import LIMA_TZ, format_timedelta

        await interaction.response.defer(ephemeral=True)

        discord_id = interaction.user.id
        practicante_id = await obtener_practicante(interaction, discord_id, usar_followup=True)
        if not practicante_id:
            return

        ahora = datetime.now(LIMA_TZ)
        fecha_actual = ahora.date()

        query = """
        SELECT estado, hora_entrada, hora_salida, salida_auto FROM asistencia
        WHERE practicante_id = $1 AND fecha = $2
        """
        registro = await db.fetch_one(query, practicante_id, fecha_actual)

        query_recup = """
        SELECT hora_entrada, hora_salida, estado FROM recuperacion
        WHERE practicante_id = $1 AND fecha = $2
        """
        recup = await db.fetch_one(query_recup, practicante_id, fecha_actual)

        embed = Embed(title="📊 Tu estado de hoy", color=Color.blue())
        embed.add_field(name="📅 Fecha", value=fecha_actual.strftime('%d-%m-%Y'), inline=False)

        if registro:
            he = format_timedelta(registro['hora_entrada'])
            hs = format_timedelta(registro['hora_salida']) if registro['hora_salida'] else "Pendiente"
            auto = " (automática)" if registro.get('salida_auto') else ""
            embed.add_field(name="📋 Estado", value=registro['estado'].upper(), inline=True)
            embed.add_field(name="🟢 Entrada", value=he, inline=True)
            embed.add_field(name="🔴 Salida", value=f"{hs}{auto}", inline=True)
        else:
            embed.add_field(name="📋 Asistencia", value="Sin registro de entrada", inline=False)

        if recup:
            rhe = format_timedelta(recup['hora_entrada'])
            rhs = format_timedelta(recup['hora_salida']) if recup['hora_salida'] else "En curso"
            embed.add_field(name="🔄 Recuperación", value=f"{rhe} → {rhs} ({recup['estado']})", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

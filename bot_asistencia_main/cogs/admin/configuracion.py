import discord
from discord import app_commands
from datetime import datetime
import database as db
from utils import LIMA_TZ
from .helpers import verificar_admin


class ConfiguracionCommands:
    """Comandos de configuración y ajustes rápidos."""

    @app_commands.command(name='ausencia', description="Configurar días de clase de un practicante")
    @app_commands.describe(
        usuario="Practicante",
        dia="Día de la semana con clases",
        activar="True para marcar clase, False para quitar"
    )
    @app_commands.choices(dia=[
        app_commands.Choice(name="Lunes", value="clase_lunes"),
        app_commands.Choice(name="Martes", value="clase_martes"),
        app_commands.Choice(name="Miércoles", value="clase_miercoles"),
        app_commands.Choice(name="Jueves", value="clase_jueves"),
        app_commands.Choice(name="Viernes", value="clase_viernes"),
        app_commands.Choice(name="Sábado", value="clase_sabado"),
    ])
    async def ausencia(self, interaction: discord.Interaction, usuario: discord.Member, dia: str, activar: bool = True):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        prac = await db.fetch_one(
            "SELECT id, nombre_completo FROM practicante WHERE id_discord = $1",
            usuario.id
        )
        if not prac:
            await interaction.followup.send("❌ Usuario no registrado.", ephemeral=True)
            return

        await db.execute_query(
            f"UPDATE practicante SET {dia} = $1 WHERE id = $2",
            activar, prac['id']
        )

        dia_nombre = dia.replace('clase_', '').capitalize()
        estado = "activado" if activar else "desactivado"
        await interaction.followup.send(
            f"✅ **{prac['nombre_completo']}** — {dia_nombre}: clase **{estado}**.",
            ephemeral=True
        )

    @app_commands.command(name='justificar', description="Justificar la inasistencia de un practicante")
    @app_commands.describe(usuario="Practicante a justificar", motivo="Motivo de la justificación")
    async def justificar(self, interaction: discord.Interaction, usuario: discord.Member, motivo: str):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        prac = await db.fetch_one(
            "SELECT id, nombre_completo FROM practicante WHERE id_discord = $1",
            usuario.id
        )
        if not prac:
            await interaction.followup.send("❌ Usuario no registrado.", ephemeral=True)
            return

        fecha = datetime.now(LIMA_TZ).date()

        await db.execute_query(
            "INSERT INTO reporte (practicante_id, descripcion, tipo, fecha, creado_por) VALUES ($1, $2, 'justificacion', $3, $4)",
            prac['id'], motivo, fecha, interaction.user.id
        )

        await interaction.followup.send(
            f"✅ Justificación registrada para **{prac['nombre_completo']}** — {motivo}",
            ephemeral=True
        )

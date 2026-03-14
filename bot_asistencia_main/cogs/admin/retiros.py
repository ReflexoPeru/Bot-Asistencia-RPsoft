import discord
from discord import app_commands, Embed, Color
import database as db
from .helpers import verificar_admin
from .views import ConfirmacionRetirar


class RetirosCommands:
    """Comandos relacionados a retiros (soft-delete)."""

    @app_commands.command(name='retirar', description="Retirar a un practicante (soft-delete)")
    @app_commands.describe(usuario="Practicante a retirar", motivo="Motivo del retiro")
    async def retirar(self, interaction: discord.Interaction, usuario: discord.Member, motivo: str):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        prac = await db.fetch_one(
            "SELECT id, nombre_completo, estado FROM practicante WHERE id_discord = $1",
            usuario.id
        )
        if not prac:
            await interaction.followup.send("❌ Este usuario no está registrado.", ephemeral=True)
            return
        if prac['estado'] == 'retirado':
            await interaction.followup.send("⚠️ Este practicante ya está retirado.", ephemeral=True)
            return

        view = ConfirmacionRetirar(prac['id'], prac['nombre_completo'], motivo, interaction.user.id)
        await interaction.followup.send(
            f"⚠️ ¿Confirmar retiro de **{prac['nombre_completo']}**?\nMotivo: {motivo}",
            view=view,
            ephemeral=True
        )

    @app_commands.command(name='listar_retirados', description="Ver lista de practicantes retirados")
    async def listar_retirados(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        rows = await db.fetch_all(
            "SELECT nombre_completo, fecha_retiro, motivo_retiro FROM practicante WHERE estado = 'retirado' ORDER BY fecha_retiro DESC"
        )
        if not rows:
            await interaction.followup.send("📭 No hay practicantes retirados.", ephemeral=True)
            return

        lineas = []
        for i, r in enumerate(rows, 1):
            fecha = r['fecha_retiro'].strftime('%d/%m') if r['fecha_retiro'] else 'N/A'
            motivo = r['motivo_retiro'] or 'Sin motivo'
            lineas.append(f"`{i}.` {r['nombre_completo']} — {fecha} — {motivo}")

        embed = Embed(title="📋 Practicantes Retirados", description="\n".join(lineas[:25]), color=Color.red())
        embed.set_footer(text=f"Total: {len(rows)}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='eliminar_practicante', description="Eliminar un practicante (soft-delete)")
    @app_commands.describe(usuario="Practicante a eliminar")
    async def eliminar_practicante(self, interaction: discord.Interaction, usuario: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        prac = await db.fetch_one(
            "SELECT id, nombre_completo FROM practicante WHERE id_discord = $1 AND estado = 'activo'",
            usuario.id
        )
        if not prac:
            await interaction.followup.send("❌ Este usuario no está registrado o ya fue retirado.", ephemeral=True)
            return

        view = ConfirmacionRetirar(prac['id'], prac['nombre_completo'], "Eliminado por admin", interaction.user.id)
        await interaction.followup.send(
            f"⚠️ ¿Confirmar retiro de **{prac['nombre_completo']}**?",
            view=view,
            ephemeral=True
        )

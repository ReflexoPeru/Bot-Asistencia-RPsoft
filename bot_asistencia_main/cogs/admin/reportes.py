import discord
from discord import app_commands, Embed, Color
from datetime import datetime
import database as db
from bot.config.constants import MAX_BANEOS_RETIRO
from utils import format_timedelta, LIMA_TZ
from .helpers import verificar_admin


class ReportesCommands:
    """Comandos para gestionar reportes y el resumen diario."""

    @app_commands.command(name='reportar', description="Crear un reporte para un practicante")
    @app_commands.describe(usuario="Practicante a reportar", tipo="Tipo de reporte", descripcion="Descripción del reporte")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Llamada de atención", value="llamada_atencion"),
        app_commands.Choice(name="Justificación", value="justificacion"),
        app_commands.Choice(name="Baneo", value="baneo"),
        app_commands.Choice(name="Falta", value="falta"),
    ])
    async def reportar(self, interaction: discord.Interaction, usuario: discord.Member, tipo: str, descripcion: str):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        prac = await db.fetch_one(
            "SELECT id, nombre_completo, baneos FROM practicante WHERE id_discord = $1",
            usuario.id
        )
        if not prac:
            await interaction.followup.send("❌ Usuario no registrado.", ephemeral=True)
            return

        # Crear reporte
        await db.execute_query(
            "INSERT INTO reporte (practicante_id, descripcion, tipo, creado_por) VALUES ($1, $2, $3, $4)",
            prac['id'], descripcion, tipo, interaction.user.id
        )

        msg = f"✅ Reporte **{tipo}** creado para **{prac['nombre_completo']}**."

        # Si es baneo, incrementar contador
        if tipo == 'baneo':
            nuevos_baneos = prac['baneos'] + 1
            await db.execute_query(
                "UPDATE practicante SET baneos = $1 WHERE id = $2",
                nuevos_baneos, prac['id']
            )
            msg += f"\n⚠️ Baneos acumulados: **{nuevos_baneos}/{MAX_BANEOS_RETIRO}**"

            if nuevos_baneos >= MAX_BANEOS_RETIRO:
                await db.execute_query(
                    "UPDATE practicante SET estado = 'retirado', fecha_retiro = CURRENT_DATE, motivo_retiro = 'Acumulación de baneos' WHERE id = $1",
                    prac['id']
                )
                await db.execute_query(
                    "INSERT INTO reporte (practicante_id, descripcion, tipo, creado_por) VALUES ($1, $2, 'retiro', $3)",
                    prac['id'], f"Retiro automático por acumulación de {MAX_BANEOS_RETIRO} baneos", interaction.user.id
                )
                msg += f"\n🚪 **{prac['nombre_completo']}** ha sido **retirado automáticamente** por acumulación de {MAX_BANEOS_RETIRO} baneos."

        await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name='reportes', description="Ver reportes de un practicante")
    @app_commands.describe(usuario="Practicante")
    async def reportes(self, interaction: discord.Interaction, usuario: discord.Member):
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

        rows = await db.fetch_all(
            "SELECT tipo, descripcion, fecha, revisado FROM reporte WHERE practicante_id = $1 ORDER BY fecha DESC LIMIT 15",
            prac['id']
        )
        if not rows:
            await interaction.followup.send(f"📭 {prac['nombre_completo']} no tiene reportes.", ephemeral=True)
            return

        lineas = []
        for r in rows:
            check = "✅" if r['revisado'] else "⬜"
            fecha = r['fecha'].strftime('%d/%m')
            lineas.append(f"{check} `{r['tipo']}` — {fecha} — {r['descripcion'][:60]}")

        embed = Embed(
            title=f"📋 Reportes de {prac['nombre_completo']}",
            description="\n".join(lineas),
            color=Color.orange()
        )
        embed.set_footer(text=f"Total: {len(rows)} (mostrando últimos 15)")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='reporte_hoy', description="Generar reporte del día (público)")
    async def reporte_hoy(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not await verificar_admin(interaction):
            return

        fecha = datetime.now(LIMA_TZ).date()

        rows = await db.fetch_all("""
        SELECT p.nombre_completo, a.estado, a.hora_entrada, a.hora_salida
        FROM asistencia a
        JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = $1
        ORDER BY a.hora_entrada
        """, fecha)

        if not rows:
            await interaction.followup.send("📭 No hay registros de asistencia para hoy.")
            return

        lineas = []
        for r in rows:
            he = format_timedelta(r['hora_entrada']) if r['hora_entrada'] else "—"
            hs = format_timedelta(r['hora_salida']) if r['hora_salida'] else "—"
            emoji = {'temprano': '✅', 'tarde': '⚠️', 'sobreHora': '🔴', 'falto': '❌', 'clases': '📚'}.get(r['estado'], '❓')
            lineas.append(f"{emoji} {r['nombre_completo']} — {he} → {hs}")

        embed = Embed(
            title=f"📊 Reporte de Asistencia — {fecha.strftime('%d/%m/%Y')}",
            description="\n".join(lineas[:25]),
            color=Color.blue()
        )
        embed.set_footer(text=f"Total registros: {len(rows)}")
        await interaction.followup.send(embed=embed)

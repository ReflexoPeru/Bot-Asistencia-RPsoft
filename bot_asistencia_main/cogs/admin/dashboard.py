import discord
from discord import app_commands, Embed, Color
from datetime import datetime
import database as db
from bot.config.constants import DIAS_SEMANA
from utils import DIAS_CLASE, LIMA_TZ
from .helpers import verificar_admin
from .views import DashboardListasView


class DashboardCommands:
    """Comandos del dashboard de asistencia."""

    @app_commands.command(name='registros', description="Ver dashboard de asistencia del día")
    async def registros(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        ahora = datetime.now(LIMA_TZ)
        fecha = ahora.date()
        dia_semana = ahora.weekday()  # 0=lunes
        col_clase = DIAS_CLASE.get(dia_semana, 'clase_lunes')
        dia_nombre = DIAS_SEMANA.get(dia_semana, 'Hoy')

        # 1. Total inicial (activos + retirados)
        q1 = await db.fetch_one("SELECT COUNT(*) AS total FROM practicante")
        total_inicial = q1['total']

        # 2. Retirados
        q2 = await db.fetch_one("SELECT COUNT(*) AS total FROM practicante WHERE estado = 'retirado'")
        total_retirados = q2['total']

        # 3. Actuales (activos)
        q3 = await db.fetch_one("SELECT COUNT(*) AS total FROM practicante WHERE estado = 'activo'")
        total_activos = q3['total']

        # 4. Ausentes por clases hoy
        q4 = await db.fetch_one(f"SELECT COUNT(*) AS total FROM practicante WHERE estado = 'activo' AND {col_clase} = TRUE")
        ausentes_clases = q4['total']

        # 5. Justificaciones hoy
        q5 = await db.fetch_one(
            "SELECT COUNT(*) AS total FROM reporte WHERE tipo = 'justificacion' AND fecha = $1", fecha
        )
        justificaciones = q5['total']

        # 6. Deben asistir hoy
        deben_asistir = total_activos - ausentes_clases - justificaciones

        # 7. Presentes (temprano)
        q7 = await db.fetch_one(
            "SELECT COUNT(*) AS total FROM asistencia WHERE fecha = $1 AND estado = 'temprano'", fecha
        )
        presentes = q7['total']

        # 8. Faltan llegar
        q_registrados = await db.fetch_one(
            "SELECT COUNT(*) AS total FROM asistencia WHERE fecha = $1 AND estado != 'falto'", fecha
        )
        registrados = q_registrados['total']
        faltan = max(0, deben_asistir - registrados)

        # 9. Tardanzas
        q9 = await db.fetch_one(
            "SELECT COUNT(*) AS total FROM asistencia WHERE fecha = $1 AND estado = 'tarde'", fecha
        )
        tardanzas = q9['total']

        # 10. Sobre hora
        q10 = await db.fetch_one(
            "SELECT COUNT(*) AS total FROM asistencia WHERE fecha = $1 AND estado = 'sobreHora'", fecha
        )
        sobre_hora = q10['total']

        # 11. Faltas
        q11 = await db.fetch_one(f"""
        SELECT COUNT(*) AS total FROM practicante p
        WHERE p.estado = 'activo'
          AND p.{col_clase} = FALSE
          AND NOT EXISTS (SELECT 1 FROM asistencia a WHERE a.practicante_id = p.id AND a.fecha = $1)
          AND NOT EXISTS (SELECT 1 FROM reporte r WHERE r.practicante_id = p.id AND r.fecha = $1 AND r.tipo = 'justificacion')
        """, fecha)
        faltas = q11['total']

        # 12. Acumulación de tardanzas total
        q12 = await db.fetch_one(
            "SELECT COUNT(*) AS total FROM asistencia WHERE estado IN ('tarde', 'sobreHora')"
        )
        acum_tardanzas = q12['total']

        # 13. Retirados hoy
        q13 = await db.fetch_one(
            "SELECT COUNT(*) AS total FROM practicante WHERE fecha_retiro = $1", fecha
        )
        retirados_hoy = q13['total']

        embed = Embed(
            title=f"📊 Dashboard de Asistencia — {dia_nombre} {fecha.strftime('%d/%m/%Y')}",
            color=Color.blue()
        )
        embed.add_field(
            name="👥 Practicantes",
            value=(
                f"Total inicial: **{total_inicial}**\n"
                f"Retirados: **{total_retirados}**\n"
                f"Actuales: **{total_activos}**"
            ),
            inline=True
        )
        embed.add_field(
            name="📅 Asistencia hoy",
            value=(
                f"Ausentes por clases: **{ausentes_clases}**\n"
                f"Justificaciones: **{justificaciones}**\n"
                f"Deben asistir: **{deben_asistir}**"
            ),
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.add_field(name="✅ Presentes a tiempo", value=f"**{presentes}**", inline=True)
        embed.add_field(name="⏳ Faltan llegar", value=f"**{faltan}**", inline=True)
        embed.add_field(name="⚠️ Tardanzas (8:11-9:00)", value=f"**{tardanzas}**", inline=True)
        embed.add_field(name="🔴 Sobre hora (>9:00)", value=f"**{sobre_hora}**", inline=True)
        embed.add_field(name="❌ Faltas", value=f"**{faltas}**", inline=True)
        embed.add_field(name="📈 Tardanzas acumuladas", value=f"**{acum_tardanzas}**", inline=True)

        if retirados_hoy > 0:
            embed.add_field(name="🚪 Retirados hoy", value=f"**{retirados_hoy}**", inline=True)

        embed.set_footer(text=f"Hora del reporte: {ahora.strftime('%H:%M:%S')}")

        await interaction.followup.send(embed=embed, view=DashboardListasView(fecha), ephemeral=True)

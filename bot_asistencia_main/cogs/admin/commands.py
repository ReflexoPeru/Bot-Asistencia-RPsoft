"""Módulo administrativo para gestión de asistencia"""

import discord
from discord import app_commands, Embed, Color
from discord.ext import commands
from typing import Optional
from datetime import datetime, time
from zoneinfo import ZoneInfo
from collections import defaultdict
import aiohttp
import re
import database as db
import logging
from utils import obtener_practicante, format_timedelta, format_timedelta_total, es_admin_bot, DIAS_CLASE, LIMA_TZ
from bot.config.constants import DIAS_SEMANA, MAX_BANEOS_RETIRO


# ──────────────────────────────────────────────
# View con botones para listas del dashboard
# ──────────────────────────────────────────────
class DashboardListasView(discord.ui.View):
    """Botones interactivos para ver cada lista del dashboard."""

    def __init__(self, fecha):
        super().__init__(timeout=300)
        self.fecha = fecha

    async def _enviar_lista(self, interaction, titulo, query, *args):
        await interaction.response.defer(ephemeral=True)
        rows = await db.fetch_all(query, *args)
        if not rows:
            await interaction.followup.send(f"📭 {titulo}: sin resultados.", ephemeral=True)
            return
        lineas = []
        for i, r in enumerate(rows, 1):
            nombre = r.get('nombre_completo', r.get('nombre_discord', 'N/A'))
            extra = ""
            if 'hora_entrada' in r and r['hora_entrada']:
                extra = f" — {format_timedelta(r['hora_entrada'])}"
            if 'descripcion' in r:
                extra = f" — {r['descripcion'][:50]}"
            if 'fecha_retiro' in r and r['fecha_retiro']:
                extra = f" — Retirado: {r['fecha_retiro'].strftime('%d/%m')}"
            lineas.append(f"`{i}.` {nombre}{extra}")

        texto = "\n".join(lineas[:25])  # Máx 25 para no exceder embed
        embed = Embed(title=f"📋 {titulo}", description=texto, color=Color.blue())
        embed.set_footer(text=f"Total: {len(rows)}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="📋 Retirados", style=discord.ButtonStyle.secondary, row=0)
    async def lista_retirados(self, interaction, button):
        query = "SELECT nombre_completo, fecha_retiro, motivo_retiro FROM practicante WHERE estado = 'retirado' ORDER BY fecha_retiro DESC"
        await self._enviar_lista(interaction, "Retirados", query)

    @discord.ui.button(label="📋 Justificados", style=discord.ButtonStyle.secondary, row=0)
    async def lista_justificados(self, interaction, button):
        query = """
        SELECT p.nombre_completo, r.descripcion FROM reporte r
        JOIN practicante p ON r.practicante_id = p.id
        WHERE r.tipo = 'justificacion' AND r.fecha = $1
        ORDER BY p.nombre_completo
        """
        await self._enviar_lista(interaction, "Justificados hoy", query, self.fecha)

    @discord.ui.button(label="📋 Tardanzas", style=discord.ButtonStyle.secondary, row=0)
    async def lista_tardanzas(self, interaction, button):
        query = """
        SELECT p.nombre_completo, a.hora_entrada, a.estado FROM asistencia a
        JOIN practicante p ON a.practicante_id = p.id
        WHERE a.fecha = $1 AND a.estado IN ('tarde', 'sobreHora')
        ORDER BY a.hora_entrada
        """
        await self._enviar_lista(interaction, "Tardanzas hoy", query, self.fecha)

    @discord.ui.button(label="📋 Faltas", style=discord.ButtonStyle.danger, row=1)
    async def lista_faltas(self, interaction, button):
        hoy = datetime.now(LIMA_TZ).weekday()
        col = DIAS_CLASE.get(hoy, 'clase_lunes')
        query = f"""
        SELECT p.nombre_completo FROM practicante p
        WHERE p.estado = 'activo'
          AND p.{col} = FALSE
          AND NOT EXISTS (SELECT 1 FROM asistencia a WHERE a.practicante_id = p.id AND a.fecha = $1)
          AND NOT EXISTS (SELECT 1 FROM reporte r WHERE r.practicante_id = p.id AND r.fecha = $1 AND r.tipo = 'justificacion')
        ORDER BY p.nombre_completo
        """
        await self._enviar_lista(interaction, "Faltas hoy", query, self.fecha)

    @discord.ui.button(label="📋 Acum. Tardanzas", style=discord.ButtonStyle.secondary, row=1)
    async def lista_tardanzas_acum(self, interaction, button):
        query = """
        SELECT p.nombre_completo, COUNT(*) AS total FROM asistencia a
        JOIN practicante p ON a.practicante_id = p.id
        WHERE a.estado IN ('tarde', 'sobreHora') AND p.estado = 'activo'
        GROUP BY p.nombre_completo
        ORDER BY total DESC
        LIMIT 25
        """
        await interaction.response.defer(ephemeral=True)
        rows = await db.fetch_all(query)
        if not rows:
            await interaction.followup.send("📭 Sin acumulación de tardanzas.", ephemeral=True)
            return
        lineas = [f"`{i}.` {r['nombre_completo']} — **{r['total']}** tardanzas" for i, r in enumerate(rows, 1)]
        embed = Embed(title="📋 Acumulación de Tardanzas", description="\n".join(lineas), color=Color.orange())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="📋 Ret. Hoy", style=discord.ButtonStyle.danger, row=1)
    async def lista_retirados_hoy(self, interaction, button):
        query = "SELECT nombre_completo, motivo_retiro FROM practicante WHERE fecha_retiro = $1 ORDER BY nombre_completo"
        await self._enviar_lista(interaction, "Retirados hoy", query, self.fecha)


# ──────────────────────────────────────────────
# Confirmación de eliminación (soft-delete)
# ──────────────────────────────────────────────
class ConfirmacionRetirar(discord.ui.View):
    def __init__(self, practicante_id, nombre, motivo, admin_id):
        super().__init__(timeout=60)
        self.practicante_id = practicante_id
        self.nombre = nombre
        self.motivo = motivo
        self.admin_id = admin_id

    @discord.ui.button(label="✅ Confirmar retiro", style=discord.ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button):
        await db.execute_query(
            "UPDATE practicante SET estado = 'retirado', fecha_retiro = CURRENT_DATE, motivo_retiro = $1 WHERE id = $2",
            self.motivo, self.practicante_id
        )
        # Crear reporte de retiro
        await db.execute_query(
            "INSERT INTO reporte (practicante_id, descripcion, tipo, creado_por) VALUES ($1, $2, 'retiro', $3)",
            self.practicante_id, f"Retirado: {self.motivo}", self.admin_id
        )
        await interaction.response.edit_message(
            content=f"✅ **{self.nombre}** ha sido retirado. Motivo: {self.motivo}",
            view=None
        )

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button):
        await interaction.response.edit_message(content="❌ Operación cancelada.", view=None)


# ──────────────────────────────────────────────
# Admin Cog
# ──────────────────────────────────────────────
class Admin(commands.GroupCog, name="admin"):
    """Cog para comandos administrativos"""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def _verificar_admin(self, interaction) -> bool:
        if not await es_admin_bot(interaction.user.id):
            await interaction.followup.send("❌ No tienes permisos de administrador.", ephemeral=True)
            return False
        return True

    async def _resolver_discord_id(self, usuario: str):
        """Resuelve un id de Discord a partir de mención, número o nombre parcial."""
        numeros = re.findall(r"\d+", usuario)
        if numeros:
            return int(numeros[0])

        row = await db.fetch_one(
            "SELECT id_discord FROM practicante WHERE LOWER(nombre_completo) LIKE LOWER($1) ORDER BY estado = 'activo' DESC, nombre_completo LIMIT 1",
            f"%{usuario}%",
        )
        return row['id_discord'] if row else None

    def _construir_embeds_historial(self, data):
        """Construye los 3 embeds del historial a partir de la data del backend."""
        h_semana = round(data.get('horasSemanalesSegundos', 0) / 3600.0, 1)
        h_total = round(data.get('horasTotalesSegundos', 0) / 3600.0, 1)
        h_recup_semana = round(data.get('horasRecuperacionSemanalesSegundos', 0) / 3600.0, 1)
        h_recup_total = round(data.get('horasRecuperacionSegundos', 0) / 3600.0, 1)
        h_base = round(data.get('horasBaseSegundos', 576 * 3600) / 3600.0, 1)
        incid_tardanza = data.get('incidenciasTardanza', 0)
        incid_sobre_hora = data.get('incidenciasSobreHora', 0)
        incid_baneo = data.get('incidenciasBaneo', 0)
        incid_falta = data.get('incidenciasFalta', 0)
        incid_inasistencia = data.get('incidenciasInasistencia', 0)
        reportes_list = data.get('reportes', [])

        h_falta_semana = max(0.0, 36.0 - (h_semana + h_recup_semana))
        h_falta_total = max(0.0, h_base - (h_total + h_recup_total))
        h_total_acumulado = round(h_total + h_recup_total, 1)

        registros = data.get('ultimosRegistros', [])
        historial_por_dia = defaultdict(list)
        for reg in registros:
            historial_por_dia[reg.get('fecha', 'Desconocido')].append(reg)
        fechas_ordenadas = list(historial_por_dia.keys())[:7]

        historial_text = ""
        if not fechas_ordenadas:
            historial_text = "No hay registros recientes.\n"
        else:
            for fecha in fechas_ordenadas:
                regs = historial_por_dia[fecha]
                historial_text += f"\n📅 **{fecha}**\n"
                for reg in regs:
                    he = reg.get('horaEntrada', '—')
                    if len(he) > 5:
                        he = he[:5]
                    hs = reg.get('horaSalida', '—')
                    if len(hs) > 5:
                        hs = hs[:5]
                    estado = reg.get('estado', '').upper()
                    recup = " (Recuperación)" if reg.get('esRecuperacion') else ""
                    solo_recup = " [Solo recup]" if reg.get('soloRecuperacion') else ""
                    historial_text += f"> {estado}{recup}{solo_recup} | 🟢 {he} - 🔴 {hs}\n"

        embed_historial = Embed(
            title=f"📋 Historial de Asistencia - {data.get('nombreCompleto', 'Desconocido')}",
            color=Color.blue(),
            description=historial_text.strip()
        )

        embed_semanal = Embed(
            title="📆 Resumen Semanal (Meta: 36h)",
            color=Color.green()
        )
        embed_semanal.add_field(
            name="Horas Trabajadas",
            value=f"🔸 **Normal:** {h_semana}h\n🔸 **Recuperación:** {h_recup_semana}h",
            inline=True
        )
        embed_semanal.add_field(
            name="Estado Semanal",
            value=f"🔻 **Falta para la meta:** {round(h_falta_semana, 1)}h",
            inline=True
        )

        incidencias_text = (
            f"⏱️ Tardanza: {incid_tardanza}\n"
            f"🔴 Sobre hora: {incid_sobre_hora}\n"
            f"⛔ Baneos: {incid_baneo}\n"
            f"📌 Faltas: {incid_falta}\n"
            f"🚫 Inasistencias: {incid_inasistencia}"
        )

        embed_total = Embed(
            title="📈 Resumen Histórico Total",
            color=Color.orange()
        )
        embed_total.add_field(
            name="Acumulado Global",
            value=(
                f"🎯 **Meta Total:** {h_base}h\n"
                f"🔸 **Total Llevado:** {h_total_acumulado}h\n"
                f"🔻 **Falta para concluir:** {round(h_falta_total, 1)}h"
            ),
            inline=True
        )
        embed_total.add_field(
            name="Incidencias",
            value=incidencias_text,
            inline=True
        )

        if reportes_list:
            resumen_reportes = defaultdict(list)
            for r in reportes_list:
                resumen_reportes[r.get('tipo', 'otros')].append(r.get('descripcion', 'Sin descripción'))

            reportes_text = f"**Total de reportes:** {len(reportes_list)}\n\n"
            for tipo, descs in resumen_reportes.items():
                reportes_text += f"▪️ **{tipo.upper()}** ({len(descs)}):\n"
                for d in set(descs):
                    linea = f"  - {d}\n"
                    if len(reportes_text) + len(linea) > 1000:
                        reportes_text += "  - ...y más\n"
                        break
                    reportes_text += linea
                if len(reportes_text) > 1000:
                    break

            embed_total.add_field(name="🚨 Detalle de Reportes", value=reportes_text, inline=False)

        return [embed_historial, embed_semanal, embed_total]

    # ──────────────────────────────────────────────
    # /admin registros — Dashboard de 14 métricas
    # ──────────────────────────────────────────────
    @app_commands.command(name='registros', description="Ver dashboard de asistencia del día")
    async def registros(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not await self._verificar_admin(interaction):
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

        # Construir embed
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

        embed.add_field(name="\u200b", value="\u200b", inline=False)  # Separator

        embed.add_field(
            name="✅ Presentes a tiempo",
            value=f"**{presentes}**",
            inline=True
        )
        embed.add_field(
            name="⏳ Faltan llegar",
            value=f"**{faltan}**",
            inline=True
        )
        embed.add_field(
            name="⚠️ Tardanzas (8:11-9:00)",
            value=f"**{tardanzas}**",
            inline=True
        )

        embed.add_field(
            name="🔴 Sobre hora (>9:00)",
            value=f"**{sobre_hora}**",
            inline=True
        )
        embed.add_field(
            name="❌ Faltas",
            value=f"**{faltas}**",
            inline=True
        )
        embed.add_field(
            name="📈 Tardanzas acumuladas",
            value=f"**{acum_tardanzas}**",
            inline=True
        )

        if retirados_hoy > 0:
            embed.add_field(
                name="🚪 Retirados hoy",
                value=f"**{retirados_hoy}**",
                inline=True
            )

        embed.set_footer(text=f"Hora del reporte: {ahora.strftime('%H:%M:%S')}")

        await interaction.followup.send(embed=embed, view=DashboardListasView(fecha), ephemeral=True)

    # ──────────────────────────────────────────────
    # /admin retirar — Soft-delete de practicante
    # ──────────────────────────────────────────────
    @app_commands.command(name='retirar', description="Retirar a un practicante (soft-delete)")
    @app_commands.describe(
        usuario="Practicante a retirar",
        motivo="Motivo del retiro"
    )
    async def retirar(self, interaction: discord.Interaction, usuario: discord.Member, motivo: str):
        await interaction.response.defer(ephemeral=True)
        if not await self._verificar_admin(interaction):
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

    # ──────────────────────────────────────────────
    # /admin listar_retirados
    # ──────────────────────────────────────────────
    @app_commands.command(name='listar_retirados', description="Ver lista de practicantes retirados")
    async def listar_retirados(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not await self._verificar_admin(interaction):
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

    # ──────────────────────────────────────────────
    # /admin reportar — Crear un reporte
    # ──────────────────────────────────────────────
    @app_commands.command(name='reportar', description="Crear un reporte para un practicante")
    @app_commands.describe(
        usuario="Practicante a reportar",
        tipo="Tipo de reporte",
        descripcion="Descripción del reporte"
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Llamada de atención", value="llamada_atencion"),
        app_commands.Choice(name="Justificación", value="justificacion"),
        app_commands.Choice(name="Baneo", value="baneo"),
        app_commands.Choice(name="Falta", value="falta"),
    ])
    async def reportar(self, interaction: discord.Interaction, usuario: discord.Member, tipo: str, descripcion: str):
        await interaction.response.defer(ephemeral=True)
        if not await self._verificar_admin(interaction):
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

    # ──────────────────────────────────────────────
    # /admin reportes — Ver reportes de un practicante
    # ──────────────────────────────────────────────
    @app_commands.command(name='reportes', description="Ver reportes de un practicante")
    @app_commands.describe(usuario="Practicante")
    async def reportes(self, interaction: discord.Interaction, usuario: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if not await self._verificar_admin(interaction):
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

    # ──────────────────────────────────────────────
    # /admin ausencia — Marcar días de clase
    # ──────────────────────────────────────────────
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
        if not await self._verificar_admin(interaction):
            return

        prac = await db.fetch_one(
            "SELECT id, nombre_completo FROM practicante WHERE id_discord = $1",
            usuario.id
        )
        if not prac:
            await interaction.followup.send("❌ Usuario no registrado.", ephemeral=True)
            return

        # Actualizar el día de clase (columna dinámica — nombre validado por choices)
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

    # ──────────────────────────────────────────────
    # /admin justificar — Justificar falta
    # ──────────────────────────────────────────────
    @app_commands.command(name='justificar', description="Justificar la inasistencia de un practicante")
    @app_commands.describe(
        usuario="Practicante a justificar",
        motivo="Motivo de la justificación"
    )
    async def justificar(self, interaction: discord.Interaction, usuario: discord.Member, motivo: str):
        await interaction.response.defer(ephemeral=True)
        if not await self._verificar_admin(interaction):
            return

        prac = await db.fetch_one(
            "SELECT id, nombre_completo FROM practicante WHERE id_discord = $1",
            usuario.id
        )
        if not prac:
            await interaction.followup.send("❌ Usuario no registrado.", ephemeral=True)
            return

        fecha = datetime.now(LIMA_TZ).date()

        # Crear reporte de justificación
        await db.execute_query(
            "INSERT INTO reporte (practicante_id, descripcion, tipo, fecha, creado_por) VALUES ($1, $2, 'justificacion', $3, $4)",
            prac['id'], motivo, fecha, interaction.user.id
        )

        await interaction.followup.send(
            f"✅ Justificación registrada para **{prac['nombre_completo']}** — {motivo}",
            ephemeral=True
        )

    # ──────────────────────────────────────────────
    # /admin eliminar_practicante — Soft-delete (alias)
    # ──────────────────────────────────────────────
    @app_commands.command(name='eliminar_practicante', description="Eliminar un practicante (soft-delete)")
    @app_commands.describe(usuario="Practicante a eliminar")
    async def eliminar_practicante(self, interaction: discord.Interaction, usuario: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if not await self._verificar_admin(interaction):
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

    # ──────────────────────────────────────────────
    # /admin reporte_hoy — Resumen para enviar a canal
    # ──────────────────────────────────────────────
    @app_commands.command(name='reporte_hoy', description="Generar reporte del día (público)")
    async def reporte_hoy(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not await es_admin_bot(interaction.user.id):
            await interaction.followup.send("❌ No tienes permisos.", ephemeral=True)
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

    # ──────────────────────────────────────────────
    # /admin asistencia_historial — Ver historial de otro practicante
    # ──────────────────────────────────────────────
    @app_commands.command(name='asistencia_historial', description="Ver historial de asistencia de un practicante por ID o nombre")
    @app_commands.describe(usuario="ID de Discord, mención o nombre del practicante")
    async def asistencia_historial(self, interaction: discord.Interaction, usuario: str):
        await interaction.response.defer(ephemeral=True)
        if not await self._verificar_admin(interaction):
            return

        discord_id = await self._resolver_discord_id(usuario)
        if not discord_id:
            await interaction.followup.send("❌ No se pudo resolver el practicante. Usa su ID de Discord o un nombre que coincida.", ephemeral=True)
            return

        try:
            async with aiohttp.ClientSession() as session:
                backend_url = getattr(self.bot, '_backend_url', 'http://backend:9090/api/v1')
                base_api_url = backend_url.replace('/v1', '')
                url = f"{base_api_url}/asistencia/historial/{discord_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        embeds = self._construir_embeds_historial(data)
                        for embed in embeds:
                            await interaction.followup.send(embed=embed, ephemeral=True)
                    elif response.status == 404:
                        await interaction.followup.send("📭 No hay registros de asistencia para este practicante.", ephemeral=True)
                    else:
                        await interaction.followup.send(f"❌ Error al consultar el historial: HTTP {response.status}", ephemeral=True)
        except Exception as e:
            logging.error(f"Error llamando al API de historial admin para {discord_id}: {e}")
            await interaction.followup.send("❌ Hubo un error al contactar con el servidor.", ephemeral=True)

    @asistencia_historial.autocomplete('usuario')
    async def asistencia_historial_autocomplete(self, interaction: discord.Interaction, current: str):
        term = current.strip()
        if not term:
            term = ""

        rows = await db.fetch_all(
            """
            SELECT id_discord, nombre_completo
            FROM practicante
            WHERE LOWER(nombre_completo) LIKE LOWER($1)
               OR CAST(id_discord AS TEXT) LIKE $1
            ORDER BY estado = 'activo' DESC, nombre_completo
            LIMIT 25
            """,
            f"%{term}%",
        )

        opciones = []
        for r in rows:
            nombre = r['nombre_completo']
            did = str(r['id_discord'])
            opciones.append(app_commands.Choice(name=f"{nombre} ({did})", value=did))
        return opciones


async def setup(bot):
    await bot.add_cog(Admin(bot))

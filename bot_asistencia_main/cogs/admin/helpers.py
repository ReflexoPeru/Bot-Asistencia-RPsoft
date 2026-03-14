import re
from collections import defaultdict
from typing import Optional
from discord import Embed, Color
from utils import es_admin_bot
import database as db
async def verificar_admin(interaction) -> bool:
    """Valida si el usuario es admin y responde en caso contrario."""
    if not await es_admin_bot(interaction.user.id):
        await interaction.followup.send("❌ No tienes permisos de administrador.", ephemeral=True)
        return False
    return True
async def resolver_discord_id(usuario: str) -> Optional[int]:
    """Resuelve un id de Discord a partir de mención, número o nombre parcial."""
    numeros = re.findall(r"\d+", usuario)
    if numeros:
        return int(numeros[0])
    row = await db.fetch_one(
        "SELECT id_discord FROM practicante WHERE LOWER(nombre_completo) LIKE LOWER($1) ORDER BY estado = 'activo' DESC, nombre_completo LIMIT 1",
        f"%{usuario}%",
    )
    return row['id_discord'] if row else None
def construir_embeds_historial(data):
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

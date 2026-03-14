import logging
import discord
from discord import app_commands, Embed, Color
import aiohttp
import database as db


class HistorialCommands:
    """Comando para consultar el historial propio de asistencia."""

    @app_commands.command(name='historial', description="Ver tu historial de asistencia")
    async def historial(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        discord_id = interaction.user.id

        try:
            async with aiohttp.ClientSession() as session:
                backend_url = getattr(self.bot, '_backend_url', 'http://backend:9090/api/v1')
                base_api_url = backend_url.replace('/v1', '')
                url = f"{base_api_url}/asistencia/historial/{discord_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        await self._enviar_historial(interaction, data)
                    elif response.status == 404:
                        await interaction.followup.send("📭 No tienes registros de asistencia o no estás registrado.", ephemeral=True)
                    else:
                        await interaction.followup.send(f"❌ Error al consultar el historial: HTTP {response.status}", ephemeral=True)
        except Exception as e:
            logging.error(f"Error llamando al API de historial para {discord_id}: {e}")
            await interaction.followup.send("❌ Hubo un error al contactar con el servidor.", ephemeral=True)

    async def _enviar_historial(self, interaction: discord.Interaction, data):
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
        from collections import defaultdict
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
        await interaction.followup.send(embed=embed_historial, ephemeral=True)

        embed_semanal = Embed(title="📆 Resumen Semanal (Meta: 36h)", color=Color.green())
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
        await interaction.followup.send(embed=embed_semanal, ephemeral=True)

        incidencias_text = (
            f"⏱️ Tardanza: {incid_tardanza}\n"
            f"🔴 Sobre hora: {incid_sobre_hora}\n"
            f"⛔ Baneos: {incid_baneo}\n"
            f"📌 Faltas: {incid_falta}\n"
            f"🚫 Inasistencias: {incid_inasistencia}"
        )

        embed_total = Embed(title="📈 Resumen Histórico Total", color=Color.orange())
        embed_total.add_field(
            name="Acumulado Global",
            value=(
                f"🎯 **Meta Total:** {h_base}h\n"
                f"🔸 **Total Llevado:** {h_total_acumulado}h\n"
                f"🔻 **Falta para concluir:** {round(h_falta_total, 1)}h"
            ),
            inline=True
        )
        embed_total.add_field(name="Incidencias", value=incidencias_text, inline=True)

        if reportes_list:
            from collections import defaultdict
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

        await interaction.followup.send(embed=embed_total, ephemeral=True)

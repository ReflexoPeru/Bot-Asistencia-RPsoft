"""Comandos del módulo de asistencia"""

import discord
from discord import app_commands, Embed, Color
from discord.ext import commands
from utils import obtener_practicante, verificar_entrada, canal_permitido, tiene_clase_hoy_por_id
from datetime import datetime, time, timedelta
import database as db
import logging

from bot.config.constants import (
    HORARIO_ENTRADA_INICIO,
    HORARIO_ENTRADA_FIN,
    HORA_LIMITE_TARDANZA,
    HORARIO_ENTRADA_TOLERANCIA,
    HORA_SALIDA_OFICIAL,
    HORA_GRACIA_SALIDA,
    HORARIO_SALIDA_MINIMA,
)


class Asistencia(commands.GroupCog, name="asistencia"):
    """Cog para gestionar comandos de asistencia como subcomandos agrupados"""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    # ──────────────────────────────────────────────
    # /asistencia entrada
    # ──────────────────────────────────────────────
    @app_commands.command(name='entrada', description="Registrar tu entrada de asistencia")
    async def entrada(self, interaction: discord.Interaction):
        from utils import es_domingo, LIMA_TZ
        await interaction.response.defer(ephemeral=True)

        # 1. Bloquear domingos
        if es_domingo():
            await interaction.followup.send(
                "🚫 No se pueden registrar asistencias los domingos.",
                ephemeral=True
            )
            return

        if not await canal_permitido(interaction):
            return

        discord_id = interaction.user.id
        nombre_usuario = interaction.user.mention

        practicante_id = await obtener_practicante(interaction, discord_id, usar_followup=True)
        if not practicante_id:
            return

        ahora = datetime.now(LIMA_TZ)
        fecha_actual = ahora.date()
        hora_actual = ahora.time().replace(microsecond=0)

        # 2. Verificar horario permitido
        if hora_actual < HORARIO_ENTRADA_INICIO:
            await interaction.followup.send(
                f"⏳ El registro de asistencia aún no está habilitado. "
                f"Disponible a partir de las {HORARIO_ENTRADA_INICIO.strftime('%H:%M')}hs.",
                ephemeral=True
            )
            return

        if hora_actual > HORARIO_ENTRADA_FIN:
            await interaction.followup.send(
                "🚫 El horario de asistencia ya cerró. No puedes registrar entrada.",
                ephemeral=True
            )
            return

        # 3. Verificar si ya registró
        existente = await verificar_entrada(interaction, discord_id, fecha_actual, usar_followup=True)
        if existente:
            from utils import format_timedelta
            hora_str = format_timedelta(existente['hora_entrada'])
            await interaction.followup.send(
                f"⚠️ Ya registraste tu entrada hoy a las {hora_str}.\n"
                f"Usá `/asistencia salida` para registrar tu salida.",
                ephemeral=True
            )
            return

        # 4. Verificar si tiene clases hoy
        if await tiene_clase_hoy_por_id(practicante_id):
            # Registrar como 'clases'
            query = """
            INSERT INTO asistencia (practicante_id, estado, fecha, hora_entrada)
            VALUES ($1, 'clases', $2, $3)
            """
            await db.execute_query(query, practicante_id, fecha_actual, hora_actual)

            embed = Embed(title="📚 Entrada registrada (día de clases)", color=Color.blue())
            embed.add_field(name="👤 Practicante", value=nombre_usuario, inline=False)
            embed.add_field(name="📅 Fecha", value=fecha_actual.strftime('%d-%m-%Y'), inline=True)
            embed.add_field(name="🕐 Hora", value=hora_actual.strftime('%H:%M'), inline=True)
            embed.set_footer(text="Hoy tiene clases registradas. Su asistencia es parcial.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # 5. Determinar estado basado en la hora
        if hora_actual <= HORARIO_ENTRADA_TOLERANCIA:
            estado = 'temprano'
            color = Color.green()
            titulo = "✅ Entrada registrada — A tiempo"
        elif hora_actual <= HORA_LIMITE_TARDANZA:
            estado = 'tarde'
            color = Color.yellow()
            titulo = "⚠️ Entrada registrada — Tardanza"
        else:
            estado = 'sobreHora'
            color = Color.red()
            titulo = "🔴 Entrada registrada — Sobre hora"

        # 6. Si es tardanza o sobreHora, pedir justificación via modal
        if estado in ('tarde', 'sobreHora'):
            from utils import ModalJustificacion
            modal = ModalJustificacion(
                practicante_id=practicante_id,
                fecha=fecha_actual,
                hora_entrada=hora_actual,
                estado=estado,
            )
            # Necesitamos responder con modal, pero ya hicimos defer.
            # En su lugar, registramos y pedimos justificación después.
            query = """
            INSERT INTO asistencia (practicante_id, estado, fecha, hora_entrada)
            VALUES ($1, $2, $3, $4)
            """
            await db.execute_query(query, practicante_id, estado, fecha_actual, hora_actual)

            # Crear reporte de tardanza automático
            query_reporte = """
            INSERT INTO reporte (practicante_id, descripcion, tipo, fecha)
            VALUES ($1, $2, $3, $4)
            """
            desc_tardanza = f"Llegada tarde a las {hora_actual.strftime('%H:%M')} (estado: {estado})"
            tipo_reporte = 'sobreHora' if estado == 'sobreHora' else 'tardanza'
            await db.execute_query(query_reporte, practicante_id, desc_tardanza, tipo_reporte, fecha_actual)

            logging.info(f'Asistencia ({estado}) registrada para {interaction.user.display_name}')

            embed = Embed(title=titulo, color=color)
            embed.add_field(name="👤 Practicante", value=nombre_usuario, inline=False)
            embed.add_field(name="📅 Fecha", value=fecha_actual.strftime('%d-%m-%Y'), inline=True)
            embed.add_field(name="🕐 Hora de entrada", value=hora_actual.strftime('%H:%M'), inline=True)
            embed.add_field(name="📊 Estado", value=estado.upper(), inline=True)
            embed.set_footer(text="Se generó un reporte de tardanza automáticamente.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # 7. Registrar entrada temprano (sin reporte)
        query = """
        INSERT INTO asistencia (practicante_id, estado, fecha, hora_entrada)
        VALUES ($1, $2, $3, $4)
        """
        await db.execute_query(query, practicante_id, estado, fecha_actual, hora_actual)

        logging.info(f'Asistencia ({estado}) registrada para {interaction.user.display_name}')

        embed = Embed(title=titulo, color=color)
        embed.add_field(name="👤 Practicante", value=nombre_usuario, inline=False)
        embed.add_field(name="📅 Fecha", value=fecha_actual.strftime('%d-%m-%Y'), inline=True)
        embed.add_field(name="🕐 Hora de entrada", value=hora_actual.strftime('%H:%M'), inline=True)
        embed.add_field(name="📊 Estado", value=estado.upper(), inline=True)
        embed.set_footer(text=f"Recuerda marcar tu salida antes de las {HORA_GRACIA_SALIDA.strftime('%H:%M')}hs.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ──────────────────────────────────────────────
    # /asistencia salida
    # ──────────────────────────────────────────────
    @app_commands.command(name='salida', description="Registrar tu salida de asistencia")
    async def salida(self, interaction: discord.Interaction):
        from utils import es_domingo, LIMA_TZ, format_timedelta
        await interaction.response.defer(ephemeral=True)

        if es_domingo():
            await interaction.followup.send(
                "🚫 No se pueden registrar asistencias los domingos.",
                ephemeral=True
            )
            return

        if not await canal_permitido(interaction):
            return

        discord_id = interaction.user.id
        nombre_usuario = interaction.user.mention

        practicante_id = await obtener_practicante(interaction, discord_id, usar_followup=True)
        if not practicante_id:
            return

        ahora = datetime.now(LIMA_TZ)
        fecha_actual = ahora.date()
        hora_actual = ahora.time().replace(microsecond=0)

        # 1. Verificar que existe una entrada hoy
        query_entrada = """
        SELECT id, hora_entrada, hora_salida, estado FROM asistencia
        WHERE practicante_id = $1 AND fecha = $2
        """
        registro = await db.fetch_one(query_entrada, practicante_id, fecha_actual)

        if not registro:
            await interaction.followup.send(
                "⚠️ No tienes una entrada registrada hoy. "
                "Usá `/asistencia entrada` primero.",
                ephemeral=True
            )
            return

        if registro['hora_salida'] is not None:
            hora_sal = format_timedelta(registro['hora_salida'])
            await interaction.followup.send(
                f"⚠️ Ya registraste tu salida hoy a las {hora_sal}.",
                ephemeral=True
            )
            return

        # 2. Determinar hora de salida
        mensaje_extra = ""
        if hora_actual > HORA_GRACIA_SALIDA:
            # Ya pasó la gracia → registrar a las 14:00
            hora_salida_db = HORA_SALIDA_OFICIAL
            mensaje_extra = f"\n💡 Registraste tarde. Se marcó salida a las {HORA_SALIDA_OFICIAL.strftime('%H:%M')}."
        elif hora_actual < HORARIO_SALIDA_MINIMA:
            hora_salida_db = hora_actual
            mensaje_extra = "\n⚠️ Salida temprana registrada."
        else:
            hora_salida_db = hora_actual

        # 3. Actualizar registro
        query_update = """
        UPDATE asistencia SET hora_salida = $1 WHERE id = $2
        """
        await db.execute_query(query_update, hora_salida_db, registro['id'])

        logging.info(f'Salida registrada para {interaction.user.display_name} a las {hora_salida_db}')

        # 4. Calcular duración
        hora_entrada = registro['hora_entrada']
        if isinstance(hora_entrada, timedelta):
            hora_entrada_time = (datetime.min + hora_entrada).time()
        else:
            hora_entrada_time = hora_entrada

        dt_inicio = datetime.combine(fecha_actual, hora_entrada_time)
        dt_fin = datetime.combine(fecha_actual, hora_salida_db)
        duracion = dt_fin - dt_inicio
        horas = duracion.seconds // 3600
        minutos = (duracion.seconds % 3600) // 60

        # 5. Embed de respuesta
        embed = Embed(title="✅ Salida registrada", color=Color.blue())
        embed.add_field(name="👤 Practicante", value=nombre_usuario, inline=False)
        embed.add_field(name="📅 Fecha", value=fecha_actual.strftime('%d-%m-%Y'), inline=True)
        embed.add_field(
            name="🟢 Entrada | 🔴 Salida",
            value=f"{hora_entrada_time.strftime('%H:%M')} | {hora_salida_db.strftime('%H:%M')}",
            inline=True
        )
        embed.add_field(name="⏱️ Tiempo trabajado", value=f"{horas}h {minutos}min", inline=False)

        if mensaje_extra:
            embed.set_footer(text=mensaje_extra.strip())

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ──────────────────────────────────────────────
    # /asistencia estado
    # ──────────────────────────────────────────────
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

        # Asistencia de hoy
        query = """
        SELECT estado, hora_entrada, hora_salida, salida_auto FROM asistencia
        WHERE practicante_id = $1 AND fecha = $2
        """
        registro = await db.fetch_one(query, practicante_id, fecha_actual)

        # Recuperación de hoy
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

    # ──────────────────────────────────────────────
    # /asistencia historial
    # ──────────────────────────────────────────────
    @app_commands.command(name='historial', description="Ver tu historial de asistencia")
    async def historial(self, interaction: discord.Interaction):
        import aiohttp
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
                        
                        embed = Embed(title=f"📊 Historial de asistencia - {data.get('nombreCompleto', 'Desconocido')}", color=Color.blue())
                        
                        # Horas convertidas de segundos a horas redondeadas a 1 decimal
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

                        h_falta_semana = max(0.0, 36.0 - (h_semana + h_recup_semana)) # límite de 36h pedido
                        h_falta_total = max(0.0, h_base - (h_total + h_recup_total))
                        h_total_acumulado = round(h_total + h_recup_total, 1)

                        registros = data.get('ultimosRegistros', [])
                        
                        # Agrupar registros por día
                        from collections import defaultdict
                        historial_por_dia = defaultdict(list)
                        for reg in registros:
                            historial_por_dia[reg.get('fecha', 'Desconocido')].append(reg)
                        
                        fechas_ordenadas = list(historial_por_dia.keys())[:7] # últimos 7 días con registros
                        
                        historial_text = ""
                        if not fechas_ordenadas:
                            historial_text = "No hay registros recientes.\n"
                        else:
                            for fecha in fechas_ordenadas:
                                regs = historial_por_dia[fecha]
                                historial_text += f"\n📅 **{fecha}**\n"
                                for reg in regs:
                                    he = reg.get('horaEntrada', '—') # Formato viene del java .toString() o --:--
                                    if len(he) > 5: he = he[:5]      # Sólo HH:MM 
                                    hs = reg.get('horaSalida', '—')
                                    if len(hs) > 5: hs = hs[:5]
                                    estado = reg.get('estado', '').upper()
                                    recup = " (Recuperación)" if reg.get('esRecuperacion') else ""
                                    solo_recup = " [Solo recup]" if reg.get('soloRecuperacion') else ""
                                    historial_text += f"> {estado}{recup}{solo_recup} | 🟢 {he} - 🔴 {hs}\n"

                        # ----- MENSAJE 1: HISTORIAL DE DIAS -----
                        embed_historial = Embed(
                            title=f"📋 Historial de Asistencia - {data.get('nombreCompleto', 'Desconocido')}",
                            color=Color.blue(),
                            description=historial_text.strip()
                        )
                        await interaction.followup.send(embed=embed_historial, ephemeral=True)

                        # ----- MENSAJE 2: RESUMEN SEMANAL -----
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
                        await interaction.followup.send(embed=embed_semanal, ephemeral=True)

                        # ----- MENSAJE 3: RESUMEN TOTAL / MENSUAL -----
                        embed_total = Embed(
                            title="📈 Resumen Histórico Total",
                            color=Color.orange()
                        )
                        embed_total.add_field(
                            name="Acumulado Global",
                            value=f"🎯 **Meta Total:** {h_base}h\n🔸 **Total Llevado:** {h_total_acumulado}h\n🔻 **Falta para concluir:** {round(h_falta_total, 1)}h",
                            inline=True
                        )
                        incidencias_text = (
                            f"⏱️ Tardanza: {incid_tardanza}\n"
                            f"🔴 Sobre hora: {incid_sobre_hora}\n"
                            f"⛔ Baneos: {incid_baneo}\n"
                            f"📌 Faltas: {incid_falta}\n"
                            f"🚫 Inasistencias: {incid_inasistencia}"
                        )
                        embed_total.add_field(
                            name="Incidencias",
                            value=incidencias_text,
                            inline=True
                        )

                        # Reportes en el tercer mensaje
                        if reportes_list:
                            resumen_reportes = defaultdict(list)
                            for r in reportes_list:
                                resumen_reportes[r.get('tipo', 'otros')].append(r.get('descripcion', 'Sin descripción'))
                            
                            reportes_text = f"**Total de reportes:** {len(reportes_list)}\n\n"
                            
                            for tipo, descs in resumen_reportes.items():
                                reportes_text += f"▪️ **{tipo.upper()}** ({len(descs)}):\n"
                                # Para no exceder de 1024 caracteres
                                for d in set(descs):
                                    linea = f"  - {d}\n"
                                    if len(reportes_text) + len(linea) > 1000:
                                        reportes_text += "  - ...y más\n"
                                        break
                                    reportes_text += linea
                                if len(reportes_text) > 1000: break
                                
                            embed_total.add_field(name="🚨 Detalle de Reportes", value=reportes_text, inline=False)

                        await interaction.followup.send(embed=embed_total, ephemeral=True)
                    elif response.status == 404:
                         await interaction.followup.send("📭 No tienes registros de asistencia o no estás registrado.", ephemeral=True)
                    else:
                        await interaction.followup.send(f"❌ Error al consultar el historial: HTTP {response.status}", ephemeral=True)
        except Exception as e:
            logging.error(f"Error llamando al API de historial para {discord_id}: {e}")
            await interaction.followup.send("❌ Hubo un error al contactar con el servidor.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Asistencia(bot))

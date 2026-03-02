"""Comandos del módulo de asistencia"""

import discord
from discord import app_commands, Embed, Color
from discord.ext import commands
from utils import obtener_practicante, verificar_entrada, obtener_estado_asistencia, canal_permitido
from datetime import datetime, time, timedelta
import database as db
import logging

from bot.config.constants import HORARIO_ENTRADA_INICIO, HORARIO_ENTRADA_FIN, HORA_LIMITE_TARDANZA, HORAS_SEMANALES_REQUERIDAS

class Asistencia(commands.GroupCog, name="asistencia"):
    """Cog para gestionar comandos de asistencia"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.MAX_SESSION_HOURS = 6  # Límite de horas por sesión para evitar "farming"

    @app_commands.command(name='entrada', description="Registrar tu hora de entrada")
    async def entrada(self, interaction: discord.Interaction):
        from utils import es_domingo, LIMA_TZ
        await interaction.response.defer(ephemeral=True)
        
        # Bloquear domingos
        if es_domingo():
            await interaction.followup.send(
                "⛔ **Día Domingo, No laboral**\nLos comandos de asistencia están deshabilitados los domingos.",
                ephemeral=True
            )
            return
        
        if not await canal_permitido(interaction):
            logging.warning(f'Canal no permitido para el usuario {interaction.user.display_name}.')
            return

        discord_id = interaction.user.id
        nombre_usuario = interaction.user.mention
        logging.info(f'Usuario {interaction.user.display_name} está intentando registrar entrada.')
        practicante_id = await obtener_practicante(interaction, discord_id)
        if not practicante_id:
            logging.warning(f'Practicante no encontrado para el usuario {interaction.user.display_name}.')
            return

        fecha_actual = datetime.now(LIMA_TZ).date()
        hora_actual = datetime.now(LIMA_TZ).time()
        
        # Verificar si es antes de la hora permitida
        if hora_actual < HORARIO_ENTRADA_INICIO:
             await interaction.followup.send(
                f"Hola {nombre_usuario}, La hora de entrada no es la correcta, marca asistencia desde las {HORARIO_ENTRADA_INICIO.strftime('%H:%M')} AM.",
                ephemeral=True
            )
             return

        # Verificar si la hora actual está dentro del rango permitido (o pasado las 14:00)
        if not (HORARIO_ENTRADA_INICIO <= hora_actual <= HORARIO_ENTRADA_FIN):
            await interaction.followup.send(
                f"{nombre_usuario}, no puedes registrar tu entrada fuera del horario permitido.",
                ephemeral=True
            )
            return

        asistencia_existente = await verificar_entrada(practicante_id, fecha_actual)
        
        # Si ya existe una entrada para hoy, informar al usuario
        if asistencia_existente:
            await interaction.followup.send(
                f"{nombre_usuario}, ya has registrado tu entrada el día de hoy.",
                ephemeral=True
            )
            return

        # Determinar estado de asistencia
        if hora_actual > HORA_LIMITE_TARDANZA:
            estado_id = await obtener_estado_asistencia('Tardanza')
            mensaje = f"{nombre_usuario}, se ha registrado tu entrada a las {hora_actual.strftime('%H:%M')} con tardanza."
        else:
            estado_id = await obtener_estado_asistencia('Presente')
            mensaje = f"{nombre_usuario}, se ha registrado tu entrada a las {hora_actual.strftime('%H:%M')}."
            
        if not estado_id:
            await interaction.followup.send(
                f"{nombre_usuario}, no se registró tu asistencia el día de hoy.",
                ephemeral=True
            )
            return
            
        query_insert_asistencia = """
        INSERT INTO asistencia (practicante_id, fecha, hora_entrada, estado_id)
        VALUES (%s, %s, %s, %s)
        """
        await db.execute_query(query_insert_asistencia, (practicante_id, fecha_actual, hora_actual, estado_id))
        logging.info(f'Entrada registrada para el usuario {interaction.user.display_name}.')
        await interaction.followup.send(mensaje, ephemeral=True)

    @app_commands.command(name='salida', description="Registrar tu hora de salida")
    async def salida(self, interaction: discord.Interaction):
        from utils import es_domingo, LIMA_TZ
        await interaction.response.defer(ephemeral=True)
        
        # Bloquear domingos
        if es_domingo():
            await interaction.followup.send(
                "⛔ **Día Domingo, No laboral**\nLos comandos de asistencia están deshabilitados los domingos.",
                ephemeral=True
            )
            return
        
        if not await canal_permitido(interaction):
            logging.warning(f'Canal no permitido para el usuario {interaction.user.display_name}.')
            return
        
        discord_id = interaction.user.id
        nombre_usuario = interaction.user.mention
        logging.info(f'Usuario {interaction.user.display_name} está intentando registrar salida.')
        
        practicante_id = await obtener_practicante(interaction, discord_id)
        if not practicante_id:
            logging.warning(f'Practicante no encontrado para el usuario {interaction.user.display_name}.')
            return

        fecha_actual = datetime.now(LIMA_TZ).date()
        query_asistencia = "SELECT id, hora_salida, hora_entrada FROM asistencia WHERE practicante_id = %s AND fecha = %s"
        asistencia = await db.fetch_one(query_asistencia, (practicante_id, fecha_actual))
        
        if not asistencia:
            await interaction.followup.send(
                f"{nombre_usuario}, no has registrado tu entrada el día de hoy.",
                ephemeral=True
            )
            return

        if asistencia['hora_salida']:
            await interaction.followup.send(
                f"{nombre_usuario}, ya has registrado tu salida el día de hoy.",
                ephemeral=True
            )
            return

        hora_actual = datetime.now(LIMA_TZ).time()
        hora_limite_practicas = time(14, 30)
        
        mensaje_extra = ""
        horas_extra_str = "00:00:00"
        
        # Lógica Anti-Farming: Soft Cap a las 14:30
        if hora_actual > hora_limite_practicas:
            # Calcular horas extra (desde las 14:30 hasta la hora real de salida)
            dt_actual = datetime.combine(fecha_actual, hora_actual)
            dt_limite = datetime.combine(fecha_actual, hora_limite_practicas)
            duration_extra = dt_actual - dt_limite
            
            # Formatear duración extra
            total_seconds = int(duration_extra.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            horas_extra_display = f"{hours} horas, {minutes} minutos y {seconds} segundos"
            horas_extra_str = f"{hours:02}:{minutes:02}:{seconds:02}"

            # La hora oficial de salida se marca a las 14:30
            hora_salida_db = hora_limite_practicas
            
            mensaje_extra = (
                f"\n\n⚠️ **AntiFarming: Salida fuera de horas de práctica detectada** ⚠️\n"
                f"Las horas que hayas hecho desde las 14:30 PM hasta las {hora_actual.strftime('%H:%M')} (**{horas_extra_display}**) "
                f"**pueden llegar a no ser contadas**.\n"
                f"Informa a un líder o a Renso para que puedan validarte esas horas mostrando el trabajo que realizaste. "
                f"Caso contrario, las horas no se verán reflejadas en tu conteo."
            )
            logging.warning(f"Anti-Farming triggered for {interaction.user.display_name}: {horas_extra_display} extra.")
        else:
            # Salida normal dentro del horario
            hora_salida_db = hora_actual

        if hora_actual < time(14, 0):
            # Salida anticipada: registrar y advertir
            # Nota: Si es anticipada (antes de las 14:00), no hay horas extra
            query_update_salida = "UPDATE asistencia SET hora_salida = %s, horas_extra = %s WHERE id = %s"
            await db.execute_query(query_update_salida, (hora_salida_db, '00:00:00', asistencia['id']))
            
            logging.warning(f'Salida anticipada registrada para el usuario {interaction.user.display_name}.')
            
            mensaje_alerta = (
                f"⚠️ **SALIDA ANTICIPADA DETECTADA** ⚠️\n\n"
                f"{nombre_usuario}, tu salida ha sido registrada a las **{hora_actual.strftime('%H:%M')}**.\n\n"
                f"🔴 **ATENCIÓN:** Debes informar a un **Líder encargado** o al **equipo de desarrollo del bot** al retirarte."
            )
            await interaction.followup.send(mensaje_alerta, ephemeral=True)
        else:
            # Salida normal (o post 14:30)
            query_update_salida = "UPDATE asistencia SET hora_salida = %s, horas_extra = %s WHERE id = %s"
            await db.execute_query(query_update_salida, (hora_salida_db, horas_extra_str, asistencia['id']))
            
            logging.info(f'Salida registrada para el usuario {interaction.user.display_name}.')
            await interaction.followup.send(
                f"✅ {nombre_usuario}, se ha registrado tu salida a las **{hora_actual.strftime('%H:%M')}**.{mensaje_extra}",
                ephemeral=True
            )

    @app_commands.command(name='estado', description="Consultar tu estado de asistencia del día")
    async def estado(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        from utils import LIMA_TZ
        if not await canal_permitido(interaction):
            logging.warning(f'Canal no permitido para el usuario {interaction.user.display_name}.')
            return

        discord_id = interaction.user.id
        nombre_usuario = interaction.user.display_name
        logging.info(f'Usuario {nombre_usuario} está consultando su estado de asistencia.')
        practicante_id = await obtener_practicante(interaction, discord_id)
        if not practicante_id:
            logging.warning(f'Practicante no encontrado para el usuario {interaction.user.display_name}.')
            return
            
        # Consultar estado de asistencia
        fecha_actual = datetime.now(LIMA_TZ).date()
        query_estado = """
        SELECT a.hora_entrada, a.hora_salida, ea.estado
        FROM asistencia a
        INNER JOIN estado_asistencia ea ON a.estado_id = ea.id
        WHERE a.practicante_id = %s AND a.fecha = %s
        """
        resultado = await db.fetch_one(query_estado, (practicante_id, fecha_actual))
        
        # Embed de respuesta
        embed = Embed(
            title=f"📍 Estado de Asistencia para hoy, {nombre_usuario}",
            color=Color.orange()
        )

        if resultado:
            # Si tiene un registro, mostrar el estado, hora de entrada y salida
            embed.add_field(name="✅ Estado de Asistencia", value=f"**{resultado['estado']}**", inline=False)
            embed.add_field(name="🕒 Hora de Entrada", value=f"{resultado['hora_entrada'] or 'No registrada'}", inline=False)
            embed.add_field(name="⏳ Hora de Salida", value=f"{resultado['hora_salida'] or 'No registrada'}", inline=False)
        else:
            # Si no tiene registro, lógica diferenciada por hora
            hora_actual = datetime.now(LIMA_TZ).time()
            hora_espera_limite = time(9, 0)
            
            if hora_actual < hora_espera_limite:
                 embed.add_field(name="🟡 Estado de Asistencia", value="Esperando al inicio de Jornada", inline=False)
            else:
                 embed.add_field(name="❌ Estado de Asistencia", value="Falta injustificada", inline=False)

        # --- Sección de Recuperación ---
        query_rec = """
        SELECT hora_entrada, hora_salida, estado,
               TIMESTAMPDIFF(MINUTE, hora_entrada, hora_salida) AS rec_minutos
        FROM asistencia_recuperacion
        WHERE practicante_id = %s AND fecha_recuperacion = %s
        ORDER BY id DESC LIMIT 1
        """
        rec = await db.fetch_one(query_rec, (practicante_id, fecha_actual))

        if rec and rec['estado'] == 'valido':
            from utils import format_timedelta
            rec_entrada = format_timedelta(rec['hora_entrada'])
            rec_salida = format_timedelta(rec['hora_salida'])
            minutos = rec['rec_minutos'] or 0
            horas_rec = minutos // 60
            mins_rec = minutos % 60
            embed.add_field(
                name="⏰ Horas de Recuperación",
                value=f"🟢 Inicio: {rec_entrada} | 🔴 Fin: {rec_salida}\n⏱️ Total recuperado: {horas_rec} hs {mins_rec} min",
                inline=False
            )
        elif rec and rec['estado'] == 'abierto':
            from utils import format_timedelta
            rec_entrada = format_timedelta(rec['hora_entrada'])
            embed.add_field(
                name="⏰ Horas de Recuperación",
                value=f"🟢 Inicio: {rec_entrada} | ⏳ En curso...",
                inline=False
            )
        elif rec and rec['estado'] == 'invalidado':
            embed.add_field(
                name="⏰ Horas de Recuperación",
                value="❌ Invalidada por advertencias acumuladas",
                inline=False
            )
        else:
            embed.add_field(
                name="⏰ Horas de Recuperación",
                value="No registradas",
                inline=False
            )

        embed.set_footer(text="Si tienes dudas, contacta con el administrador.")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='historial', description="Consultar tu historial de asistencia")
    @app_commands.describe(dias="Cantidad de días a mostrar (1-15)")
    async def historial(self, interaction: discord.Interaction, dias: int = 7):
        await interaction.response.defer(ephemeral=True)
        from utils import canal_permitido, obtener_practicante
        if not await canal_permitido(interaction):
            return

        discord_id = interaction.user.id
        nombre_usuario = interaction.user.mention
        logging.info(f'Usuario {interaction.user.display_name} está consultando su historial de asistencia.')
        practicante_id = await obtener_practicante(interaction, discord_id)
        if not practicante_id:
            logging.warning(f'Practicante no encontrado para el usuario {interaction.user.display_name}.')
            return
        
        # Validar el rango de días
        if dias < 1 or dias > 15:
            await interaction.followup.send(
                f"{nombre_usuario}, el número de días debe estar entre 1 y 15.",
                ephemeral=True
            )
            return
        
        fecha_actual = datetime.now().date()
        fecha_inicio = fecha_actual - timedelta(days=dias)

        query_historial = """
            SELECT date_format(a.fecha, '%%m-%%d') as fecha, a.hora_entrada, a.hora_salida, ea.estado,
                   ar.hora_entrada AS rec_entrada,
                   ar.hora_salida  AS rec_salida,
                   ar.estado       AS rec_estado,
                   TIMESTAMPDIFF(MINUTE, ar.hora_entrada, ar.hora_salida) AS rec_minutos
            FROM asistencia a
            INNER JOIN estado_asistencia ea ON ea.id = a.estado_id
            LEFT JOIN asistencia_recuperacion ar
              ON ar.practicante_id = a.practicante_id
              AND ar.fecha_recuperacion = a.fecha
              AND ar.estado IN ('valido', 'invalidado')
            WHERE a.practicante_id = %s AND a.fecha >= %s
            ORDER BY a.fecha DESC
        """

        resultados = await db.fetch_all(query_historial, (practicante_id, fecha_inicio))

        if not resultados:
            await interaction.followup.send(
                f"{nombre_usuario}, no se encontraron registros en los últimos {dias} días.",
                ephemeral=True
            )
            return
        
        # Crear el Embed para el historial
        embed = Embed(
            title=f"📅 Historial de Asistencia - Últimos {dias} días",
            description=f"**{interaction.user.display_name}**, aquí está tu historial de asistencia para los últimos {dias} días:",
            color=Color.blue()
        )

        # Recorrer los resultados y añadirlos al Embed
        for resultado in resultados:
            fecha = resultado['fecha']
            entrada = resultado['hora_entrada'] or 'No registrada'
            salida = resultado['hora_salida'] or 'No registrada'
            estado = resultado['estado'] or 'Falta injustificada'

            # Añadir el emoji al estado
            if estado in ['Presente', 'Falta Recuperada']:
                estado_emoji = "✅"  # Verde: Asistencia
            elif estado == 'Falta Injustificada':
                estado_emoji = "❌"  # Rojo: Falta injustificada
            else:
                estado_emoji = "🟠"  # Naranja para otros estados

            # Info de recuperación del día
            rec_info = ""
            if resultado.get('rec_estado') == 'valido' and resultado.get('rec_minutos'):
                rec_min = resultado['rec_minutos']
                from utils import format_timedelta
                rec_e = format_timedelta(resultado.get('rec_entrada'))
                rec_s = format_timedelta(resultado.get('rec_salida'))
                rec_info = f"\n⏰ Recuperación: {rec_e} → {rec_s} | Total: {rec_min // 60} hs {rec_min % 60} min"
            elif resultado.get('rec_estado') == 'invalidado':
                rec_info = "\n⏰ Recuperación: ❌ Invalidada por advertencias acumuladas"

            # Añadir cada día al Embed
            embed.add_field(
                name=f"Fecha: **{fecha}** {estado_emoji}",
                value=f"**Entrada**: {entrada} | **Salida**: {salida} | **Estado**: {estado}{rec_info}",
                inline=False
            )
        
        # --- Resumen semanal ---
        query_resumen = """
        SELECT
          COALESCE(SUM(TIMESTAMPDIFF(MINUTE, a.hora_entrada, a.hora_salida)), 0) AS total_asist_min,
          COALESCE(SUM(TIMESTAMPDIFF(MINUTE, ar.hora_entrada, ar.hora_salida)), 0) AS total_rec_min
        FROM asistencia a
        LEFT JOIN asistencia_recuperacion ar
          ON ar.practicante_id = a.practicante_id
          AND ar.fecha_recuperacion = a.fecha
          AND ar.estado = 'valido'
        WHERE a.practicante_id = %s
          AND YEARWEEK(a.fecha, 1) = YEARWEEK(CURDATE(), 1)
        """
        resumen = await db.fetch_one(query_resumen, (practicante_id,))

        total_asist = resumen['total_asist_min'] if resumen else 0
        total_rec = resumen['total_rec_min'] if resumen else 0
        total_min = total_asist + total_rec
        requerido_min = HORAS_SEMANALES_REQUERIDAS * 60
        faltantes = max(0, requerido_min - total_min)

        resumen_text = (
            f"✅ Horas de asistencia: {total_asist // 60} hs {total_asist % 60} min\n"
            f"⏰ Horas de recuperación: {total_rec // 60} hs {total_rec % 60} min\n"
            f"📌 Total acumulado: {total_min // 60} hs {total_min % 60} min / {HORAS_SEMANALES_REQUERIDAS}hs"
        )
        if faltantes > 0:
            resumen_text += f"\n⚠️ Horas faltantes: {faltantes // 60} hs {faltantes % 60} min"

        embed.add_field(name="─────────────────────────", value="\u200b", inline=False)
        embed.add_field(name="📊 Resumen Semanal", value=resumen_text, inline=False)

        embed.set_footer(text="Si tienes dudas, contacta con el administrador.")

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Asistencia(bot))

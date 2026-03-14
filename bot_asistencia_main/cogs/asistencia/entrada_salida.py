import logging
from datetime import datetime, timedelta
import discord
from discord import app_commands, Embed, Color
import database as db
from utils import obtener_practicante, verificar_entrada, canal_permitido, tiene_clase_hoy_por_id
from bot.config.constants import (
    HORARIO_ENTRADA_INICIO,
    HORARIO_ENTRADA_FIN,
    HORA_LIMITE_TARDANZA,
    HORARIO_ENTRADA_TOLERANCIA,
    HORA_SALIDA_OFICIAL,
    HORA_GRACIA_SALIDA,
    HORARIO_SALIDA_MINIMA,
)


class EntradaSalidaCommands:
    """Comandos para registrar entrada y salida de asistencia."""

    @app_commands.command(name='entrada', description="Registrar tu entrada de asistencia")
    async def entrada(self, interaction: discord.Interaction):
        from utils import es_domingo, LIMA_TZ, format_timedelta

        await interaction.response.defer(ephemeral=True)

        if es_domingo():
            await interaction.followup.send("🚫 No se pueden registrar asistencias los domingos.", ephemeral=True)
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

        if hora_actual < HORARIO_ENTRADA_INICIO:
            await interaction.followup.send(
                f"⏳ El registro de asistencia aún no está habilitado. Disponible a partir de las {HORARIO_ENTRADA_INICIO.strftime('%H:%M')}hs.",
                ephemeral=True
            )
            return
        if hora_actual > HORARIO_ENTRADA_FIN:
            await interaction.followup.send("🚫 El horario de asistencia ya cerró. No puedes registrar entrada.", ephemeral=True)
            return

        existente = await verificar_entrada(interaction, discord_id, fecha_actual, usar_followup=True)
        if existente:
            hora_str = format_timedelta(existente['hora_entrada'])
            await interaction.followup.send(
                f"⚠️ Ya registraste tu entrada hoy a las {hora_str}.\nUsá `/asistencia salida` para registrar tu salida.",
                ephemeral=True
            )
            return

        if await tiene_clase_hoy_por_id(practicante_id):
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

        if estado in ('tarde', 'sobreHora'):
            query = """
            INSERT INTO asistencia (practicante_id, estado, fecha, hora_entrada)
            VALUES ($1, $2, $3, $4)
            """
            await db.execute_query(query, practicante_id, estado, fecha_actual, hora_actual)

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

    @app_commands.command(name='salida', description="Registrar tu salida de asistencia")
    async def salida(self, interaction: discord.Interaction):
        from utils import es_domingo, LIMA_TZ, format_timedelta

        await interaction.response.defer(ephemeral=True)

        if es_domingo():
            await interaction.followup.send("🚫 No se pueden registrar asistencias los domingos.", ephemeral=True)
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

        query_entrada = """
        SELECT id, hora_entrada, hora_salida, estado FROM asistencia
        WHERE practicante_id = $1 AND fecha = $2
        """
        registro = await db.fetch_one(query_entrada, practicante_id, fecha_actual)

        if not registro:
            await interaction.followup.send("⚠️ No tienes una entrada registrada hoy. Usá `/asistencia entrada` primero.", ephemeral=True)
            return
        if registro['hora_salida'] is not None:
            hora_sal = format_timedelta(registro['hora_salida'])
            await interaction.followup.send(f"⚠️ Ya registraste tu salida hoy a las {hora_sal}.", ephemeral=True)
            return

        mensaje_extra = ""
        if hora_actual > HORA_GRACIA_SALIDA:
            hora_salida_db = HORA_SALIDA_OFICIAL
            mensaje_extra = f"\n💡 Registraste tarde. Se marcó salida a las {HORA_SALIDA_OFICIAL.strftime('%H:%M')}."
        elif hora_actual < HORARIO_SALIDA_MINIMA:
            hora_salida_db = hora_actual
            mensaje_extra = "\n⚠️ Salida temprana registrada."
        else:
            hora_salida_db = hora_actual

        query_update = """
        UPDATE asistencia SET hora_salida = $1 WHERE id = $2
        """
        await db.execute_query(query_update, hora_salida_db, registro['id'])

        logging.info(f'Salida registrada para {interaction.user.display_name} a las {hora_salida_db}')

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


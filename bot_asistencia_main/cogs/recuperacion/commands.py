"""Comandos del módulo de recuperación — GroupCog con subcomandos entrada/salida"""

import discord
from discord import app_commands, Embed, Color
from discord.ext import commands
from utils import obtener_practicante, canal_permitido, verificar_rol_permitido
from datetime import datetime, time, timedelta
import database as db
import logging

from bot.config.constants import (
    HORA_INICIO_RECUPERACION,
    HORA_FIN_RECUPERACION,
    HORA_CIERRE_REAL,
)


class Recuperacion(commands.GroupCog, name="recuperacion"):
    """Cog para gestionar comandos de recuperación como subcomandos agrupados"""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    # ──────────────────────────────────────────────
    # /recuperacion entrada
    # ──────────────────────────────────────────────
    @app_commands.command(name='entrada', description="Registrar entrada de recuperación")
    async def entrada(self, interaction: discord.Interaction):
        from utils import es_domingo, LIMA_TZ
        await interaction.response.defer(ephemeral=True)

        # 1. Bloquear domingos
        if es_domingo():
            await interaction.followup.send(
                "🚫 No se pueden registrar horas de recuperación los domingos.",
                ephemeral=True
            )
            return

        if not await canal_permitido(interaction):
            return

        # 2. Verificar roles permitidos
        servidor_id = interaction.guild.id
        roles_permitidos = self.bot.roles_recuperacion.get(servidor_id, [])
        if roles_permitidos:
            if not await verificar_rol_permitido(interaction, roles_permitidos, usar_followup=True):
                return

        discord_id = interaction.user.id
        nombre_usuario = interaction.user.mention

        practicante_id = await obtener_practicante(interaction, discord_id, usar_followup=True)
        if not practicante_id:
            return

        ahora = datetime.now(LIMA_TZ)
        fecha_actual = ahora.date()
        hora_actual = ahora.time().replace(microsecond=0)

        # 3. Verificar horario permitido
        if hora_actual < HORA_INICIO_RECUPERACION:
            await interaction.followup.send(
                f"⏳ El registro de recuperación aún no está habilitado. "
                f"Disponible desde las {HORA_INICIO_RECUPERACION.strftime('%H:%M')}hs.",
                ephemeral=True
            )
            return

        if hora_actual > HORA_FIN_RECUPERACION:
            await interaction.followup.send(
                f"🚫 El registro de recuperación ya no está disponible. "
                f"El límite es hasta las {HORA_FIN_RECUPERACION.strftime('%H:%M')}hs.",
                ephemeral=True
            )
            return

        # 4. Verificar si ya tiene un registro abierto hoy
        query_abierto = """
        SELECT id, hora_entrada FROM recuperacion
        WHERE practicante_id = $1
          AND fecha = $2
          AND estado = 'abierto'
        """
        existente = await db.fetch_one(query_abierto, practicante_id, fecha_actual)

        if existente:
            from utils import format_timedelta
            hora_str = format_timedelta(existente['hora_entrada'])
            await interaction.followup.send(
                f"⚠️ Ya registraste una entrada de recuperación hoy a las {hora_str}.\n"
                f"Usá `/recuperacion salida` para cerrarla.",
                ephemeral=True
            )
            return

        # 5. Verificar si ya tiene un registro valido/invalidado hoy
        query_usado = """
        SELECT id FROM recuperacion
        WHERE practicante_id = $1
          AND fecha = $2
          AND estado IN ('valido', 'invalidado')
        """
        ya_usado = await db.fetch_one(query_usado, practicante_id, fecha_actual)
        if ya_usado:
            await interaction.followup.send(
                "⚠️ Ya registraste una recuperación el día de hoy. Solo se permite una por día.",
                ephemeral=True
            )
            return

        # 6. INSERT
        query_insert = """
        INSERT INTO recuperacion
          (practicante_id, fecha, hora_entrada, hora_salida, estado)
        VALUES ($1, $2, $3, NULL, 'abierto')
        """
        await db.execute_query(query_insert, practicante_id, fecha_actual, hora_actual)
        logging.info(f'Recuperación iniciada para {interaction.user.display_name}')

        # 7. Embed de confirmación
        embed = Embed(
            title="✅ Recuperación iniciada",
            color=Color.green()
        )
        embed.add_field(name="👤 Practicante", value=nombre_usuario, inline=False)
        embed.add_field(name="📅 Fecha", value=fecha_actual.strftime('%d-%m'), inline=True)
        embed.add_field(name="🟢 Hora de inicio", value=hora_actual.strftime('%H:%M'), inline=True)
        embed.set_footer(
            text=f"Recuerda registrar tu salida con /recuperacion salida antes de las {HORA_FIN_RECUPERACION.strftime('%H:%M')}hs."
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ──────────────────────────────────────────────
    # /recuperacion salida
    # ──────────────────────────────────────────────
    @app_commands.command(name='salida', description="Registrar salida de recuperación")
    async def salida(self, interaction: discord.Interaction):
        from utils import es_domingo, LIMA_TZ
        await interaction.response.defer(ephemeral=True)

        if es_domingo():
            await interaction.followup.send(
                "🚫 No se pueden registrar horas de recuperación los domingos.",
                ephemeral=True
            )
            return

        if not await canal_permitido(interaction):
            return

        practicante_id = await obtener_practicante(interaction, interaction.user.id, usar_followup=True)
        if not practicante_id:
            return

        ahora = datetime.now(LIMA_TZ)
        fecha_actual = ahora.date()
        hora_actual = ahora.time().replace(microsecond=0)
        nombre_usuario = interaction.user.mention

        # 1. Buscar registro abierto de hoy
        query_abierto = """
        SELECT id, hora_entrada FROM recuperacion
        WHERE practicante_id = $1
          AND fecha = $2
          AND estado = 'abierto'
        """
        rec = await db.fetch_one(query_abierto, practicante_id, fecha_actual)

        if not rec:
            await interaction.followup.send(
                "⚠️ No tenés una recuperación iniciada hoy. "
                "Usá `/recuperacion entrada` para comenzar.",
                ephemeral=True
            )
            return

        # 2. Determinar hora de salida según escenario
        mensaje_extra = ""

        if hora_actual <= HORA_FIN_RECUPERACION:
            # Caso 1: Salida en horario normal
            hora_salida_db = hora_actual
        else:
            # Caso 2/3: Salida después de las 20:00 → registrar hasta las 20:00
            hora_salida_db = HORA_FIN_RECUPERACION
            mensaje_extra = f"\n💡 Recordá marcar tu salida antes de las {HORA_FIN_RECUPERACION.strftime('%H:%M')}hs la próxima vez."

        # 3. Actualizar registro
        await db.execute_query(
            "UPDATE recuperacion SET hora_salida = $1, estado = 'valido' WHERE id = $2",
            hora_salida_db, rec['id']
        )

        # 4. Calcular duración
        hora_entrada = rec['hora_entrada']
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
        embed = Embed(
            title="✅ Recuperación finalizada",
            color=Color.blue()
        )
        embed.add_field(name="👤 Practicante", value=nombre_usuario, inline=False)
        embed.add_field(name="📅 Fecha", value=fecha_actual.strftime('%d-%m'), inline=True)
        embed.add_field(
            name="🟢 Inicio | 🔴 Fin",
            value=f"{hora_entrada_time.strftime('%H:%M')} | {hora_salida_db.strftime('%H:%M')}",
            inline=True
        )
        embed.add_field(name="⏱️ Tiempo recuperado hoy", value=f"{horas} hs {minutos} min", inline=False)

        if mensaje_extra:
            embed.set_footer(text=mensaje_extra.strip())

        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f'Recuperación finalizada para {interaction.user.display_name}: {horas}h {minutos}m')


async def setup(bot):
    await bot.add_cog(Recuperacion(bot))

import discord
from discord import app_commands
import aiohttp
import logging
import database as db
from .helpers import verificar_admin, resolver_discord_id, construir_embeds_historial


class HistorialCommands:
    """Comandos para consultar historial de asistencia."""

    @app_commands.command(name='asistencia_historial', description="Ver historial de asistencia de un practicante por ID o nombre")
    @app_commands.describe(usuario="ID de Discord, mención o nombre del practicante")
    async def asistencia_historial(self, interaction: discord.Interaction, usuario: str):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        discord_id = await resolver_discord_id(usuario)
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
                        embeds = construir_embeds_historial(data)
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

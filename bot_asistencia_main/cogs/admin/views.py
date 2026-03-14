import discord
from discord import Embed, Color
from datetime import datetime
from utils import format_timedelta, DIAS_CLASE, LIMA_TZ
import database as db


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


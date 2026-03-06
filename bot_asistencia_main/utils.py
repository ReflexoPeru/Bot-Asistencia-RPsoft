import database as db
import discord
from discord import TextStyle, ui
import datetime
from zoneinfo import ZoneInfo

# Zona horaria de Perú
LIMA_TZ = ZoneInfo("America/Lima")

# Mapeo de día de semana (0=lunes) a columna de clase
DIAS_CLASE = {
    0: 'clase_lunes',
    1: 'clase_martes',
    2: 'clase_miercoles',
    3: 'clase_jueves',
    4: 'clase_viernes',
    5: 'clase_sabado',
}

async def es_admin_bot(discord_id: int) -> bool:
    """Verifica si un usuario es administrador/developer del bot en la BD"""
    query = "SELECT 1 FROM bot_admin WHERE discord_id = $1"
    resultado = await db.fetch_one(query, discord_id)
    return resultado is not None

def format_timedelta(td):
    """Convierte un timedelta o time a string HH:MM:SS"""
    if td is None:
        return "N/A"
    if isinstance(td, datetime.time):
        return td.strftime("%H:%M:%S")
    if isinstance(td, datetime.timedelta):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return str(td)

def format_timedelta_total(td):
    """
    Formato para horas totales (puede exceder 24h).
    Soporta timedelta, time, e INTERVAL de PostgreSQL.
    """
    if td is None:
        return "00:00:00"
    if isinstance(td, datetime.timedelta):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    if isinstance(td, datetime.time):
        return td.strftime("%H:%M:%S")
    # Puede ser str de INTERVAL
    return str(td)

async def obtener_practicante(interaction, discord_id, usar_followup=False):
    """
    Obtiene el ID interno del practicante (solo activos).
    Retorna None si no está registrado o no está activo.
    """
    query = "SELECT id FROM practicante WHERE id_discord = $1 AND estado = 'activo'"
    resultado = await db.fetch_one(query, discord_id)

    if not resultado:
        msg = "❌ No estás registrado como practicante activo."
        if usar_followup:
            await interaction.followup.send(msg, ephemeral=True)
        else:
            try:
                await interaction.response.send_message(msg, ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send(msg, ephemeral=True)
        return None

    return resultado['id']

async def obtener_practicante_cualquier_estado(discord_id):
    """
    Obtiene datos del practicante sin importar el estado.
    Útil para verificar si existió alguna vez.
    """
    query = "SELECT id, estado, nombre_completo FROM practicante WHERE id_discord = $1"
    return await db.fetch_one(query, discord_id)

def tiene_clase_hoy(practicante_row: dict) -> bool:
    """
    Verifica si un practicante tiene clase hoy dado su registro completo.
    Requiere que el dict contenga los campos clase_lunes..clase_sabado.
    """
    hoy = datetime.datetime.now(LIMA_TZ).weekday()  # 0=lunes
    col = DIAS_CLASE.get(hoy)
    if col and col in practicante_row:
        return bool(practicante_row[col])
    return False

async def tiene_clase_hoy_por_id(practicante_id: int) -> bool:
    """Verifica si un practicante tiene clase hoy consultando la BD."""
    hoy = datetime.datetime.now(LIMA_TZ).weekday()
    col = DIAS_CLASE.get(hoy)
    if not col:
        return False
    query = f"SELECT {col} FROM practicante WHERE id = $1"
    resultado = await db.fetch_one(query, practicante_id)
    return bool(resultado[col]) if resultado else False

async def canal_permitido(interaction) -> bool:
    """Verifica si el canal actual está en la lista de canales permitidos."""
    bot = interaction.client
    guild_id = interaction.guild_id
    canales = bot.canales_permitidos.get(guild_id, [])
    if canales and interaction.channel_id not in canales:
        try:
            await interaction.followup.send(
                "❌ Este comando solo se puede usar en el canal de asistencia.",
                ephemeral=True
            )
        except:
            try:
                await interaction.response.send_message(
                    "❌ Este comando solo se puede usar en el canal de asistencia.",
                    ephemeral=True
                )
            except:
                pass
        return False
    return True

async def verificar_entrada(interaction, discord_id, fecha_actual, usar_followup=False):
    """Verifica si ya existe un registro de entrada para hoy."""
    query = """
    SELECT id, hora_entrada FROM asistencia
    WHERE practicante_id = (SELECT id FROM practicante WHERE id_discord = $1)
      AND fecha = $2
    """
    resultado = await db.fetch_one(query, discord_id, fecha_actual)
    return resultado

def es_domingo():
    """Retorna True si hoy es domingo en la zona horaria de Lima."""
    ahora = datetime.datetime.now(LIMA_TZ)
    return ahora.weekday() == 6  # 6 = domingo

async def verificar_rol_permitido(interaction, roles_permitidos, usar_followup=False):
    """Verifica si el usuario tiene al menos uno de los roles permitidos."""
    member = interaction.user
    roles_usuario = [r.id for r in member.roles]
    if not any(rol_id in roles_usuario for rol_id in roles_permitidos):
        msg = "❌ No tienes el rol necesario para usar este comando."
        if usar_followup:
            await interaction.followup.send(msg, ephemeral=True)
        else:
            try:
                await interaction.response.send_message(msg, ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send(msg, ephemeral=True)
        return False
    return True


class ModalJustificacion(ui.Modal, title="Justificación de tardanza"):
    """Modal para que el usuario ingrese el motivo de su tardanza."""
    motivo = ui.TextInput(
        label="Motivo de la tardanza",
        style=TextStyle.paragraph,
        placeholder="Explica brevemente el motivo de tu tardanza...",
        required=True,
        max_length=500,
    )

    def __init__(self, practicante_id: int, fecha, hora_entrada, estado: str, **kwargs):
        super().__init__(**kwargs)
        self.practicante_id = practicante_id
        self.fecha = fecha
        self.hora_entrada = hora_entrada
        self.estado = estado

    async def on_submit(self, interaction: discord.Interaction):
        # Registrar la asistencia con el motivo usando reporte
        query = """
        INSERT INTO asistencia (practicante_id, estado, fecha, hora_entrada)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (practicante_id, fecha) DO NOTHING
        """
        await db.execute_query(query, self.practicante_id, self.estado, self.fecha, self.hora_entrada)

        # Crear reporte de tardanza
        motivo_texto = self.motivo.value
        query_reporte = """
        INSERT INTO reporte (practicante_id, descripcion, tipo, fecha)
        VALUES ($1, $2, 'tardanza', $3)
        """
        await db.execute_query(query_reporte, self.practicante_id, f"Tardanza justificada: {motivo_texto}", self.fecha)

        await interaction.response.send_message(
            f"✅ Asistencia registrada como **{self.estado}** con justificación.",
            ephemeral=True
        )

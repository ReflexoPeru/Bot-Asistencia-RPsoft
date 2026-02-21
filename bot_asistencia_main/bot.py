import os
import json
import discord
from discord.ext import commands, tasks
import aiohttp
from dotenv import load_dotenv
# from database import init_db_pool, close_db_pool
import asyncio
import logging
import datetime
from zoneinfo import ZoneInfo
from aiohttp import web
import database as db
from utils import LIMA_TZ, format_timedelta, format_timedelta_total, es_domingo

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
BACKEND_API_KEY = os.getenv('BACKEND_API_KEY')
BACKEND_URL = os.getenv('BACKEND_URL')

# Eliminar handlers previos para evitar logs duplicados
root_logger = logging.getLogger()
if root_logger.handlers:
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S' 
)

# Configurar logging para usar hora de Lima
logging.Formatter.converter = lambda *args: datetime.datetime.now(LIMA_TZ).timetuple()

# Clase para métricas del bot
class BotMetrics:
    def __init__(self):
        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        self.events_processed_today = 0
        self.last_reset_day = self.start_time.day

    def increment_event_count(self):
        """Incrementa el contador de eventos y lo resetea si es un nuevo día."""
        now = datetime.datetime.now(datetime.timezone.utc)
        if now.day != self.last_reset_day:
            self.events_processed_today = 0
            self.last_reset_day = now.day
        self.events_processed_today += 1

    def get_uptime(self):
        """Calcula el tiempo de actividad del bot."""
        return datetime.datetime.now(datetime.timezone.utc) - self.start_time

metrics = BotMetrics()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)


# Diccionario de canales permitidos por servidor
bot.canales_permitidos = {
    # Servidor RP Soft (Producción)
    1389959112556679239: [
        1390353417079361607, # NO IMPLEMENTADO POR FAVOR CAMBIAR EL ID DE CANAL
    ],
    # Servidor Laboratorios (Pruebas)
    1405602519635202048: [
        1468308523539628208, # SERVIDOR LABORATORIOS CANAL │﹕📚・a-s-i-s-t-e-n-c-i-a
    ]
}

# Diccionario de roles permitidos para recuperación por servidor
# Agregar aquí los IDs de los roles que pueden usar el comando de recuperación
bot.roles_recuperacion = {
    1389959112556679239: [], # Servidor RP Soft - lista vacía significa que todos los practicantes pueden usar
    1405602519635202048: []  # Servidor Laboratorios - lista vacía significa que todos los practicantes pueden usar
    # Ejemplo con roles: 1389959112556679239: [123456789012345678, 987654321098765432]
}

# Función para actualizar el estado del bot en el backend
async def update_bot_status(status: str):
    """Envía una actualización de estado al backend."""
    if not BACKEND_URL or not BACKEND_API_KEY:
        return  # Skip if backend not configured
    
    headers = {"Authorization": f"Bearer {BACKEND_API_KEY}"}
    payload = {"status": status}
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.post(f"{BACKEND_URL}/status/", json=payload) as response:
                if response.status == 200:
                    logging.info(f"Estado del bot actualizado a '{status}' en el backend.")
                else:
                    logging.error(f"Error al actualizar el estado del bot: {response.status}")
        except aiohttp.ClientConnectorError as e:
            logging.error(f"No se pudo conectar al backend para actualizar estado: {e}")

# Eventos para Contar Métricas
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    metrics.increment_event_count()
    await bot.process_commands(message)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    metrics.increment_event_count()

# Tarea Periódica para Enviar Métricas
@tasks.loop(minutes=1)
async def send_metrics_to_backend():
    if not BACKEND_URL or not BACKEND_API_KEY:
        return  # Skip if backend not configured
    await bot.wait_until_ready()
    
    uptime_delta = metrics.get_uptime()
    now_lima = datetime.datetime.now()

    payload = {
        "resumen": {
            "servidores_conectados": len(bot.guilds),
            "eventos_procesados_hoy": metrics.events_processed_today,
            "uptime_porcentaje": 99.9,
            "ultima_sincronizacion": now_lima.isoformat()
        },
        "estado": {
            "status": "online",
            "uptime_dias": uptime_delta.days,
            "latencia_ms": round(bot.latency * 1000, 2),
            "ultima_conexion": now_lima.isoformat()
        },
        "servers": [
            {
                "server_id": guild.id,
                "server_name": guild.name,
                "miembros": guild.member_count,
                "canales": len(guild.channels),
                "status": "conectado"
            } for guild in bot.guilds
        ]
    }

    headers = {
        "Authorization": f"Bearer {BACKEND_API_KEY}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.post(f"{BACKEND_URL}/metrics/", json=payload) as response:
                if response.status == 200:
                    logging.info("Métricas enviadas exitosamente al backend.")
                else:
                    logging.error(f"Error al enviar métricas: {response.status} - {await response.text()}")
        except aiohttp.ClientConnectorError as e:
            logging.error(f"No se pudo conectar al backend para enviar métricas: {e}")
        except Exception as e:
            logging.error(f"Ocurrió un error inesperado al enviar métricas: {e}")

# Evento de inicio del bot
@bot.event
async def setup_hook():
    import database as db
    logging.info('Verificando y configurando base de datos...')
    await db.ensure_db_setup()
    
    logging.info('Cargando extensiones...')
    # Ajuste: Cargar explícitamente .commands ya que no usamos __init__.py en las subcarpetas
    await bot.load_extension('cogs.asistencia.commands')
    logging.info('...Asistencia cargada')
    
    # await bot.load_extension('cogs.faltas.commands') 
    
    await bot.load_extension('cogs.test.commands')
    logging.info('...Módulo Test cargado')
    
    await bot.load_extension('cogs.admin.commands')
    logging.info('...Admin cargada')
    
    logging.info('Sincronizando comandos...')
    
    # Sincronización global
    synced = await bot.tree.sync()
    logging.info(f'✅ {len(synced)} comandos sincronizados globalmente.')
    
    # Imprimir qué comandos se cargaron para debug
    cmds = [cmd.name for cmd in synced]
    logging.info(f"Comandos cargados: {', '.join(cmds)}")

    # Opcional: Forzar sincronización en el servidor específico para cambios instantáneos
    # Reemplaza con tu ID de servidor si quieres que sea ultra rápido el cambio
    # guild = discord.Object(id=1405602519635202048)
    # await bot.tree.sync(guild=guild)
    
    # Iniciar sincronización con Google Sheets (si está configurada)
    from google_sheets import sync_practicantes_to_db, export_report_to_sheet
    
    # Tarea de sincronización
    @tasks.loop(minutes=10)
    async def sync_google_sheets_task():
        await bot.wait_until_ready()
        logging.info("↻ Iniciando sincronización periódica con Google Sheets...")
        from google_sheets import sync_practicantes_to_db, export_report_to_sheet
        await sync_practicantes_to_db()
        await export_report_to_sheet()

    # Tarea de Reporte Diario Automático
    @tasks.loop(minutes=15)
    async def auto_reporte_diario_task():
        await bot.wait_until_ready()
        
        ahora = datetime.datetime.now(LIMA_TZ)
        # El reporte se intenta enviar a partir de las 2:30 PM (14:30)
        if ahora.hour < 14 or es_domingo():
            return

        fecha_hoy = ahora.date()
        
        # 1. Verificar si ya se envió hoy
        query_check = "SELECT 1 FROM reportes_enviados WHERE fecha = %s"
        ya_enviado = await db.fetch_one(query_check, (fecha_hoy,))
        if ya_enviado:
            return

        # 2. Verificar si hay salidas pendientes
        # Buscamos registros de hoy donde haya entrada pero NO salida
        query_pendientes = "SELECT COUNT(*) as count FROM asistencia WHERE fecha = %s AND hora_entrada IS NOT NULL AND hora_salida IS NULL"
        pendientes = await db.fetch_one(query_pendientes, (fecha_hoy,))
        
        if pendientes and pendientes['count'] > 0:
            logging.info(f"⏳ Reporte diario: {pendientes['count']} salidas pendientes. Postergando...")
            return

        # 3. Si no hay pendientes, generar y enviar reporte
        canal_reportes_id = 1468317880553574420
        canal = bot.get_channel(canal_reportes_id)
        
        if not canal:
            logging.error(f"❌ No se encontró el canal de reportes {canal_reportes_id}")
            return

        logging.info("📊 Todos han salido. Enviando reporte diario automático...")
        
        query_asistencia = """
        SELECT p.nombre_completo, a.hora_entrada, a.hora_salida, ea.estado
        FROM practicante p
        JOIN asistencia a ON p.id = a.practicante_id AND a.fecha = %s
        JOIN estado_asistencia ea ON a.estado_id = ea.id
        ORDER BY a.hora_entrada ASC
        """
        asistencias = await db.fetch_all(query_asistencia, (fecha_hoy,))

        if not asistencias:
            return

        embed = discord.Embed(
            title=f"📋 Reporte Diario de Asistencia - {fecha_hoy.strftime('%d/%m/%Y')}",
            description="Todos los practicantes del turno han registrado su salida.",
            color=discord.Color.gold(),
            timestamp=ahora
        )

        lista_resumen = ""
        for asis in asistencias:
            entrada = format_timedelta(asis['hora_entrada'])
            salida = format_timedelta(asis['hora_salida'])
            lista_resumen += f"• **{asis['nombre_completo']}**: {entrada} - {salida} ({asis['estado']})\n"

        embed.add_field(name="Resumen de hoy", value=lista_resumen or "Sin registros", inline=False)
        embed.set_footer(text="Cierre de jornada automático")

        await canal.send(content="🔔 <@615932763161362636>, el reporte diario ya está listo.", embed=embed)
        
        # 4. Marcar como enviado en la BD
        await db.execute_query("INSERT INTO reportes_enviados (fecha) VALUES (%s)", (fecha_hoy,))
        logging.info(f"✅ Reporte diario del {fecha_hoy} enviado correctamente.")

    # Iniciar las tareas
    sync_google_sheets_task.start()
    auto_reporte_diario_task.start()
    logging.info('Tareas programadas iniciadas.')

    # Nota: Los cogs ahora están organizados en carpetas (asistencia/, faltas/, recuperacion/)
    logging.info('Iniciando tarea de envío de métricas...')
    send_metrics_to_backend.start()
    logging.info(f'Bot logueado como {bot.user} (Configurando conexión...)')

@bot.event
async def on_ready():
    # Configurar presencia del bot cuando ya está totalmente conectado
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="la asistencia | RP Soft"))
    logging.info(f'✅ Bot conectado y listo como {bot.user}')

# Servidor web para Health Check
# Servidor web para Health Check y Dashboard
async def health_check_handler(request):
    return web.Response(text="Bot is running!", status=200)

async def dashboard_handler(request):
    try:
        from aiohttp import web
        import datetime
        from utils import LIMA_TZ
        import database as db

        # 1. Obtener fecha desde query param o usar la actual
        fecha_param = request.query.get('fecha', None)
        if fecha_param:
            try:
                fecha_actual = datetime.datetime.strptime(fecha_param, '%Y-%m-%d').date()
            except ValueError:
                fecha_actual = datetime.datetime.now(LIMA_TZ).date()
        else:
            fecha_actual = datetime.datetime.now(LIMA_TZ).date()
        
        query = """
        SELECT p.nombre_completo, a.hora_entrada, a.hora_salida, ea.estado
        FROM practicante p
        JOIN asistencia a ON p.id = a.practicante_id AND a.fecha = %s
        JOIN estado_asistencia ea ON a.estado_id = ea.id
        ORDER BY a.hora_entrada ASC
        """
        
        resultados = await db.fetch_all(query, (fecha_actual,))
        
        # 2. Construir filas HTML
        rows_html = ""
        empty_state = ""
        
        if resultados:
            for row in resultados:
                nombre = row['nombre_completo']
                entrada = str(row['hora_entrada']) if row['hora_entrada'] else "--:--"
                salida_raw = row['hora_salida']
                salida = str(salida_raw) if salida_raw else ""
                estado_bd = row['estado']
                
                badge_class = "badge-presente"
                if "Tardanza" in estado_bd: badge_class = "badge-tardanza"
                elif "Falta" in estado_bd: badge_class = "badge-falta"
                
                estado_badge = f'<span class="badge {badge_class}">{estado_bd}</span>'
                
                if salida_raw:
                    situacion = '<span class="state-offline">Finalizado</span>'
                else:
                    situacion = '<span class="state-online">● En Línea</span>'
                    if not salida:
                        salida = "---"

                rows_html += f"""
                <tr>
                    <td>{nombre}</td>
                    <td>{estado_badge}</td>
                    <td>{entrada}</td>
                    <td>{salida}</td>
                    <td>{situacion}</td>
                </tr>
                """
        else:
             empty_state = '<div class="empty-state"><h3>No hay registros para esta fecha</h3><p>Selecciona otro día en el calendario.</p></div>'

        # 3. Leer template
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(current_dir, 'templates', 'index.html')
            
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except FileNotFoundError:
            return web.Response(text=f"<h1>Error: Template not found at {template_path}</h1>", status=500, content_type='text/html')

        # 4. Reemplazar placeholders
        final_html = html_content.replace('<!-- DATA_ROWS__BE_REPLACED_BY_PYTHON -->', rows_html)
        final_html = final_html.replace('<!-- EMPTY_STATE_PLACEHOLDER -->', empty_state)
        final_html = final_html.replace('<!-- SELECTED_DATE_PLACEHOLDER -->', fecha_actual.strftime('%Y-%m-%d'))
        
        return web.Response(text=final_html, content_type='text/html')

    except Exception as e:
        logging.error(f"Error en dashboard: {e}")
        return web.Response(text=f"Error interno: {str(e)}", status=500)

async def api_asistencia_handler(request):
    """Retorna registros de asistencia para una fecha dada como JSON."""
    try:
        import datetime
        from utils import LIMA_TZ
        import database as db

        fecha_param = request.query.get('fecha', None)
        if fecha_param:
            try:
                fecha = datetime.datetime.strptime(fecha_param, '%Y-%m-%d').date()
            except ValueError:
                return web.json_response({"error": "Formato de fecha inválido. Usa YYYY-MM-DD"}, status=400)
        else:
            fecha = datetime.datetime.now(LIMA_TZ).date()

        query = """
        SELECT p.nombre_completo, a.hora_entrada, a.hora_salida, ea.estado
        FROM practicante p
        JOIN asistencia a ON p.id = a.practicante_id AND a.fecha = %s
        JOIN estado_asistencia ea ON a.estado_id = ea.id
        ORDER BY a.hora_entrada ASC
        """
        resultados = await db.fetch_all(query, (fecha,))

        data = []
        for row in resultados:
            data.append({
                "nombre": row['nombre_completo'],
                "entrada": str(row['hora_entrada']) if row['hora_entrada'] else None,
                "salida": str(row['hora_salida']) if row['hora_salida'] else None,
                "estado": row['estado']
            })

        return web.json_response({"fecha": str(fecha), "registros": data})

    except Exception as e:
        logging.error(f"Error en API asistencia: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_fechas_handler(request):
    """Retorna las fechas de un mes que tienen registros de asistencia."""
    try:
        import datetime
        from utils import LIMA_TZ
        import database as db

        mes_param = request.query.get('mes', None)
        if mes_param:
            try:
                # Esperamos formato YYYY-MM
                year, month = mes_param.split('-')
                year, month = int(year), int(month)
            except (ValueError, AttributeError):
                return web.json_response({"error": "Formato inválido. Usa YYYY-MM"}, status=400)
        else:
            now = datetime.datetime.now(LIMA_TZ)
            year, month = now.year, now.month

        query = """
        SELECT DISTINCT fecha FROM asistencia
        WHERE YEAR(fecha) = %s AND MONTH(fecha) = %s
        ORDER BY fecha
        """
        resultados = await db.fetch_all(query, (year, month))

        fechas = [str(row['fecha']) for row in resultados]

        return web.json_response({"mes": f"{year}-{month:02d}", "fechas": fechas})

    except Exception as e:
        logging.error(f"Error en API fechas: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def start_health_check():
    app = web.Application()
    app.router.add_get("/health", health_check_handler)
    app.router.add_get("/", dashboard_handler)
    app.router.add_get("/api/asistencia", api_asistencia_handler)
    app.router.add_get("/api/fechas", api_fechas_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    # Usar el puerto que asigne el hosting o el 10000 por defecto
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Servidor Web iniciado en el puerto {port}")

# Manejo de errores globales
async def main():
    if not TOKEN:
        logging.error("Falta DISCORD_TOKEN. El bot no puede iniciar sin el token de Discord.")
        return
    
    if not all([BACKEND_API_KEY, BACKEND_URL]):
        logging.warning("BACKEND_API_KEY o BACKEND_URL no configurados. El bot funcionará sin enviar métricas al backend.")

    # Iniciar servidor Health Check
    await start_health_check()

    try:
        await bot.start(TOKEN)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logging.info("Bot detenido manualmente.")
    finally:
        logging.info("Bot apagándose...")
        if send_metrics_to_backend.is_running():
            send_metrics_to_backend.cancel()
        await update_bot_status("offline")
        await asyncio.sleep(1)
        # await close_db_pool()
        # logging.info("Conexión a la base de datos cerrada.")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())

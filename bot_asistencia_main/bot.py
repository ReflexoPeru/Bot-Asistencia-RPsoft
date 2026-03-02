import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import logging
import datetime
from zoneinfo import ZoneInfo
import database as db
from utils import LIMA_TZ

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

# Configurar bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Guardar config del backend en el bot para acceso desde cogs
bot._backend_api_key = BACKEND_API_KEY
bot._backend_url = BACKEND_URL

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
bot.roles_recuperacion = {
    1389959112556679239: [], # Servidor RP Soft
    1405602519635202048: []  # Servidor Laboratorios
}

# Evento de inicio del bot
@bot.event
async def setup_hook():
    logging.info('Verificando y configurando base de datos...')
    await db.ensure_db_setup()
    
    logging.info('Cargando extensiones...')
    
    await bot.load_extension('cogs.asistencia.commands')
    logging.info('...Asistencia cargada')
    
    await bot.load_extension('cogs.recuperacion.commands')
    logging.info('...Recuperación cargada')
    
    await bot.load_extension('cogs.test.commands')
    logging.info('...Módulo Test cargado')
    
    await bot.load_extension('cogs.admin.commands')
    logging.info('...Admin cargada')
    
    await bot.load_extension('cogs.tasks.scheduled_tasks')
    logging.info('...Tareas programadas cargadas')
    
    logging.info('Sincronizando comandos...')
    
    # Sincronización global
    synced = await bot.tree.sync()
    logging.info(f'✅ {len(synced)} comandos sincronizados globalmente.')
    
    cmds = [cmd.name for cmd in synced]
    logging.info(f"Comandos cargados: {', '.join(cmds)}")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="la asistencia | RP Soft"))
    logging.info(f'✅ Bot conectado y listo como {bot.user}')

# Punto de entrada
async def main():
    if not TOKEN:
        logging.error("Falta DISCORD_TOKEN. El bot no puede iniciar sin el token de Discord.")
        return
    
    if not all([BACKEND_API_KEY, BACKEND_URL]):
        logging.warning("BACKEND_API_KEY o BACKEND_URL no configurados. El bot funcionará sin enviar métricas al backend.")

    # Iniciar servidor web
    from web.server import start_web_server
    await start_web_server()

    try:
        await bot.start(TOKEN)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logging.info("Bot detenido manualmente.")
    finally:
        logging.info("Bot apagándose...")
        from cogs.tasks.scheduled_tasks import update_bot_status
        await update_bot_status(bot, "offline")
        await asyncio.sleep(1)
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())

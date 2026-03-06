"""Script temporal para crear las tablas en PostgreSQL."""
import asyncio
import sys
sys.path.insert(0, '/home/jhefry-lap/IdeaProjects/Bot-Asistencia-RPsoft/bot_asistencia_main')

import database as db

async def main():
    await db.ensure_db_setup()
    await db.close_db_pool()
    print("✅ Tablas creadas exitosamente")

asyncio.run(main())

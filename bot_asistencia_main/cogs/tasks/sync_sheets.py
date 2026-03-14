"""Sincronización periódica con Google Sheets."""

import logging
from discord.ext import tasks


class SyncSheetsTasks:
    """Tarea recurrente para sincronizar datos con Google Sheets."""

    @tasks.loop(minutes=10)
    async def sync_google_sheets_task(self):
        logging.info("↻ Iniciando sincronización periódica con Google Sheets...")
        from google_sheets import sync_practicantes_to_db, export_report_to_sheet
        await sync_practicantes_to_db()
        await export_report_to_sheet()

    @sync_google_sheets_task.before_loop
    async def before_sync_sheets(self):
        await self.bot.wait_until_ready()

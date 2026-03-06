import gspread
from google.oauth2.service_account import Credentials
import logging
import os

# Configuración
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
CREDENTIALS_FILE = '/app/credentials.json'
SHEET_NAME_ENV = 'GOOGLE_SHEET_NAME'

def format_duration(td_str):
    """
    Convierte un string de duración o un timedelta al formato [HH]:MM:SS.
    """
    if not td_str or td_str == 'None' or str(td_str) == '0:00:00':
        return '00:00:00'

    td_str = str(td_str)

    try:
        if 'day' in td_str:
            parts = td_str.split(',')
            days_part = parts[0].strip()
            time_part = parts[1].strip()
            days = int(days_part.split(' ')[0])
            h, m, s = map(int, time_part.split(':'))
            total_hours = (days * 24) + h
            return f"{total_hours:02d}:{m:02d}:{s:02d}"
        else:
            return td_str
    except Exception as e:
        logging.warning(f"⚠️ Error formateando duración '{td_str}': {e}")
        return td_str

def get_spanish_date(date_obj):
    """Retorna la fecha formateada en español."""
    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
              "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    day_name = days[date_obj.weekday()]
    month_name = months[date_obj.month - 1]
    return f"{day_name} {date_obj.day} {month_name} {date_obj.year}"

def get_practicantes_from_sheet():
    """
    Lee la lista de practicantes desde Google Sheets.
    Retorna una lista de diccionarios con 'id_discord', 'nombre_completo', 'horas_base'.
    """
    sheet_name = os.getenv(SHEET_NAME_ENV, 'Bot_de_asistencia_2026')

    if not os.path.exists(CREDENTIALS_FILE) and not os.path.exists('credentials.json'):
        if os.path.exists('credentials.json'):
            creds_path = 'credentials.json'
        else:
            logging.warning(f"⚠️ No se encontró {CREDENTIALS_FILE}.")
            return []
    else:
        creds_path = CREDENTIALS_FILE if os.path.exists(CREDENTIALS_FILE) else 'credentials.json'

    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        client = gspread.authorize(creds)

        try:
            sheet = client.open(sheet_name).sheet1
        except gspread.SpreadsheetNotFound:
            logging.error(f"❌ No se encontró la hoja: '{sheet_name}'.")
            return []

        rows = sheet.get_all_values()
        if len(rows) < 2:
            return []

        practicantes = []
        headers = [h.lower() for h in rows[0]]

        try:
            idx_id = next(i for i, h in enumerate(headers) if 'id' in h and 'discord' in h)
            idx_nombre = next(i for i, h in enumerate(headers) if 'nombre' in h)
            try:
                idx_horas_base = next(i for i, h in enumerate(headers) if 'base' in h or 'acumuladas' in h)
            except StopIteration:
                idx_horas_base = None
        except StopIteration:
            logging.error("❌ Columnas 'ID Discord' o 'Nombre' no encontradas.")
            return []

        for row in rows[1:]:
            if len(row) <= max(idx_id, idx_nombre):
                continue

            raw_id = row[idx_id].strip()
            idx_apellido = next((i for i, h in enumerate(headers) if 'apellido' in h), None)
            nombre_part = row[idx_nombre].strip()
            apellido_part = row[idx_apellido].strip() if idx_apellido is not None and len(row) > idx_apellido else ""

            if not apellido_part or apellido_part == nombre_part:
                full_name_raw = nombre_part
            else:
                full_name_raw = f"{nombre_part} {apellido_part}".strip()

            nombre_completo = " ".join([word.capitalize() for word in full_name_raw.split()])

            horas_base = row[idx_horas_base].strip() if idx_horas_base is not None and len(row) > idx_horas_base else "00:00:00"

            if horas_base and horas_base.isdigit():
                horas_base = f"{horas_base}:00:00"
            elif not horas_base or ':' not in horas_base:
                horas_base = "00:00:00"

            if not raw_id or not nombre_completo:
                continue

            try:
                raw_id_clean = "".join(filter(str.isdigit, raw_id))
                if not raw_id_clean:
                    if '.' in raw_id:
                        discord_id = int(float(raw_id))
                    else:
                        continue
                else:
                    discord_id = int(raw_id_clean)

                practicantes.append({
                    'id_discord': discord_id,
                    'nombre_completo': nombre_completo,
                    'horas_base': horas_base
                })
            except ValueError:
                logging.warning(f"⚠️ ID inválido: {raw_id} ({nombre_completo})")
                continue

        logging.info(f"✅ {len(practicantes)} practicantes leídos de Google Sheets.")
        return practicantes

    except Exception as e:
        logging.error(f"❌ Error en Google Sheets: {e}")
        return []


async def sync_practicantes_to_db():
    """Sincroniza practicantes desde Sheets a PostgreSQL (no sobrescribe retirados)."""
    import database as db
    import datetime

    practicantes = get_practicantes_from_sheet()
    if not practicantes:
        return

    for p in practicantes:
        # Convertir HH:MM:SS string a timedelta para asyncpg INTERVAL
        horas_str = p['horas_base']
        try:
            parts = horas_str.split(':')
            h = int(parts[0]) if len(parts) > 0 else 0
            m = int(parts[1]) if len(parts) > 1 else 0
            s = int(parts[2]) if len(parts) > 2 else 0
            horas_td = datetime.timedelta(hours=h, minutes=m, seconds=s)
        except (ValueError, IndexError):
            horas_td = datetime.timedelta(0)

        # ON CONFLICT: actualizar nombre y horas_base, pero NO tocar retirados
        query = """
        INSERT INTO practicante (id_discord, nombre_completo, horas_base)
        VALUES ($1, $2, $3)
        ON CONFLICT (id_discord) DO UPDATE SET
            nombre_completo = EXCLUDED.nombre_completo,
            horas_base = EXCLUDED.horas_base
        WHERE practicante.estado = 'activo'
        """
        await db.execute_query(query, p['id_discord'], p['nombre_completo'], horas_td)

    logging.info("📥 Sincronización con Google Sheets completa.")


async def export_report_to_sheet():
    """Exporta el reporte de asistencia y resumen general a Google Sheets."""
    import database as db

    # Query directo (ya no dependemos de la vista reporte_asistencia)
    query_detallado = """
    SELECT
        a.fecha AS "Fecha",
        p.nombre_completo AS "Nombre_Completo",
        a.hora_entrada AS "Entrada",
        a.hora_salida AS "Salida",
        CASE
            WHEN a.hora_salida IS NOT NULL AND a.hora_entrada IS NOT NULL THEN
                a.hora_salida - a.hora_entrada
            ELSE INTERVAL '0 seconds'
        END AS "Horas_Sesion",
        a.estado AS "Estado"
    FROM asistencia a
    JOIN practicante p ON a.practicante_id = p.id
    ORDER BY a.fecha DESC, p.nombre_completo ASC
    """
    data = await db.fetch_all(query_detallado)

    if not data:
        logging.info("↻ Reporte Sheets: No hay datos.")
        return

    sheet_name = os.getenv(SHEET_NAME_ENV, 'Bot_de_asistencia_2026')

    if not os.path.exists(CREDENTIALS_FILE) and not os.path.exists('credentials.json'):
        logging.warning("⚠️ Sin credenciales de Google Sheets.")
        return

    creds_path = CREDENTIALS_FILE if os.path.exists(CREDENTIALS_FILE) else 'credentials.json'

    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open(sheet_name)

        # ------ Reporte Detallado ------
        try:
            worksheet_det = spreadsheet.worksheet("Reporte Detallado")
        except gspread.WorksheetNotFound:
            worksheet_det = spreadsheet.add_worksheet(title="Reporte Detallado", rows="1000", cols="10")

        headers_det = ["Fecha", "Nombre Completo", "Entrada", "Salida", "Horas Sesión", "Estado"]
        rows_det = [headers_det]

        last_date = None
        header_positions = []

        for row in data:
            current_date = row['Fecha']
            if current_date != last_date:
                date_str = get_spanish_date(current_date)
                rows_det.append([date_str, "", "", "", "", ""])
                header_positions.append(len(rows_det))
                last_date = current_date

            rows_det.append([
                str(row['Fecha']),
                row.get('Nombre_Completo', 'N/A'),
                str(row['Entrada']) if row['Entrada'] else '-',
                str(row['Salida']) if row['Salida'] else '-',
                format_duration(str(row['Horas_Sesion'])),
                row['Estado']
            ])

        worksheet_det.clear()
        worksheet_det.format("A1:Z1000", {
            "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
            "textFormat": {"bold": False, "foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0}, "fontSize": 10}
        })
        worksheet_det.update('A1', rows_det)

        if header_positions:
            for pos in header_positions:
                range_str = f"A{pos}:F{pos}"
                worksheet_det.format(range_str, {
                    "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 1.0},
                    "textFormat": {"bold": True, "fontSize": 11}
                })

        worksheet_det.format("A1:F1", {
            "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
            "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True}
        })

        # ------ Resumen General ------
        try:
            worksheet_res = spreadsheet.worksheet("Resumen General")
        except gspread.WorksheetNotFound:
            worksheet_res = spreadsheet.add_worksheet(title="Resumen General", rows="100", cols="6")

        query_resumen = """
        SELECT
            p.nombre_completo,
            COALESCE(p.horas_base, INTERVAL '0 seconds') AS "Horas_Base",
            COALESCE(SUM(
                CASE WHEN a.hora_salida IS NOT NULL AND a.hora_entrada IS NOT NULL
                     THEN a.hora_salida - a.hora_entrada
                     ELSE INTERVAL '0 seconds'
                END
            ), INTERVAL '0 seconds') AS "Horas_Trabajadas_Bot",
            COALESCE(p.horas_base, INTERVAL '0 seconds') + COALESCE(SUM(
                CASE WHEN a.hora_salida IS NOT NULL AND a.hora_entrada IS NOT NULL
                     THEN a.hora_salida - a.hora_entrada
                     ELSE INTERVAL '0 seconds'
                END
            ), INTERVAL '0 seconds') AS "Total_Acumulado"
        FROM practicante p
        LEFT JOIN asistencia a ON p.id = a.practicante_id AND a.hora_salida IS NOT NULL
        WHERE p.estado = 'activo'
        GROUP BY p.id, p.nombre_completo, p.horas_base
        ORDER BY "Total_Acumulado" DESC
        """
        data_resumen = await db.fetch_all(query_resumen)

        headers_res = ["Nombre Completo", "Horas Base", "Horas Bot", "TOTAL ACUMULADO", "Meta (480h)"]
        rows_res = [headers_res]

        for row in data_resumen:
            rows_res.append([
                row['nombre_completo'],
                format_duration(str(row['Horas_Base'])),
                format_duration(str(row['Horas_Trabajadas_Bot'])),
                format_duration(str(row['Total_Acumulado'])),
                '480:00:00'
            ])

        worksheet_res.clear()
        worksheet_res.update('A1', rows_res)

        logging.info(f"📊 Reportes actualizados en Sheets: Detallado ({len(data)}) y Resumen ({len(data_resumen)}).")

    except Exception as e:
        logging.error(f"❌ Error exportando a Google Sheets: {e}")

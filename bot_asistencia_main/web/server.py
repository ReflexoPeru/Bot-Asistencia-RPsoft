"""Servidor web para Health Check, Dashboard y APIs"""

import os
import logging
import datetime
from aiohttp import web
import database as db
from utils import LIMA_TZ


async def health_check_handler(request):
    return web.Response(text="Bot is running!", status=200)


async def dashboard_handler(request):
    try:
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
            # El template está en ../templates/ relativo a web/
            template_path = os.path.join(current_dir, '..', 'templates', 'index.html')

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
        mes_param = request.query.get('mes', None)
        if mes_param:
            try:
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


async def start_web_server():
    """Inicia el servidor web con health check, dashboard y APIs."""
    app = web.Application()
    app.router.add_get("/health", health_check_handler)
    app.router.add_get("/", dashboard_handler)
    app.router.add_get("/api/asistencia", api_asistencia_handler)
    app.router.add_get("/api/fechas", api_fechas_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Servidor Web iniciado en el puerto {port}")

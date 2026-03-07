"""
Script de migración: MariaDB → PostgreSQL
Lee respaldo_migracion.sql y genera sentencias INSERT para PostgreSQL.
Ejecutar con: python migrate_data.py | docker exec -i postgres_db psql -U bot_user -d asistencia_rp_soft
O ejecutarlo directamente: python migrate_data.py
"""
import re
import sys


def parse_mysql_insert(line: str):
    """Extrae la tabla y los valores de un INSERT INTO MySQL."""
    # Intentar primero con nombres de columnas: INSERT INTO `tabla` (`col1`, `col2`) VALUES (...)
    match_with_cols = re.match(r"INSERT INTO `(\w+)` \(([^)]+)\) VALUES (.+);$", line)
    
    if match_with_cols:
        table = match_with_cols.group(1)
        columns = [c.strip().strip('`') for c in match_with_cols.group(2).split(',')]
        values_str = match_with_cols.group(3)
    else:
        # Intentar sin nombres de columnas (dump de producción): INSERT INTO `tabla` VALUES (...)
        match_no_cols = re.match(r"INSERT INTO `(\w+)` VALUES (.+);$", line)
        if not match_no_cols:
            return None, None, None
            
        table = match_no_cols.group(1)
        values_str = match_no_cols.group(2)
        
        # Hardcodear las columnas esperadas según la DB en producción para cada tabla
        if table == "practicante":
            columns = ["id", "id_discord", "nombre_completo", "horas_base", "advertencias"]
        elif table == "asistencia":
            columns = ["id", "practicante_id", "estado_id", "fecha", "hora_entrada", "hora_salida", "horas_extra", "observaciones", "motivo"]
        elif table == "bot_admins":
            columns = ["discord_id", "nombre_referencia", "rol", "estado"]
        elif table == "asistencia_recuperacion":
            columns = ["id", "practicante_id", "fecha_recuperacion", "hora_entrada", "hora_salida", "estado"]
        elif table == "reportes_enviados":
            columns = ["fecha", "enviado_at"]
        else:
            return None, None, None

    # Parsear los VALUES (...),(...),...
    rows = []
    current = ""
    depth = 0
    for ch in values_str:
        if ch == '(':
            depth += 1
            if depth == 1:
                current = ""
                continue
        elif ch == ')':
            depth -= 1
            if depth == 0:
                rows.append(current)
                current = ""
                continue
        if depth >= 1:
            current += ch
    
    parsed_rows = []
    for row_str in rows:
        vals = []
        in_quote = False
        escape_next = False
        val = ""
        for ch in row_str:
            if escape_next:
                val += ch
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                val += ch
                continue
            if ch == "'" and not in_quote:
                in_quote = True
                val += ch
                continue
            if ch == "'" and in_quote:
                in_quote = False
                val += ch
                continue
            if ch == ',' and not in_quote:
                vals.append(val.strip())
                val = ""
                continue
            val += ch
        vals.append(val.strip())
        parsed_rows.append(vals)
    
    return table, columns, parsed_rows


def map_estado_asistencia(estado_id: int, hora_entrada: str) -> str:
    """Mapea estado_id de MariaDB al nuevo enum de PostgreSQL."""
    if estado_id == 1:
        return 'temprano'
    elif estado_id == 2:
        # Diferenciar tarde vs sobreHora basado en hora_entrada
        if hora_entrada and hora_entrada != 'NULL':
            parts = hora_entrada.strip("'").split(':')
            hora = int(parts[0])
            minuto = int(parts[1])
            if hora > 9 or (hora == 9 and minuto > 0):
                return 'sobreHora'
        return 'tarde'
    elif estado_id == 3:
        return 'falto'
    elif estado_id == 4:
        return 'falto'  # Falta recuperada → la info está en tabla recuperacion
    elif estado_id == 5:
        return 'clases'  # Permiso → se mapea a 'clases'
    return 'temprano'


def generate_practicante_inserts(columns, rows):
    """Genera INSERTs PostgreSQL para practicante."""
    output = []
    col_map = {c: i for i, c in enumerate(columns)}
    
    for vals in rows:
        pid = vals[col_map['id']]
        discord_id = vals[col_map['id_discord']]
        nombre = vals[col_map['nombre_completo']].strip("'").replace("''", "'")
        horas_base = vals[col_map['horas_base']].strip("'")
        
        # Convertir HH:MM:SS de MariaDB a INTERVAL de PostgreSQL
        parts = horas_base.split(':')
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        interval = f"{h} hours {m} minutes {s} seconds"
        
        nombre_escaped = nombre.replace("'", "''")
        output.append(
            f"INSERT INTO practicante (id, id_discord, nombre_completo, horas_base, estado) "
            f"VALUES ({pid}, {discord_id}, '{nombre_escaped}', '{interval}', 'activo') "
            f"ON CONFLICT (id) DO NOTHING;"
        )
    
    return output


def generate_asistencia_inserts(columns, rows):
    """Genera INSERTs PostgreSQL para asistencia con mapeo de estados."""
    output = []
    col_map = {c: i for i, c in enumerate(columns)}
    
    for vals in rows:
        aid = vals[col_map['id']]
        prac_id = vals[col_map['practicante_id']]
        estado_id = int(vals[col_map['estado_id']])
        fecha = vals[col_map['fecha']].strip("'")
        hora_entrada = vals[col_map['hora_entrada']]
        hora_salida = vals[col_map['hora_salida']]
        
        estado = map_estado_asistencia(estado_id, hora_entrada)
        
        he = hora_entrada.strip("'") if hora_entrada != 'NULL' else None
        hs = hora_salida.strip("'") if hora_salida != 'NULL' else None
        
        he_sql = f"'{he}'" if he else "NULL"
        hs_sql = f"'{hs}'" if hs else "NULL"
        
        output.append(
            f"INSERT INTO asistencia (id, practicante_id, estado, fecha, hora_entrada, hora_salida) "
            f"VALUES ({aid}, {prac_id}, '{estado}', '{fecha}', {he_sql}, {hs_sql}) "
            f"ON CONFLICT (practicante_id, fecha) DO NOTHING;"
        )
    
    return output


def generate_bot_admin_inserts(columns, rows):
    """Genera INSERTs PostgreSQL para bot_admin."""
    output = []
    col_map = {c: i for i, c in enumerate(columns)}
    
    for vals in rows:
        discord_id = vals[col_map['discord_id']]
        nombre = vals[col_map['nombre_referencia']].strip("'").replace("''", "'")
        rol = vals[col_map['rol']].strip("'")
        
        nombre_escaped = nombre.replace("'", "''")
        output.append(
            f"INSERT INTO bot_admin (discord_id, nombre_discord, rol) "
            f"VALUES ({discord_id}, '{nombre_escaped}', '{rol}') "
            f"ON CONFLICT (discord_id) DO NOTHING;"
        )
    
    return output


def generate_recuperacion_inserts(columns, rows):
    """Genera INSERTs PostgreSQL para recuperacion."""
    output = []
    col_map = {c: i for i, c in enumerate(columns)}
    
    for vals in rows:
        rid = vals[col_map['id']]
        prac_id = vals[col_map['practicante_id']]
        fecha = vals[col_map['fecha_recuperacion']].strip("'")
        he = vals[col_map['hora_entrada']].strip("'")
        hs = vals[col_map['hora_salida']].strip("'") if vals[col_map['hora_salida']] != 'NULL' else None
        estado = vals[col_map['estado']].strip("'")
        
        hs_sql = f"'{hs}'" if hs else "NULL"
        
        output.append(
            f"INSERT INTO recuperacion (id, practicante_id, fecha, hora_entrada, hora_salida, estado) "
            f"VALUES ({rid}, {prac_id}, '{fecha}', '{he}', {hs_sql}, '{estado}') "
            f"ON CONFLICT (practicante_id, fecha) DO NOTHING;"
        )
    
    return output


def generate_reportes_enviados_inserts(columns, rows):
    """Genera INSERTs PostgreSQL para reportes_enviados."""
    output = []
    col_map = {c: i for i, c in enumerate(columns)}
    
    for vals in rows:
        fecha = vals[col_map['fecha']].strip("'")
        enviado = vals[col_map['enviado_at']].strip("'")
        
        output.append(
            f"INSERT INTO reportes_enviados (fecha, enviado_at) "
            f"VALUES ('{fecha}', '{enviado}') "
            f"ON CONFLICT (fecha) DO NOTHING;"
        )
    
    return output


def main():
    with open('respaldo_migracion.sql', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Unir líneas rotas (MySQL dump puede partir en varias líneas)
    lines = content.split('\n')
    all_inserts = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('INSERT INTO'):
            all_inserts.append(line)
    
    output_lines = [
        "-- ============================================",
        "-- Datos migrados de MariaDB → PostgreSQL",
        "-- Generado automáticamente por migrate_data.py",
        "-- ============================================",
        "",
        "BEGIN;",
        "",
    ]
    
    # Parsear todos los INSERTs y agrupar por tabla
    tables_data = {}
    for insert_line in all_inserts:
        table, columns, rows = parse_mysql_insert(insert_line)
        if table:
            tables_data[table] = (columns, rows)
    
    # Orden de procesamiento respetando FK: padres primero, hijos después
    TABLE_ORDER = [
        'practicante',              # Sin dependencias
        'bot_admins',               # Sin dependencias
        'asistencia',               # FK → practicante
        'asistencia_recuperacion',  # FK → practicante
        'reportes_enviados',        # Sin dependencias
        'estado_asistencia',        # Se elimina (inline)
        'configuracion_servidor',   # Sin datos
    ]
    
    for table in TABLE_ORDER:
        if table not in tables_data:
            continue
        columns, rows = tables_data[table]
        
        output_lines.append(f"-- Tabla: {table} ({len(rows)} registros)")
        
        if table == 'practicante':
            output_lines.extend(generate_practicante_inserts(columns, rows))
        elif table == 'asistencia':
            output_lines.extend(generate_asistencia_inserts(columns, rows))
        elif table == 'bot_admins':
            output_lines.extend(generate_bot_admin_inserts(columns, rows))
        elif table == 'asistencia_recuperacion':
            output_lines.extend(generate_recuperacion_inserts(columns, rows))
        elif table == 'reportes_enviados':
            output_lines.extend(generate_reportes_enviados_inserts(columns, rows))
        elif table == 'estado_asistencia':
            output_lines.append("-- Tabla estado_asistencia eliminada (estados inline)")
        elif table == 'configuracion_servidor':
            output_lines.append("-- Sin datos en configuracion_servidor")
        
        output_lines.append("")
    
    # Ajustar secuencias
    output_lines.extend([
        "-- Ajustar secuencias al máximo ID existente",
        "SELECT setval('practicante_id_seq', (SELECT COALESCE(MAX(id), 1) FROM practicante));",
        "SELECT setval('asistencia_id_seq', (SELECT COALESCE(MAX(id), 1) FROM asistencia));",
        "SELECT setval('recuperacion_id_seq', (SELECT COALESCE(MAX(id), 1) FROM recuperacion));",
        "SELECT setval('reporte_id_seq', (SELECT COALESCE(MAX(id), 1) FROM reporte));",
        "",
        "COMMIT;",
        ""
    ])
    
    # Escribir archivo de salida
    output_file = 'migracion_postgres_datos.sql'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"✅ Migración generada: {output_file}")
    print(f"   Ejecutar con:")
    print(f"   docker exec -i postgres_db psql -U bot_user -d asistencia_rp_soft < {output_file}")


if __name__ == '__main__':
    main()

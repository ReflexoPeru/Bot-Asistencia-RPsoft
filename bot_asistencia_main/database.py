import os
import asyncpg
import logging
from dotenv import load_dotenv
from typing import Optional, Union, Tuple, Dict, Any, List

load_dotenv()

# Configuración de conexión PostgreSQL
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

# Pool de conexiones global
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool(min_size: int = 1, max_size: int = 10) -> asyncpg.Pool:
    """Inicializa el pool de conexiones de PostgreSQL."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            min_size=min_size,
            max_size=max_size,
            **DB_CONFIG
        )
        logging.info("✅ Pool de conexiones PostgreSQL inicializado.")
    return _pool


async def close_db_pool() -> None:
    """Cierra el pool de conexiones."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logging.info("🔒 Pool de conexiones PostgreSQL cerrado.")


async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Ejecuta un query y retorna una fila como dict."""
    pool = await init_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Ejecuta un query y retorna todas las filas como lista de dicts."""
    pool = await init_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def execute_query(query: str, *args) -> Optional[int]:
    """
    Ejecuta un query de escritura (INSERT, UPDATE, DELETE).
    Para INSERT con RETURNING id, retorna el id insertado.
    """
    pool = await init_db_pool()
    async with pool.acquire() as conn:
        # Si el query tiene RETURNING, usamos fetchrow
        if 'RETURNING' in query.upper():
            row = await conn.fetchrow(query, *args)
            return row[0] if row else None
        else:
            await conn.execute(query, *args)
            return None


async def execute_many(query: str, args_list: list) -> None:
    """Ejecuta un query con múltiples sets de parámetros."""
    pool = await init_db_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(query, args_list)


async def ensure_db_setup():
    """Verifica y crea las tablas necesarias con el nuevo esquema PostgreSQL."""
    logging.info("Verificando integridad de la base de datos PostgreSQL...")

    pool = await init_db_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():

            # ========================================
            # TABLA 1: practicante (expandida)
            # ========================================
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS practicante (
                id              SERIAL PRIMARY KEY,
                id_discord      BIGINT NOT NULL UNIQUE,
                nombre_completo VARCHAR(255) NOT NULL,
                correo          VARCHAR(255),
                clase_lunes     BOOLEAN DEFAULT FALSE,
                clase_martes    BOOLEAN DEFAULT FALSE,
                clase_miercoles BOOLEAN DEFAULT FALSE,
                clase_jueves    BOOLEAN DEFAULT FALSE,
                clase_viernes   BOOLEAN DEFAULT FALSE,
                clase_sabado    BOOLEAN DEFAULT FALSE,
                convenio        VARCHAR(20) DEFAULT 'no',
                semestre        SMALLINT,
                rol             VARCHAR(50),
                fecha_inscripcion DATE DEFAULT CURRENT_DATE,
                matriculado     BOOLEAN DEFAULT FALSE,
                dni             VARCHAR(15),
                numero          VARCHAR(20),
                sede            VARCHAR(100),
                carrera         VARCHAR(150),
                usuario_github  VARCHAR(100),
                usuario_discord VARCHAR(100),
                estado          VARCHAR(20) DEFAULT 'activo',
                fecha_retiro    DATE,
                motivo_retiro   VARCHAR(255),
                baneos          INT DEFAULT 0,
                horas_base      INTERVAL DEFAULT '0 hours'
            );
            """)

            # ========================================
            # TABLA 2: reporte (unificada, multi-tipo)
            # ========================================
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS reporte (
                id              SERIAL PRIMARY KEY,
                practicante_id  INT NOT NULL REFERENCES practicante(id) ON DELETE CASCADE,
                descripcion     TEXT NOT NULL,
                tipo            VARCHAR(30) NOT NULL,
                fecha           DATE NOT NULL DEFAULT CURRENT_DATE,
                revisado        BOOLEAN DEFAULT FALSE,
                creado_por      BIGINT,
                created_at      TIMESTAMP DEFAULT NOW()
            );
            """)

            # Índices para reporte
            await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reporte_practicante ON reporte(practicante_id);
            """)
            await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reporte_fecha ON reporte(fecha);
            """)
            await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reporte_tipo ON reporte(tipo);
            """)

            # ========================================
            # TABLA 3: asistencia (estados inline)
            # ========================================
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS asistencia (
                id              SERIAL PRIMARY KEY,
                practicante_id  INT NOT NULL REFERENCES practicante(id) ON DELETE CASCADE,
                estado          VARCHAR(20) NOT NULL,
                fecha           DATE NOT NULL,
                hora_entrada    TIME,
                hora_salida     TIME,
                salida_auto     BOOLEAN DEFAULT FALSE,
                dispositivo     VARCHAR(10),
                UNIQUE (practicante_id, fecha)
            );
            """)

            await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_asistencia_fecha ON asistencia(fecha);
            """)
            await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_asistencia_estado ON asistencia(estado);
            """)

            # ========================================
            # TABLA 4: recuperacion
            # ========================================
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS recuperacion (
                id              SERIAL PRIMARY KEY,
                practicante_id  INT NOT NULL REFERENCES practicante(id) ON DELETE CASCADE,
                fecha           DATE NOT NULL,
                hora_entrada    TIME NOT NULL,
                hora_salida     TIME,
                estado          VARCHAR(15) DEFAULT 'abierto',
                salida_auto     BOOLEAN DEFAULT FALSE,
                UNIQUE (practicante_id, fecha)
            );
            """)

            # ========================================
            # TABLA 5: bot_admin
            # ========================================
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_admin (
                discord_id      BIGINT PRIMARY KEY,
                nombre_discord  VARCHAR(255),
                rol             VARCHAR(100) DEFAULT 'Developer'
            );
            """)

            # ========================================
            # TABLAS DE SOPORTE
            # ========================================
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS reportes_enviados (
                fecha       DATE PRIMARY KEY,
                enviado_at  TIMESTAMP DEFAULT NOW()
            );
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS configuracion_servidor (
                guild_id                BIGINT PRIMARY KEY,
                canal_asistencia_id     BIGINT,
                canal_reportes_id       BIGINT,
                usuarios_mencion_reporte TEXT,
                mensaje_bienvenida      TEXT
            );
            """)

            # ========================================
            # INSERTAR EQUIPO INICIAL (si no existe)
            # ========================================
            admins = [
                (615932763161362636, 'Renso Mamani', 'Dev Principal'),
                (824692049084678144, 'Wilber Peralta', 'Product Owner'),
            ]
            for discord_id, nombre, rol in admins:
                await conn.execute("""
                INSERT INTO bot_admin (discord_id, nombre_discord, rol)
                VALUES ($1, $2, $3)
                ON CONFLICT (discord_id) DO NOTHING
                """, discord_id, nombre, rol)

    logging.info("✅ Base de datos PostgreSQL inicializada correctamente.")

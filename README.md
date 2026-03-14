# 🤖 Bot de Asistencia RP Soft

Automatiza asistencia de practicantes vía Discord, guarda todo en PostgreSQL y sincroniza con Google Sheets. Incluye un backend Spring Boot para APIs internas y un bot en Python con tareas programadas.

## 🧩 Stack
- Bot: Python 3.10 + discord.py + asyncpg
- Backend: Spring Boot (Java) expuesto en `9090`
- Base de datos: PostgreSQL 16 (puerto `5432`)
- Webhook liviano para métricas: puerto `10000` mapeado a `8081` en local

## 🚀 Inicio Rápido (Docker)
1. Clona el repo:
   ```bash
   git clone https://github.com/ReflexoPeru/Bot-Asistencia-RPsoft.git
   cd Bot-Asistencia-RPsoft
   ```
2. Crea un `.env` en la raíz con tus claves:
   ```env
   DISCORD_TOKEN=xxx
   BACKEND_API_KEY=xxx
   BACKEND_URL=http://backend:9090/api/v1
   DB_HOST=db
   DB_PORT=5432
   DB_NAME=asistencia_rp_soft
   DB_USER=postgres
   DB_PASSWORD=postgres
   GOOGLE_SHEET_NAME=Bot_de_asistencia_2026
   TZ=America/Lima
   LOG_LEVEL=INFO
   ```
3. Coloca `bot_asistencia_main/credentials.json` (Service Account de Google Sheets).
4. Levanta todo:
   ```bash
   docker compose up -d --build
   ```
5. Revisa logs si algo falla:
   ```bash
   docker compose logs -f bot
   docker compose logs -f backend
   ```

## 🏗️ Estructura del Proyecto
- `bot_asistencia_main/bot.py`: Arranque del bot y carga de cogs/tareas.
- `bot_asistencia_main/database.py`: Conexión y schema bootstrap para PostgreSQL.
- `bot_asistencia_main/cogs/`: Comandos de asistencia, administración y tareas programadas.
- `backend-java/`: API Spring Boot que consume la misma base PostgreSQL.
- `docs/` y `bot_asistencia_main/docs/`: Guías de BD, deployment y Google Cloud.

## 🛠️ Comandos Principales
- `/entrada`, `/salida`, `/estado`, `/historial` para practicantes.
- `/admin editar_asistencia`, `/admin equipo`, `/admin eliminar_practicante`, `/admin sincronizar` para admins.

## ⚙️ Configuración rápida
- Tiempos y reglas: `bot_asistencia_main/bot/config/constants.py`.
- Canales permitidos y roles: `bot_asistencia_main/bot/config/settings.py`.

## ❓ Troubleshooting
- Bot sin respuesta: valida `DISCORD_TOKEN` y que el canal esté en `CANALES_PERMITIDOS`.
- Google Sheets: comparte el sheet con el `client_email` de `credentials.json`.
- Base de datos: `docker compose logs -f db` y confirma que `DB_HOST=db`.

**Última actualización:** 2026-03-14

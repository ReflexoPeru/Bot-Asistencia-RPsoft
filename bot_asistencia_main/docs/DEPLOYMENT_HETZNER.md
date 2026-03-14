# 🚀 Guía de Deployment - Bot de Asistencia en Hetzner VPS

Pasos rápidos para desplegar el bot (Python), backend (Spring Boot) y PostgreSQL usando Docker Compose.

## 📋 Requisitos
- VPS con Docker y Docker Compose instalados (`docker --version`, `docker compose version`).
- Archivos locales listos: `.env` en la raíz del proyecto y `bot_asistencia_main/credentials.json`.

## 🔧 Paso 1: Conectarse al VPS
```bash
ssh root@tu_ip_del_vps
```

## 📁 Paso 2: Preparar directorio
```bash
mkdir -p ~/bot_asistencia
cd ~/bot_asistencia
```

## 📤 Paso 3: Clonar el proyecto
```bash
git clone https://github.com/ReflexoPeru/Bot-Asistencia-RPsoft.git .
```

## 🔐 Paso 4: Cargar secretos
1) `.env` en la raíz (mismos nombres que usa `docker-compose.yml`):
```bash
nano .env
```
Incluye al menos: `DISCORD_TOKEN`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `BACKEND_API_KEY`, `BACKEND_URL`, `GOOGLE_SHEET_NAME`.

2) `credentials.json` para Google Sheets:
```bash
cd bot_asistencia_main
nano credentials.json
```
Guarda y vuelve a la raíz (`cd ..`).

## 🐳 Paso 5: Levantar servicios
```bash
docker compose up -d --build
```
Servicios y puertos expuestos:
- `db` (PostgreSQL): 5432
- `bot` (Discord bot + web liviano): 8081 → contenedor 10000
- `backend` (Spring Boot): 9090

## 📊 Paso 6: Verificación y logs
```bash
docker compose ps
docker compose logs -f bot
docker compose logs -f backend
```
Usa `Ctrl + C` para salir de los logs sin apagar contenedores.

## 🎯 Comandos útiles
- Reiniciar servicios: `docker compose restart`
- Actualizar código: `git pull && docker compose up -d --build`
- Apagar todo: `docker compose down`

**Última actualización:** 2026-03-14

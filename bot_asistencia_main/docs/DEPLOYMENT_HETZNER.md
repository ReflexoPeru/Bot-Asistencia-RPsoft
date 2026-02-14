# 🚀 Guía de Deployment - Bot de Asistencia en Hetzner VPS

Esta guía detalla los pasos para poner el bot en marcha en un servidor VPS de Hetzner de manera rápida.

## 📋 Requisitos Iniciales
Para que el bot funcione, debes tener listos en tu PC estos dos archivos:
1.  **`.env`**: Archivo con los tokens y claves de la base de datos.
2.  **`credentials.json`**: La llave de Google que generamos anteriormente.

---

## 🔧 Paso 1: Conectarse al VPS
Usa tu terminal (PowerShell o CMD en Windows) para conectarte por SSH:
```bash
ssh root@tu_ip_del_vps
```

*Nota: Por seguridad, el VPS ya debe tener instalado Docker y Docker Compose. Si no es así, verifica con `docker --version`.*

---

## 📁 Paso 2: Crear Directorio del Proyecto
En el servidor, crea una carpeta para mantener el orden:
```bash
mkdir -p ~/bot_asistencia
cd ~/bot_asistencia
```

---

## 📤 Paso 3: Clonar el Proyecto (Git)
Descarga el código directamente desde el repositorio oficial:
```bash
git clone https://github.com/ReflexoPeru/Bot-Asistencia-RPsoft.git .
```

---

## 🔐 Paso 4: Configurar Archivos Sensibles
Debes crear manualmente los archivos que Git ignora por seguridad:

1.  **Crear archivo .env**:
    ```bash
    nano .env
    ```
    Pega el contenido de tu configuración (Tokens de Discord, DB_HOST, DB_USER, etc.).
    *Nota: No es necesario configurar el backend si no se usa.*

2.  **Crear credentials.json**:
    ```bash
    cd bot_asistencia_main
    nano credentials.json
    ```
    Pega el contenido del JSON que descargaste de Google Cloud.

Sal de nano con `Ctrl + O` (guardar), `Enter` y `Ctrl + X` (salir).

---

## 🐳 Paso 5: Lanzar el Bot
Regresa a la carpeta principal donde está el archivo `docker-compose.yml` y ejecuta:
```bash
docker-compose up -d --build
```
Este comando construirá la imagen y encenderá los contenedores del Bot y la Base de Datos en segundo plano.

---

## 📊 Paso 6: Verificación y Logs
Para confirmar que todo está corriendo bien y ver los mensajes del bot en tiempo real:
```bash
docker-compose logs -f bot-asistencia
```
Para salir de los logs sin apagar el bot, presiona `Ctrl + C`.

---

## 🎯 Resumen de Comandos Rápidos
- **Reiniciar el Bot**: `docker-compose restart`
- **Actualizar Código**: `git pull && docker-compose up --build -d`
- **Apagar Todo**: `docker-compose down`
- **Ver Estado**: `docker-compose ps`

---

**Última actualización:** 2026-02-14
**Autor:** Renso Abraham - RpSoft

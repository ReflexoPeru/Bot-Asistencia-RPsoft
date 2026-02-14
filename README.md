# 🤖 Bot de Asistencia RP Soft

Bienvenido a la documentación oficial del Bot de Asistencia. Este sistema está diseñado para automatizar el registro de entrada, salida y horas totales de los practicantes a través de Discord, sincronizando toda la información en tiempo real con Google Sheets.

## 🚀 Inicio Rápido

Para trabajar con este proyecto en tu entorno local (PC), sigue estos pasos:

1.  **Clonar el proyecto**:
    ```bash
    git clone https://github.com/ReflexoPeru/Bot-Asistencia-RPsoft.git
    cd Bot-Asistencia-RPsoft
    ```
2.  **Configuración**:
    - Crea un archivo `.env` basado en el ejemplo proporcionado.
    - Coloca tu archivo `credentials.json` en la carpeta `bot_asistencia_main/`.
3.  **Lanzar con Docker**:
    Asegúrate de tener **Docker Desktop** instalado y ejecuta:
    ```bash
    docker-compose up -d --build
    ```

---

## 🏗️ Estructura del Proyecto

- **`bot.py`**: Núcleo principal del bot. Aquí se inician las tareas programadas y se cargan los comandos.
- **`cogs/`**: Contiene los módulos de comandos divididos por categorías (asistencia, administración, etc.).
- **`database.py`**: Gestiona la conexión con la base de datos MySQL y la creación automática de tablas.
- **`google_sheets.py`**: Se encarga de la comunicación con la API de Google para actualizar los reportes.
- **`bot/config/`**: Aquí puedes modificar los horarios de entrada, tardanza y constantes del sistema.
- **`docs/`**: Guías detalladas para la creación de cuentas de servicio y despliegue en servidores.

---

## 🛠️ Comandos Principales

### Para Practicantes
- `/entrada`: Registra el inicio de tu jornada.
- `/salida`: Registra el fin de tu jornada (calcula horas automáticas).
- `/estado`: Consulta si tienes una sesión activa.
- `/historial`: Mira tus registros de los últimos días.

### Para Administradores
- `/admin editar_asistencia`: Corrige o añade registros manualmente.
- `/admin equipo`: Gestiona los encargados del bot.
- `/admin eliminar_practicante`: Borra toda la data de un practicante que se retira.
- `/admin sincronizar`: Fuerza la actualización inmediata del Google Sheets.

---

## ⚙️ Configuración Importante

En el archivo `bot/config/constants.py` puedes ajustar:
- **Horario de entrada**: 8:00 AM.
- **Tolerancia/Tardanza**: Hasta las 8:10 AM (a las 8:11 AM ya es tardanza).
- **Salida mínima**: 2:30 PM.

---

## ❓ Troubleshooting Común

- **¿El bot no responde?** Verifica que el ID del canal en `settings.py` coincida con tu servidor de Discord.
- **¿Error en Google Sheets?** Asegúrate de haber compartido el Excel con el email de tu `Service Account`.
- **¿Problemas de DB?** Chequea los logs con `docker-compose logs -f`.

---

**Última actualización:** 2026-02-14
**Autor:** Renso Abraham - RpSoft

# 🔐 Guía: Crear Service Account de Google para el Bot de Asistencia

Esta guía explica cómo obtener las credenciales necesarias para que el bot pueda leer y escribir en Google Sheets.

## 📋 ¿Por qué necesitamos esto?

El bot usa Google Sheets API para sincronizar datos. Necesitamos crear un **Service Account** para que el sistema tenga su propia identidad y permisos, sin depender de accesos manuales.

---

## 🎯 Paso 1: Crear Proyecto en Google Cloud

1.  **Ir a Google Cloud Console**: Abre [https://console.cloud.google.com/](https://console.cloud.google.com/) e inicia sesión con tu cuenta de Google (puedes usar tu cuenta personal o de desarrollador para la creación).
2.  **Crear Nuevo Proyecto**: 
    - Click en el selector de proyectos (arriba a la izquierda).
    - Click en **"Nuevo Proyecto"**.
    - Nombre del proyecto: `Bot-Asistencia-RP-Soft`.
    - Click en **"Crear"** y espera a que se active.
3.  **Seleccionar Proyecto**: Asegúrate de que el proyecto `Bot-Asistencia-RP-Soft` esté seleccionado en la parte superior.

---

## 🔌 Paso 2: Habilitar APIs Necesarias

Debes activar dos servicios para que el bot funcione:

1.  **Google Sheets API**: Ve a "APIs y servicios" → "Biblioteca". Busca `Google Sheets API` y dale a **Habilitar**.
2.  **Google Drive API**: Regresa a la "Biblioteca", busca `Google Drive API` y dale a **Habilitar**.

---

## 👤 Paso 3: Crear Service Account

1.  Ve a **APIs y servicios** → **Credenciales**.
2.  Click en **"+ Crear credenciales"** → **"Cuenta de servicio"**.
3.  **Configurar**:
    - Nombre: `bot-asistencia-rp-soft`
    - Descripción: `Cuenta para el bot de asistencia`
    - Click en **"Crear y continuar"**.
4.  **Función**: Selecciona la función de **Editor** para que tenga permisos de escritura.
5.  Dale a **"Listo"**.

---

## 🔑 Paso 4: Generar Clave JSON

1.  En la lista de cuentas de servicio, haz clic en el **email** de la cuenta que acabas de crear.
2.  Ve a la pestaña **"Claves"** (Keys).
3.  Click en **"Agregar clave"** → **"Crear clave nueva"**.
4.  Selecciona el formato **JSON** y dale a **Crear**.
5.  Se descargará un archivo `.json`. 
    - **⚠️ IMPORTANTE:** Renombra este archivo a `credentials.json`.
    - Pon este archivo en la carpeta principal del bot (donde está el archivo `bot.py`).
    - **NO compartas este archivo** ni lo subas a GitHub, ya que es la llave de acceso a tus datos.

---

## 📊 Paso 5: Compartir Google Sheet con el Bot

1.  Abre tu archivo `credentials.json` con un bloc de notas y busca el email donde dice `"client_email"`.
2.  Abre tu Google Sheet (Excel) de asistencia.
3.  Click en **"Compartir"** (arriba a la derecha).
4.  Pega el email del Service Account.
5.  Asegúrate de que tenga permisos de **"Editor"**.
6.  Desmarca "Notificar a las personas" y dale a **Compartir**.

---

**Última actualización:** 2026-02-14
**Autor:** Renso Abraham - RpSoft

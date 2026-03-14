# Comandos y API de Capacitación

## Alcance
- Python (bot Discord) solo orquesta permisos y llamadas REST.
- Java (Spring Boot) ejecuta la lógica de negocio, validaciones y cálculos de tiempo.
- Estados válidos: `planned | in_progress | paused | finished | cancelled`.

## Endpoints Java (backend)
Base: `/api/v1/capacitacion`

### Cursos y temas
- **Crear curso** `POST /curso`
  - Body:
    ```json
    {"nombre":"Node.js","descripcion":"Curso de Node","activo":true,
     "temas":[{"nombre":"Intro","orden":1,"descripcion":"Fundamentos","duracionRefDias":1}]}
    ```
  - `201 Created` → `CapacitacionCursoDto` con `id` y temas.
  - Errores: `409` curso duplicado; `400` temas duplicados en payload.

- **Agregar temas** `POST /curso/{id}/temas`
  - Body:
    ```json
    {"temas":[{"nombre":"Async","orden":3,"duracionRefDias":2}]}
    ```
  - `201 Created` → curso con todos los temas.
  - Errores: `404` curso no encontrado; `409` nombre/orden ya existen; `400` sin temas.

### Progresos
- **Listar por practicante** `GET /practicante/{id}?curso={opcional}` → cursos/temas con progreso.
- **Iniciar** `POST /iniciar`
  ```json
  {"practicanteId":1,"cursoNombre":"Node.js","temaNombre":"Intro",
   "evaluadorId":2,"crearSiNoExiste":true}
  ```
- **Pausar** `POST /pausar`
- **Reanudar** `POST /reanudar`
- **Finalizar** `POST /finalizar`
  - Cuerpo base para pausar/reanudar/finalizar:
    ```json
    {"practicanteId":1,"cursoNombre":"Node.js","temaNombre":"Intro"}
    ```
  - Errores: `404` practicante/curso/tema; `409` estado inválido; `400` tema no corresponde a curso; `409` progreso ya existe para ese tema.

### Evaluadores
- **Asignar evaluador** `PATCH /evaluador`
  ```json
  {"practicanteId":1,"cursoNombre":"Node.js","temaNombre":"Intro","evaluadorId":2}
  ```
- **Activar evaluador** `POST /evaluador/activar`
  ```json
  {"practicanteId":2,"notas":"Senior JS"}
  ```
- **Desactivar evaluador** `POST /evaluador/desactivar`
  ```json
  {"practicanteId":2}
  ```
  - Reglas: evaluador ≠ practicante; evaluador debe estar activo; `409` si progreso cancelado.

## Comandos esperados en el bot (Python)
> El bot debe validar permisos admin antes de invocar los endpoints.

- `/admin capacitacion crear-curso nombre:<texto> [descripcion] [activo:true|false] [temas:<lista>]`
  - Llama a `POST /curso`. `temas` se puede pasar como lista parseada (p.ej. `"Intro|1|1; Async|2|2"`).

- `/admin capacitacion agregar-temas curso:<nombre|id> temas:<lista>`
  - Llama a `POST /curso/{id}/temas` (preferir id) o nombre→id vía lookup.

- `/admin capacitacion ver practicante:<@usuario> [curso:<nombre>]`
  - Llama a `GET /practicante/{id}` (con query `curso` opcional).

- `/admin capacitacion iniciar practicante:<@usuario> curso:<nombre> tema:<nombre> [evaluador:<@usuario>]`
  - `POST /iniciar` (con `crearSiNoExiste=true`).

- `/admin capacitacion pausar|reanudar|finalizar practicante:<@usuario> curso:<nombre> tema:<nombre>`
  - `POST /pausar|reanudar|finalizar`.

- `/admin capacitacion asignar-evaluador practicante:<@usuario> curso:<nombre> tema:<nombre> evaluador:<@usuario>`
  - `PATCH /evaluador`.

- `/admin capacitacion hacer-evaluador practicante:<@usuario> [notas]`
  - `POST /evaluador/activar`.

- `/admin capacitacion quitar-evaluador practicante:<@usuario>`
  - `POST /evaluador/desactivar`.

## Formatos de respuesta sugeridos (Discord)
- Lista de cursos/temas por practicante:
  ```
  👤 Juan Pérez
  📘 Node.js
    📌 Tema 1 – Intro
       👨‍🏫 Evaluador: @Carlos
       🟢 Inicio: 01/06/2025 09:00
       🔴 Fin:    03/06/2025 17:00
       ⏱  Duración: 2 días
  ```
- En progreso: usar "🔄 En progreso: 5h 30min" (duración calculada en Java).
- Sin iniciar: "⏳ Sin iniciar".

## Reglas de negocio clave
- Evaluador único por progreso; no puede ser el mismo practicante.
- Evaluador debe estar activo en `capacitacion_evaluador`.
- Un evaluador puede tener sus propios progresos como practicante.
- Tiempos truncados a segundos.
- `cancelled` bloquea cualquier transición.

## Errores comunes (HTTP)
- `404 Practicante/Curso/Tema no encontrado`
- `400 Evaluador inválido o inactivo / Tema no corresponde al curso`
- `409 Estado inválido / Tema duplicado para practicante / Curso o tema duplicado`


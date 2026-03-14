import aiohttp
import discord
from discord import app_commands, Embed, Color
import database as db
import logging
from .helpers import verificar_admin


async def _autocomplete_cursos_activos(interaction: discord.Interaction, current: str):
    filtro = f"%{current}%" if current else "%"
    rows = await db.fetch_all(
        "SELECT id, nombre FROM capacitacion_curso WHERE activo = true AND nombre ILIKE $1 ORDER BY nombre LIMIT 25",
        filtro,
    )
    # Mostrar id en la etiqueta, pero enviar el nombre como valor para que el backend resuelva por nombre
    return [app_commands.Choice(name=f"{row['nombre']} (id {row['id']})", value=row['nombre']) for row in rows]


async def _autocomplete_temas_por_curso(interaction: discord.Interaction, current: str):
    curso_val = getattr(interaction.namespace, "curso", None)
    if curso_val is None:
        return []
    curso_id = await _resolver_curso_id(str(curso_val))
    if not curso_id:
        return []
    filtro = f"%{current}%" if current else "%"
    rows = await db.fetch_all(
        "SELECT nombre, orden FROM capacitacion_tema WHERE curso_id = $1 AND nombre ILIKE $2 ORDER BY orden LIMIT 25",
        curso_id,
        filtro,
    )
    return [app_commands.Choice(name=f"{row['orden']}. {row['nombre']}", value=row['nombre']) for row in rows]


def _duration_to_str(iso_str: str) -> str:
    if not iso_str:
        return "0s"
    try:
        iso = iso_str.replace('PT', '')
        h, m, s = 0, 0, 0
        num = ''
        for ch in iso:
            if ch.isdigit():
                num += ch
            else:
                if ch == 'H':
                    h = int(num or 0)
                elif ch == 'M':
                    m = int(num or 0)
                elif ch == 'S':
                    s = int(num or 0)
                num = ''
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception:
        return iso_str


class CapacitacionCommands:
    capacitacion = app_commands.Group(name="capacitacion", description="Gestión de capacitación")

    @capacitacion.command(name="ver", description="Ver progreso de capacitación de un practicante")
    @app_commands.describe(practicante="Practicante a consultar", curso="Opcional: curso a filtrar")
    async def ver(self, interaction: discord.Interaction, practicante: discord.Member, curso: str | None = None):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        prac = await db.fetch_one("SELECT id, nombre_completo FROM practicante WHERE id_discord = $1", practicante.id)
        if not prac:
            await interaction.followup.send("❌ Practicante no encontrado en la BD.", ephemeral=True)
            return

        base_url = getattr(self.bot, '_backend_url', 'http://backend:9090/api/v1')
        params = f"?curso={curso}" if curso else ""
        url = f"{base_url}/capacitacion/practicante/{prac['id']}{params}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = _embed_progreso(data)
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    elif resp.status == 404:
                        await interaction.followup.send("📭 Practicante o curso no encontrado.", ephemeral=True)
                    else:
                        await interaction.followup.send(f"❌ Error HTTP {resp.status}", ephemeral=True)
        except Exception as e:
            logging.exception("Error consultando capacitación")
            await interaction.followup.send("❌ Error al contactar al backend.", ephemeral=True)

    @capacitacion.command(name="iniciar", description="Iniciar progreso de un tema")
    @app_commands.describe(practicante="Practicante", curso="Curso", tema="Tema", evaluador="Evaluador (opcional)")
    @app_commands.autocomplete(curso=_autocomplete_cursos_activos, tema=_autocomplete_temas_por_curso)
    async def iniciar(self, interaction: discord.Interaction, practicante: discord.Member, curso: str, tema: str, evaluador: discord.Member | None = None):
        await self._mutate(interaction, "iniciar", practicante, curso, tema, evaluador)

    @capacitacion.command(name="pausar", description="Pausar progreso en curso")
    @app_commands.autocomplete(curso=_autocomplete_cursos_activos, tema=_autocomplete_temas_por_curso)
    async def pausar(self, interaction: discord.Interaction, practicante: discord.Member, curso: str, tema: str):
        await self._mutate(interaction, "pausar", practicante, curso, tema)

    @capacitacion.command(name="reanudar", description="Reanudar progreso pausado")
    @app_commands.autocomplete(curso=_autocomplete_cursos_activos, tema=_autocomplete_temas_por_curso)
    async def reanudar(self, interaction: discord.Interaction, practicante: discord.Member, curso: str, tema: str):
        await self._mutate(interaction, "reanudar", practicante, curso, tema)

    @capacitacion.command(name="finalizar", description="Finalizar progreso en curso")
    @app_commands.autocomplete(curso=_autocomplete_cursos_activos, tema=_autocomplete_temas_por_curso)
    async def finalizar(self, interaction: discord.Interaction, practicante: discord.Member, curso: str, tema: str):
        await self._mutate(interaction, "finalizar", practicante, curso, tema)

    @capacitacion.command(name="asignar_evaluador", description="Asignar evaluador a un tema")
    @app_commands.autocomplete(curso=_autocomplete_cursos_activos, tema=_autocomplete_temas_por_curso)
    async def asignar_evaluador(self, interaction: discord.Interaction, practicante: discord.Member, curso: str, tema: str, evaluador: discord.Member):
        await self._mutate(interaction, "evaluador", practicante, curso, tema, evaluador, method="PATCH")

    @capacitacion.command(name="hacer_evaluador", description="Activar practicante como evaluador")
    async def hacer_evaluador(self, interaction: discord.Interaction, practicante: discord.Member, notas: str | None = None):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        prac = await db.fetch_one("SELECT id, nombre_completo FROM practicante WHERE id_discord = $1", practicante.id)
        if not prac:
            await interaction.followup.send("❌ Practicante no encontrado en la BD.", ephemeral=True)
            return

        payload = {"practicanteId": prac['id'], "notas": notas}
        await self._post_simple(interaction, "evaluador/activar", payload, f"🆙 {prac['nombre_completo']} ahora es evaluador (activo)")

    @capacitacion.command(name="quitar_evaluador", description="Desactivar evaluador")
    async def quitar_evaluador(self, interaction: discord.Interaction, practicante: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        prac = await db.fetch_one("SELECT id, nombre_completo FROM practicante WHERE id_discord = $1", practicante.id)
        if not prac:
            await interaction.followup.send("❌ Practicante no encontrado en la BD.", ephemeral=True)
            return

        payload = {"practicanteId": prac['id']}
        await self._post_simple(interaction, "evaluador/desactivar", payload, f"🚫 {prac['nombre_completo']} desactivado como evaluador")

    @capacitacion.command(name="crear_curso", description="Crear curso y temas (opcional)")
    @app_commands.describe(nombre="Nombre del curso", descripcion="Descripción", activo="Activo?", temas="Formato: Nombre|Orden|DuracionDias;...")
    async def crear_curso(self, interaction: discord.Interaction, nombre: str, descripcion: str | None = None, activo: bool = True, temas: str | None = None):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return
        temas_list = _parse_temas(temas) if temas else []
        payload = {
            "nombre": nombre,
            "descripcion": descripcion,
            "activo": activo,
            "temas": temas_list
        }
        base_url = getattr(self.bot, '_backend_url', 'http://backend:9090/api/v1')
        url = f"{base_url}/capacitacion/curso"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status in (200, 201):
                        await interaction.followup.send(f"✅ Curso creado: {data.get('nombre')} (id {data.get('id')})", ephemeral=True)
                    else:
                        msg = data.get('message') if isinstance(data, dict) else str(data)
                        await interaction.followup.send(f"❌ {msg} (HTTP {resp.status})", ephemeral=True)
        except Exception:
            logging.exception("Error creando curso")
            await interaction.followup.send("❌ Error al contactar al backend.", ephemeral=True)

    @capacitacion.command(name="agregar_temas", description="Agregar temas a un curso existente")
    @app_commands.describe(curso="ID o nombre del curso", temas="Formato: Nombre|Orden|DuracionDias;...")
    @app_commands.autocomplete(curso=_autocomplete_cursos_activos)
    async def agregar_temas(self, interaction: discord.Interaction, curso: str, temas: str):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        curso_id = await _resolver_curso_id(curso)
        if not curso_id:
            await interaction.followup.send("❌ Curso no encontrado.", ephemeral=True)
            return

        temas_list = _parse_temas(temas)
        if not temas_list:
            await interaction.followup.send("❌ Debes enviar al menos un tema (Nombre|Orden|DuracionDias).", ephemeral=True)
            return

        base_url = getattr(self.bot, '_backend_url', 'http://backend:9090/api/v1')
        url = f"{base_url}/capacitacion/curso/{curso_id}/temas"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"temas": temas_list}) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status in (200, 201):
                        await interaction.followup.send(f"✅ Temas agregados al curso {data.get('nombre')} (id {data.get('id')})", ephemeral=True)
                    else:
                        msg = data.get('message') if isinstance(data, dict) else str(data)
                        await interaction.followup.send(f"❌ {msg} (HTTP {resp.status})", ephemeral=True)
        except Exception:
            logging.exception("Error agregando temas")
            await interaction.followup.send("❌ Error al contactar al backend.", ephemeral=True)

    # --------------- helpers ---------------
    async def _mutate(self, interaction: discord.Interaction, accion: str, practicante: discord.Member, curso: str, tema: str, evaluador: discord.Member | None = None, method: str = "POST"):
        await interaction.response.defer(ephemeral=True)
        if not await verificar_admin(interaction):
            return

        prac = await db.fetch_one("SELECT id, nombre_completo FROM practicante WHERE id_discord = $1", practicante.id)
        if not prac:
            await interaction.followup.send("❌ Practicante no encontrado en la BD.", ephemeral=True)
            return

        eval_row = None
        if evaluador:
            eval_row = await db.fetch_one("SELECT id, nombre_completo FROM practicante WHERE id_discord = $1", evaluador.id)
            if not eval_row:
                await interaction.followup.send("❌ Evaluador no existe en la BD.", ephemeral=True)
                return

        base_url = getattr(self.bot, '_backend_url', 'http://backend:9090/api/v1')
        url = f"{base_url}/capacitacion/{accion}"
        payload = {
            "practicanteId": prac['id'],
            "cursoNombre": curso,
            "temaNombre": tema
        }
        if accion == "iniciar":
            payload["evaluadorId"] = eval_row['id'] if eval_row else None
        if accion == "evaluador":
            payload["evaluadorId"] = eval_row['id'] if eval_row else None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, json=payload) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status in (200, 201):
                        embed = _embed_progreso_unico(data)
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        mensaje = data.get('message') if isinstance(data, dict) else str(data)
                        await interaction.followup.send(f"❌ {mensaje} (HTTP {resp.status})", ephemeral=True)
        except Exception as e:
            logging.exception("Error mutando capacitación")
            await interaction.followup.send("❌ Error al contactar al backend.", ephemeral=True)

    async def _post_simple(self, interaction: discord.Interaction, path: str, payload: dict, success_msg: str):
        base_url = getattr(self.bot, '_backend_url', 'http://backend:9090/api/v1')
        url = f"{base_url}/capacitacion/{path}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        await interaction.followup.send(success_msg, ephemeral=True)
                    else:
                        data = await resp.json(content_type=None)
                        mensaje = data.get('message') if isinstance(data, dict) else str(data)
                        await interaction.followup.send(f"❌ {mensaje} (HTTP {resp.status})", ephemeral=True)
        except Exception:
            logging.exception("Error llamando endpoint simple")
            await interaction.followup.send("❌ Error al contactar al backend.", ephemeral=True)


def _embed_progreso(data: dict) -> Embed:
    embed = Embed(title=f"👤 {data.get('practicanteNombre', 'Practicante')}", color=Color.green())
    cursos = data.get('cursos', []) or []
    if not cursos:
        embed.description = "📭 Sin cursos configurados"
        return embed
    for curso in cursos:
        lineas = []
        for tema in curso.get('temas', []):
            estado = tema.get('estado', 'planned')
            base = f"📌 {tema.get('orden', '-')}. {tema.get('tema')} — **{estado}**"
            eval_data = tema.get('evaluador')
            if eval_data:
                base += f"\n👨‍🏫 {eval_data.get('nombre', 'Evaluador')}"
            if tema.get('fechaInicio'):
                base += f"\n🟢 Inicio: {tema.get('fechaInicio')}"
            if tema.get('fechaFin'):
                base += f"\n🔴 Fin: {tema.get('fechaFin')}"
            if estado == 'in_progress' and tema.get('acumulado'):
                base += f"\n🔄 En progreso: {_duration_to_str(tema.get('acumulado'))}"
            if estado == 'finished' and tema.get('duracionFinal'):
                base += f"\n⏱ Duración: {_duration_to_str(tema.get('duracionFinal'))}"
            lineas.append(base)
        embed.add_field(name=f"📘 {curso.get('curso')}", value="\n".join(lineas) or "(Sin temas)", inline=False)
    return embed


def _embed_progreso_unico(data: dict) -> Embed:
    embed = Embed(title=f"{data.get('curso')} — {data.get('tema')}", color=Color.blue())
    estado = data.get('estado', 'planned')
    embed.add_field(name="Estado", value=estado, inline=True)
    if data.get('evaluador'):
        embed.add_field(name="Evaluador", value=data['evaluador'].get('nombre', 'N/D'), inline=True)
    if data.get('fechaInicio'):
        embed.add_field(name="Inicio", value=str(data['fechaInicio']), inline=False)
    if data.get('fechaFin'):
        embed.add_field(name="Fin", value=str(data['fechaFin']), inline=False)
    if estado == 'in_progress' and data.get('acumulado'):
        embed.add_field(name="En progreso", value=_duration_to_str(data['acumulado']), inline=False)
    if estado == 'finished' and data.get('duracionFinal'):
        embed.add_field(name="Duración", value=_duration_to_str(data['duracionFinal']), inline=False)
    return embed


def _parse_temas(temas_str: str) -> list[dict]:
    temas = []
    if not temas_str:
        return temas
    for raw in temas_str.split(';'):
        raw = raw.strip()
        if not raw:
            continue
        parts = [p.strip() for p in raw.split('|')]
        if len(parts) < 2:
            continue
        nombre = parts[0]
        try:
            orden = int(parts[1]) if parts[1] else None
        except ValueError:
            continue
        duracion = None
        if len(parts) > 2 and parts[2]:
            try:
                duracion = int(parts[2])
            except ValueError:
                duracion = None
        temas.append({
            "nombre": nombre,
            "orden": orden,
            "duracionRefDias": duracion
        })
    return temas


async def _resolver_curso_id(curso: str) -> int | None:
    # Si viene numérico, úsalo directo
    if curso.isdigit():
        return int(curso)
    row = await db.fetch_one("SELECT id FROM capacitacion_curso WHERE lower(nombre) = lower($1)", curso)
    return row['id'] if row else None


"""Modales para el módulo de asistencia"""

import database as db
import discord
from discord import TextStyle, ui


class SalidaAnticipadaModal(ui.Modal, title="Salida Anticipada"):
    """Modal para registrar salida anticipada con motivo"""
    
    motivo = ui.TextInput(
        label="Motivo de la salida anticipada",
        style=TextStyle.paragraph,
        placeholder="Escribe tu motivo aquí...",
        required=True,
        max_length=255
    )

    def __init__(self, hora_actual, asistencia, nombre_usuario):
        super().__init__()
        self.hora_actual = hora_actual
        self.asistencia = asistencia
        self.nombre_usuario = nombre_usuario

    async def on_submit(self, interaction: discord.Interaction):
        """Maneja el envío del modal"""
        motivo_guardado = self.motivo.value

        # Actualizar salida con estado 'temprano' (ya tenía su estado original)
        query_update = """
            UPDATE asistencia 
            SET hora_salida = $1 
            WHERE id = $2
        """
        await db.execute_query(query_update, self.hora_actual, self.asistencia['id'])

        # Crear reporte de salida anticipada
        query_reporte = """
            INSERT INTO reporte (practicante_id, descripcion, tipo, fecha)
            VALUES ($1, $2, 'justificacion', CURRENT_DATE)
        """
        await db.execute_query(
            query_reporte,
            self.asistencia['practicante_id'],
            f"Salida anticipada: {motivo_guardado}"
        )

        await interaction.response.send_message(
            f"{self.nombre_usuario}, tu salida anticipada ha sido registrada.",
            ephemeral=True
        )

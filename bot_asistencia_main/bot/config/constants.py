"""
Constantes del sistema
Valores fijos utilizados en todo el bot
"""

from datetime import time
from typing import Set

# Horarios de entrada
HORARIO_ENTRADA_INICIO = time(7, 50)      # 7:50 AM
HORARIO_ENTRADA_FIN = time(14, 0)        # 2:00 PM
HORARIO_ENTRADA_TOLERANCIA = time(8, 10, 59) # 8:10:59 AM
HORA_LIMITE_TARDANZA = time(8, 10, 59)   # 8:10:59 AM
HORARIO_SALIDA_MINIMA = time(14, 30)     # 2:30 PM

# Horarios de recuperación
HORA_INICIO_RECUPERACION = time(14, 50)     # 2:50 PM
HORA_FIN_RECUPERACION = time(20, 0)         # 8:00 PM
MARGEN_TOLERANCIA_MINUTOS = 20
HORA_CIERRE_REAL = time(20, 20)             # 8:20 PM (FIN + MARGEN)
MAX_ADVERTENCIAS_CONSECUTIVAS = 3
HORAS_SEMANALES_REQUERIDAS = 36

# Días de la semana (0=Lunes, 6=Domingo)
# Solo permitir lunes a viernes (0-4)
DIAS_SEMANA_PERMITIDOS: Set[int] = {0, 1, 2, 3, 4}

# Límites de historial
DIAS_HISTORIAL_MIN = 1
DIAS_HISTORIAL_MAX = 15

DIAS_HISTORIAL_RECUPERACION_MIN = 1
DIAS_HISTORIAL_RECUPERACION_MAX = 30

# Límites de caracteres
MAX_LENGTH_MOTIVO = 255
MAX_LENGTH_NOMBRE = 100

# Mensajes comunes
MSG_CANAL_NO_PERMITIDO = "Este comando no está habilitado en este canal."
MSG_NO_REGISTRADO = "no estás registrado como practicante."
MSG_CONTACTO_ADMIN = "Si tienes dudas, contacta con el administrador."

LINK_FORMULARIO_REGISTRO = "https://docs.google.com/forms/d/e/1FAIpQLSe3_6V9xPss_HZIw7quWUMkP5juOxocxIVOBz8gC_zpw5iIiw/viewform?usp=publish-editor"

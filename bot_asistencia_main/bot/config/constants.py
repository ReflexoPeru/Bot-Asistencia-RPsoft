"""
Constantes del sistema
Valores fijos utilizados en todo el bot
"""

from datetime import time
from typing import Set

# Horarios de entrada
HORARIO_ENTRADA_INICIO = time(7, 50)         # 7:50 AM
HORARIO_ENTRADA_FIN = time(14, 0)            # 2:00 PM (última hora para registrar entrada)
HORARIO_ENTRADA_TOLERANCIA = time(8, 10, 59) # 8:10:59 AM — límite para 'temprano'
HORA_LIMITE_TARDANZA = time(9, 0, 0)         # 9:00:00 AM — después de esto es 'sobreHora'

# Horarios de salida asistencia
HORA_SALIDA_OFICIAL = time(14, 0)            # 2:00 PM — hora oficial de salida
HORA_GRACIA_SALIDA = time(14, 15)            # 2:15 PM — gracia para marcar salida
HORARIO_SALIDA_MINIMA = time(12, 0)          # 12:00 PM — mínimo para marcar salida temprana

# Horarios de recuperación
HORA_INICIO_RECUPERACION = time(14, 50)      # 2:50 PM
HORA_FIN_RECUPERACION = time(20, 0)          # 8:00 PM
HORA_CIERRE_REAL = time(20, 0)               # Hora límite real (sin gracia)
HORA_GRACIA_RECUPERACION = time(20, 20)      # 8:20 PM — gracia para marcar salida recup

# Horas semanales requeridas
HORAS_SEMANALES_REQUERIDAS = 30

# Advertencias de recuperación → ahora se manejan por reportes (tipo afk_salida)
# MAX_ADVERTENCIAS_CONSECUTIVAS eliminada — se cuenta por reportes de tipo afk_salida

# Baneos para retiro automático
MAX_BANEOS_RETIRO = 3  # 3 baneos = retirado automáticamente

# Estados de asistencia
ESTADOS_ASISTENCIA = ('temprano', 'tarde', 'sobreHora', 'falto', 'clases')

# Tipos de reporte
TIPOS_REPORTE = (
    'llamada_atencion',
    'justificacion',
    'baneo',
    'tardanza',
    'falta',
    'afk_salida',
    'retiro',
)

# Días de la semana
DIAS_SEMANA = {
    0: 'Lunes',
    1: 'Martes',
    2: 'Miércoles',
    3: 'Jueves',
    4: 'Viernes',
    5: 'Sábado',
    6: 'Domingo',
}

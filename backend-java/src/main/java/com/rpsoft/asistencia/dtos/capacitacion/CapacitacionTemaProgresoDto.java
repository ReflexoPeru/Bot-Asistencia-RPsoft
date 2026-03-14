package com.rpsoft.asistencia.dtos.capacitacion;

import lombok.Builder;
import lombok.Value;

import java.time.Duration;
import java.time.LocalDateTime;

@Value
@Builder
public class CapacitacionTemaProgresoDto {
    String curso;
    String tema;
    Integer orden;
    String estado;
    CapacitacionEvaluadorDto evaluador;
    LocalDateTime fechaInicio;
    LocalDateTime fechaFin;
    LocalDateTime ultimaReanudacion;
    Duration acumulado;
    Duration duracionFinal;
}

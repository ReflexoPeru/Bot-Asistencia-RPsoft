package com.rpsoft.asistencia.dtos.capacitacion;

import lombok.Builder;
import lombok.Value;

@Value
@Builder
public class CapacitacionEvaluadorDto {
    Integer id;
    String nombre;
    Boolean activo;
    String notas;
}

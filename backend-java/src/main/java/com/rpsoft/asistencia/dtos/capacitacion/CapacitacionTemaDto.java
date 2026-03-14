package com.rpsoft.asistencia.dtos.capacitacion;

import lombok.Builder;
import lombok.Value;

@Value
@Builder
public class CapacitacionTemaDto {
    Integer id;
    String nombre;
    Integer orden;
    String descripcion;
    Integer duracionRefDias;
}


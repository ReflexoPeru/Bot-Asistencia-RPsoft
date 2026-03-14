package com.rpsoft.asistencia.dtos.capacitacion;

import lombok.Builder;
import lombok.Singular;
import lombok.Value;

import java.util.List;

@Value
@Builder
public class CapacitacionCursoDto {
    Integer id;
    String nombre;
    String descripcion;
    Boolean activo;
    @Singular
    List<CapacitacionTemaDto> temas;
}


package com.rpsoft.asistencia.dtos.capacitacion;

import lombok.Builder;
import lombok.Singular;
import lombok.Value;

import java.util.List;

@Value
@Builder
public class CapacitacionPracticanteResponseDto {
    Integer practicanteId;
    String practicanteNombre;
    @Singular
    List<CapacitacionCursoProgresoDto> cursos;
}

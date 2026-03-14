package com.rpsoft.asistencia.dtos.capacitacion;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CapacitacionEvaluadorToggleRequest {
    @NotNull
    private Integer practicanteId;

    private String notas;
}

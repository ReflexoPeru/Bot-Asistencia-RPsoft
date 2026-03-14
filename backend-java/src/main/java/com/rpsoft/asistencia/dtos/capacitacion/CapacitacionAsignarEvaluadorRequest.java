package com.rpsoft.asistencia.dtos.capacitacion;

import jakarta.validation.constraints.NotNull;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
public class CapacitacionAsignarEvaluadorRequest extends CapacitacionBaseRequest {

    @NotNull
    private Integer evaluadorId;
}

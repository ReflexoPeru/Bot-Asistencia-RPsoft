package com.rpsoft.asistencia.dtos.capacitacion;

import jakarta.validation.constraints.NotNull;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
public class CapacitacionIniciarRequest extends CapacitacionBaseRequest {

    private Integer evaluadorId;

    @NotNull
    private Boolean crearSiNoExiste = Boolean.TRUE;
}

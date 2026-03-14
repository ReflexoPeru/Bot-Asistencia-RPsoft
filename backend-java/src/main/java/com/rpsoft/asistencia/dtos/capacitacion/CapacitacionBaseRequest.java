package com.rpsoft.asistencia.dtos.capacitacion;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CapacitacionBaseRequest {
    @NotNull
    private Integer practicanteId;

    @NotBlank
    private String cursoNombre;

    @NotBlank
    private String temaNombre;
}

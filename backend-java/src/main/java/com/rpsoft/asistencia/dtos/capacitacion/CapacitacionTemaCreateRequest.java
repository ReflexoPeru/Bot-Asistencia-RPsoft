package com.rpsoft.asistencia.dtos.capacitacion;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class CapacitacionTemaCreateRequest {

    @NotBlank
    @Size(max = 150)
    private String nombre;

    @NotNull
    @Min(1)
    private Integer orden;

    private String descripcion;

    @Min(1)
    private Integer duracionRefDias;
}


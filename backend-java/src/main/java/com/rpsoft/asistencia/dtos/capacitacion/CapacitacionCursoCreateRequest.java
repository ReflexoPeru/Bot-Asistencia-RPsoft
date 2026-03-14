package com.rpsoft.asistencia.dtos.capacitacion;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

@Data
public class CapacitacionCursoCreateRequest {

    @NotBlank
    @Size(max = 100)
    private String nombre;

    private String descripcion;

    private Boolean activo = Boolean.TRUE;

    @Valid
    private List<CapacitacionTemaCreateRequest> temas;
}


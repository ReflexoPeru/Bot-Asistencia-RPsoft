package com.rpsoft.asistencia.dtos.capacitacion;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.List;

@Data
public class CapacitacionAgregarTemasRequest {

    @Valid
    @NotEmpty
    private List<CapacitacionTemaCreateRequest> temas;
}


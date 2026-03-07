package com.rpsoft.asistencia.dtos;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO para crear un reporte.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class ReporteCreateDto {

    @NotNull(message = "El ID del practicante es obligatorio")
    private Long practicanteId;

    @NotBlank(message = "La descripción es obligatoria")
    private String descripcion;

    @NotBlank(message = "El tipo de reporte es obligatorio")
    private String tipo;

    private Long creadoPor;
}

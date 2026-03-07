package com.rpsoft.asistencia.dtos;

import lombok.Value;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * DTO inmutable de respuesta para reportes.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Value
public class ReporteResponseDto {
    Long id;
    Long practicanteId;
    String practicanteNombre;
    String descripcion;
    String tipo;
    LocalDate fecha;
    Boolean revisado;
    Long creadoPor;
    LocalDateTime createdAt;
}

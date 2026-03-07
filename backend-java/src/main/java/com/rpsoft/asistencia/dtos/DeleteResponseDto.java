package com.rpsoft.asistencia.dtos;

import lombok.Builder;
import lombok.Data;

/**
 * DTO genérico de respuesta para operaciones de eliminación (soft-delete).
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Data
@Builder
public class DeleteResponseDto {
    @Builder.Default
    private String message = "Eliminación exitosa";
    private Long id;
    private Boolean deleted;
}

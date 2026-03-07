package com.rpsoft.asistencia.exceptions;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Estructura estandarizada de respuesta de error.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Data
@Builder
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ErrorResponse {

    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "dd-MM-yyyy HH:mm:ss")
    private LocalDateTime timestamp;
    private int status;
    private String error;
    private String message;
    private String path;
    private List<ValidationError> validationErrors;

    @Data
    @Builder
    public static class ValidationError {
        private String field;
        private String message;
    }
}

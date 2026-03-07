package com.rpsoft.asistencia.exceptions;

/**
 * Excepción lanzada cuando un recurso no es encontrado.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
public class ResourceNotFoundException extends RuntimeException {

    public ResourceNotFoundException(String message) {
        super(message);
    }

    public ResourceNotFoundException(String resource, String field, Object value) {
        super(String.format("%s no encontrado con %s: '%s'", resource, field, value));
    }
}

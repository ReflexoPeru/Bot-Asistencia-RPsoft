package com.rpsoft.asistencia.exceptions;

/**
 * Excepción lanzada cuando un recurso ya existe (conflicto).
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
public class ResourceAlreadyExistsException extends RuntimeException {

    public ResourceAlreadyExistsException(String resource, String field, Object value) {
        super(String.format("%s ya existe con %s: '%s'", resource, field, value));
    }
}

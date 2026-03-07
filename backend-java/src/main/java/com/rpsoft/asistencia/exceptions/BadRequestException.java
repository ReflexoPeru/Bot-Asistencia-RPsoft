package com.rpsoft.asistencia.exceptions;

/**
 * Excepción lanzada para solicitudes inválidas.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
public class BadRequestException extends RuntimeException {

    public BadRequestException(String message) {
        super(message);
    }
}

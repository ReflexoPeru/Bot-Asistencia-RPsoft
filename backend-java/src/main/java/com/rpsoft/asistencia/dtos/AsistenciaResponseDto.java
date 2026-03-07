package com.rpsoft.asistencia.dtos;

import lombok.Value;

import java.time.LocalDate;
import java.time.LocalTime;

/**
 * DTO inmutable de respuesta para registros de asistencia.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Value
public class AsistenciaResponseDto {
    Long id;
    Long practicanteId;
    String nombreCompleto;
    String estado;
    LocalDate fecha;
    LocalTime horaEntrada;
    LocalTime horaSalida;
    Boolean salidaAuto;
    String dispositivo;
}

package com.rpsoft.asistencia.dtos;

import lombok.Value;

import java.time.LocalDate;

/**
 * DTO inmutable de respuesta para practicantes.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Value
public class PracticanteResponseDto {
    Integer id;
    Long idDiscord;
    String nombreCompleto;
    String correo;
    Boolean claseLunes;
    Boolean claseMartes;
    Boolean claseMiercoles;
    Boolean claseJueves;
    Boolean claseViernes;
    Boolean claseSabado;
    String convenio;
    Short semestre;
    String rol;
    LocalDate fechaInscripcion;
    Boolean matriculado;
    String dni;
    String numero;
    String sede;
    String carrera;
    String usuarioGithub;
    String usuarioDiscord;
    String estado;
    LocalDate fechaRetiro;
    String motivoRetiro;
    Integer baneos;
}

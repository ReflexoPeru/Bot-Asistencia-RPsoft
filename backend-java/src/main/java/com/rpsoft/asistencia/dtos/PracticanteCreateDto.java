package com.rpsoft.asistencia.dtos;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.validator.constraints.Length;

/**
 * DTO para crear o actualizar un practicante.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class PracticanteCreateDto {

    @NotNull(message = "El ID de Discord es obligatorio")
    private Long idDiscord;

    @NotBlank(message = "El nombre completo es obligatorio")
    @Length(min = 3, max = 255, message = "El nombre debe tener entre 3 y 255 caracteres")
    private String nombreCompleto;

    private String correo;
    private Boolean claseLunes;
    private Boolean claseMartes;
    private Boolean claseMiercoles;
    private Boolean claseJueves;
    private Boolean claseViernes;
    private Boolean claseSabado;
    private String convenio;
    private Short semestre;
    private String rol;
    private Boolean matriculado;
    private String dni;
    private String numero;
    private String sede;
    private String carrera;
    private String usuarioGithub;
    private String usuarioDiscord;
}

package com.rpsoft.asistencia.entities;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Duration;
import java.time.LocalDate;

/**
 * Entidad que representa un practicante en el sistema.
 * <p>
 * Mapea la tabla {@code practicante} existente en PostgreSQL.
 * Incluye datos personales, académicos, días de clase y estado.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see ReporteEntity
 * @see AsistenciaEntity
 */
@Getter
@Setter
@Entity
@Table(name = "practicante")
public class PracticanteEntity extends AuditableEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Integer id;

    @Column(name = "id_discord", nullable = false, unique = true)
    private Long idDiscord;

    @Column(name = "nombre_completo", nullable = false, length = 255)
    private String nombreCompleto;

    @Column(name = "correo", length = 255)
    private String correo;

    @Column(name = "correo_institucional", length = 255)
    private String correoInstitucional;

    // --- Días con clases ---
    @Column(name = "clase_lunes")
    private Boolean claseLunes = false;

    @Column(name = "clase_martes")
    private Boolean claseMartes = false;

    @Column(name = "clase_miercoles")
    private Boolean claseMiercoles = false;

    @Column(name = "clase_jueves")
    private Boolean claseJueves = false;

    @Column(name = "clase_viernes")
    private Boolean claseViernes = false;

    @Column(name = "clase_sabado")
    private Boolean claseSabado = false;

    // --- Datos académicos/laborales ---
    @Column(name = "convenio", length = 20)
    private String convenio = "no";

    @Column(name = "semestre")
    private Short semestre;

    @Column(name = "rol", length = 50)
    private String rol;

    @Column(name = "fecha_inscripcion")
    private LocalDate fechaInscripcion;

    @Column(name = "matriculado")
    private Boolean matriculado = false;

    @Column(name = "dni", length = 15)
    private String dni;

    @Column(name = "numero", length = 20)
    private String numero;

    @Column(name = "sede", length = 100)
    private String sede;

    @Column(name = "carrera", length = 150)
    private String carrera;

    @Column(name = "usuario_github", length = 100)
    private String usuarioGithub;

    @Column(name = "usuario_discord", length = 100)
    private String usuarioDiscord;

    // --- Control ---
    @Column(name = "estado", length = 20)
    private String estado = "activo";

    @Column(name = "fecha_retiro")
    private LocalDate fechaRetiro;

    @Column(name = "motivo_retiro", length = 255)
    private String motivoRetiro;

    @Column(name = "baneos")
    private Integer baneos = 0;

    @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.INTERVAL_SECOND)
    @Column(name = "horas_base", columnDefinition = "interval")
    private Duration horasBase;
}

package com.rpsoft.asistencia.entities;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;
import java.time.LocalTime;

/**
 * Entidad que representa un registro de asistencia diario.
 * <p>
 * Mapea la tabla {@code asistencia}. Estados posibles: temprano, tarde,
 * sobreHora, falto, clases.
 * Constraint UNIQUE en (practicante_id, fecha).
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see PracticanteEntity
 */
@Getter
@Setter
@Entity
@Table(name = "asistencia", uniqueConstraints = {
        @UniqueConstraint(columnNames = { "practicante_id", "fecha" })
})
public class AsistenciaEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "practicante_id", nullable = false)
    private PracticanteEntity practicante;

    @Column(name = "estado", nullable = false, length = 20)
    private String estado;

    @Column(name = "fecha", nullable = false)
    private LocalDate fecha;

    @Column(name = "hora_entrada")
    private LocalTime horaEntrada;

    @Column(name = "hora_salida")
    private LocalTime horaSalida;

    @Column(name = "salida_auto")
    private Boolean salidaAuto = false;

    @Column(name = "dispositivo", length = 10)
    private String dispositivo;
}

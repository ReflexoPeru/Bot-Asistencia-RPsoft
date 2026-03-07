package com.rpsoft.asistencia.entities;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;
import java.time.LocalTime;

/**
 * Entidad que representa un registro de recuperación.
 * <p>
 * Mapea la tabla {@code recuperacion}. Estados: abierto, valido, invalidado.
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
@Table(name = "recuperacion", uniqueConstraints = {
        @UniqueConstraint(columnNames = { "practicante_id", "fecha" })
})
public class RecuperacionEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "practicante_id", nullable = false)
    private PracticanteEntity practicante;

    @Column(name = "fecha", nullable = false)
    private LocalDate fecha;

    @Column(name = "hora_entrada", nullable = false)
    private LocalTime horaEntrada;

    @Column(name = "hora_salida")
    private LocalTime horaSalida;

    @Column(name = "estado", length = 15)
    private String estado = "abierto";

    @Column(name = "salida_auto")
    private Boolean salidaAuto = false;
}

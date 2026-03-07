package com.rpsoft.asistencia.entities;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * Entidad que representa un reporte en el sistema.
 * <p>
 * Mapea la tabla {@code reporte}. Tipos: llamada_atencion, justificacion,
 * baneo, tardanza, falta, afk_salida, retiro.
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
@Table(name = "reporte")
public class ReporteEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "practicante_id", nullable = false)
    private PracticanteEntity practicante;

    @Column(name = "descripcion", nullable = false, columnDefinition = "TEXT")
    private String descripcion;

    @Column(name = "tipo", nullable = false, length = 30)
    private String tipo;

    @Column(name = "fecha", nullable = false)
    private LocalDate fecha;

    @Column(name = "revisado")
    private Boolean revisado = false;

    @Column(name = "creado_por")
    private Long creadoPor;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        if (this.fecha == null) {
            this.fecha = LocalDate.now();
        }
        if (this.createdAt == null) {
            this.createdAt = LocalDateTime.now();
        }
    }
}

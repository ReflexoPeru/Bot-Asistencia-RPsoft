package com.rpsoft.asistencia.entities.capacitacion;

import com.rpsoft.asistencia.entities.AuditableEntity;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Duration;

@Getter
@Setter
@Entity
@Table(name = "capacitacion_tema",
        uniqueConstraints = {
                @UniqueConstraint(columnNames = {"curso_id", "nombre"}),
                @UniqueConstraint(columnNames = {"curso_id", "orden"})
        })
public class CapacitacionTemaEntity extends AuditableEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "curso_id", nullable = false)
    private CapacitacionCursoEntity curso;

    @Column(nullable = false, length = 150)
    private String nombre;

    @Column(nullable = false)
    private Integer orden;

    @Column
    private String descripcion;

    @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.INTERVAL_SECOND)
    @Column(name = "duracion_ref", columnDefinition = "interval")
    private Duration duracionRef;
}

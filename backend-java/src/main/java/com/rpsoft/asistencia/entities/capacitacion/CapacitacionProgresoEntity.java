package com.rpsoft.asistencia.entities.capacitacion;

import com.rpsoft.asistencia.entities.AuditableEntity;
import com.rpsoft.asistencia.entities.PracticanteEntity;
import com.rpsoft.asistencia.entities.TrainingEstado;
import com.rpsoft.asistencia.entities.converters.TrainingEstadoConverter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Duration;
import java.time.LocalDateTime;

@Getter
@Setter
@Entity
@Table(name = "capacitacion_progreso",
        uniqueConstraints = {@UniqueConstraint(columnNames = {"practicante_id", "tema_id"})})
public class CapacitacionProgresoEntity extends AuditableEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "practicante_id", nullable = false)
    private PracticanteEntity practicante;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "curso_id", nullable = false)
    private CapacitacionCursoEntity curso;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "tema_id", nullable = false)
    private CapacitacionTemaEntity tema;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "evaluador_id")
    private CapacitacionEvaluadorEntity evaluador;

    @Convert(converter = TrainingEstadoConverter.class)
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    @Column(nullable = false, columnDefinition = "training_estado")
    private TrainingEstado estado = TrainingEstado.PLANNED;

    @Column(name = "fecha_inicio")
    private LocalDateTime fechaInicio;

    @Column(name = "ultima_reanudacion")
    private LocalDateTime ultimaReanudacion;

    @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.INTERVAL_SECOND)
    @Column(name = "acumulado", nullable = false, columnDefinition = "interval")
    private Duration acumulado = Duration.ZERO;

    @Column(name = "fecha_fin")
    private LocalDateTime fechaFin;

    @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.INTERVAL_SECOND)
    @Column(name = "duracion_final", columnDefinition = "interval")
    private Duration duracionFinal;
}

package com.rpsoft.asistencia.entities.capacitacion;

import com.rpsoft.asistencia.entities.AuditableEntity;
import com.rpsoft.asistencia.entities.PracticanteEntity;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "capacitacion_evaluador")
public class CapacitacionEvaluadorEntity extends AuditableEntity {

    @Id
    @Column(name = "practicante_id")
    private Integer practicanteId;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "practicante_id", insertable = false, updatable = false)
    private PracticanteEntity practicante;

    @Column(nullable = false)
    private Boolean activo = true;

    @Column
    private String notas;
}

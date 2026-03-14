package com.rpsoft.asistencia.entities.capacitacion;

import com.rpsoft.asistencia.entities.AuditableEntity;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.util.LinkedHashSet;
import java.util.Set;

@Getter
@Setter
@Entity
@Table(name = "capacitacion_curso")
public class CapacitacionCursoEntity extends AuditableEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(nullable = false, length = 100, unique = true)
    private String nombre;

    @Column
    private String descripcion;

    @Column(nullable = false)
    private Boolean activo = true;

    @OneToMany(mappedBy = "curso", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private Set<CapacitacionTemaEntity> temas = new LinkedHashSet<>();
}

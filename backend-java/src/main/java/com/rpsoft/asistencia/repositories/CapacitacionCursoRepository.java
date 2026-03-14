package com.rpsoft.asistencia.repositories;

import com.rpsoft.asistencia.entities.capacitacion.CapacitacionCursoEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface CapacitacionCursoRepository extends JpaRepository<CapacitacionCursoEntity, Integer> {
    Optional<CapacitacionCursoEntity> findByNombreIgnoreCase(String nombre);
}

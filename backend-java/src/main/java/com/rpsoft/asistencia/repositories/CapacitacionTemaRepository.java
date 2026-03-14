package com.rpsoft.asistencia.repositories;

import com.rpsoft.asistencia.entities.capacitacion.CapacitacionCursoEntity;
import com.rpsoft.asistencia.entities.capacitacion.CapacitacionTemaEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface CapacitacionTemaRepository extends JpaRepository<CapacitacionTemaEntity, Integer> {
    Optional<CapacitacionTemaEntity> findByCursoAndNombreIgnoreCase(CapacitacionCursoEntity curso, String nombre);
    List<CapacitacionTemaEntity> findByCursoOrderByOrdenAsc(CapacitacionCursoEntity curso);
}

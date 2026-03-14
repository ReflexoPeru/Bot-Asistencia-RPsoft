package com.rpsoft.asistencia.repositories;

import com.rpsoft.asistencia.entities.capacitacion.CapacitacionCursoEntity;
import com.rpsoft.asistencia.entities.capacitacion.CapacitacionProgresoEntity;
import com.rpsoft.asistencia.entities.capacitacion.CapacitacionTemaEntity;
import com.rpsoft.asistencia.entities.PracticanteEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface CapacitacionProgresoRepository extends JpaRepository<CapacitacionProgresoEntity, Integer> {
    Optional<CapacitacionProgresoEntity> findByPracticanteAndTema(PracticanteEntity practicante, CapacitacionTemaEntity tema);

    List<CapacitacionProgresoEntity> findByPracticanteAndCurso(PracticanteEntity practicante, CapacitacionCursoEntity curso);
}

package com.rpsoft.asistencia.repositories;

import com.rpsoft.asistencia.entities.ReporteEntity;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

/**
 * Repositorio para operaciones CRUD sobre reportes.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Repository
public interface ReporteRepository extends JpaRepository<ReporteEntity, Integer> {

    Page<ReporteEntity> findByPracticanteId(Integer practicanteId, Pageable pageable);

    List<ReporteEntity> findByFecha(LocalDate fecha);

    List<ReporteEntity> findByTipoAndFecha(String tipo, LocalDate fecha);

    long countByTipoAndFecha(String tipo, LocalDate fecha);
}

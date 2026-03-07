package com.rpsoft.asistencia.repositories;

import com.rpsoft.asistencia.entities.RecuperacionEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

/**
 * Repositorio para operaciones sobre registros de recuperación.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Repository
public interface RecuperacionRepository extends JpaRepository<RecuperacionEntity, Integer> {

    List<RecuperacionEntity> findByFechaAndEstado(LocalDate fecha, String estado);
}

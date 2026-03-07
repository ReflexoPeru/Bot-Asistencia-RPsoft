package com.rpsoft.asistencia.repositories;

import com.rpsoft.asistencia.entities.PracticanteEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Repositorio para operaciones CRUD sobre practicantes.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Repository
public interface PracticanteRepository extends JpaRepository<PracticanteEntity, Long> {

    Optional<PracticanteEntity> findByIdDiscord(Long idDiscord);

    List<PracticanteEntity> findByEstado(String estado);

    long countByEstado(String estado);
}

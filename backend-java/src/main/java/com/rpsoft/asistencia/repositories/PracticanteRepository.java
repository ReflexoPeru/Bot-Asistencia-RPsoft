package com.rpsoft.asistencia.repositories;

import com.rpsoft.asistencia.entities.PracticanteEntity;
import org.springframework.cache.annotation.Cacheable;
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
public interface PracticanteRepository extends JpaRepository<PracticanteEntity, Integer> {

    Optional<PracticanteEntity> findByIdDiscord(Long idDiscord);

    @Cacheable("practicantesActivosList")
    List<PracticanteEntity> findByEstado(String estado);

    @Cacheable("practicantesActivosCount")
    long countByEstado(String estado);
}

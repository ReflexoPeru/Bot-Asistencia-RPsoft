package com.rpsoft.asistencia.repositories;

import com.rpsoft.asistencia.entities.RecuperacionEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
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

    @Query(value = "SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (hora_salida - hora_entrada))), 0) FROM recuperacion WHERE practicante_id = :practicanteId AND estado = 'valido'", nativeQuery = true)
    long sumDuracionAprobadaSegundos(@Param("practicanteId") Integer practicanteId);

    @Query(value = "SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (hora_salida - hora_entrada))), 0) FROM recuperacion WHERE practicante_id = :practicanteId AND estado = 'valido' AND fecha >= :startDate AND fecha <= :endDate", nativeQuery = true)
    long sumDuracionRangoSegundos(@Param("practicanteId") Integer practicanteId,
            @Param("startDate") LocalDate startDate, @Param("endDate") LocalDate endDate);

    @Query("SELECT r FROM RecuperacionEntity r WHERE r.practicante.id = :practicanteId ORDER BY r.fecha DESC")
    List<RecuperacionEntity> findUltimosRegistros(@Param("practicanteId") Integer practicanteId,
            org.springframework.data.domain.Pageable pageable);
}

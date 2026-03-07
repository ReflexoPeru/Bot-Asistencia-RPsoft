package com.rpsoft.asistencia.repositories;

import com.rpsoft.asistencia.entities.AsistenciaEntity;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

/**
 * Repositorio para operaciones sobre registros de asistencia.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Repository
public interface AsistenciaRepository extends JpaRepository<AsistenciaEntity, Long> {

    List<AsistenciaEntity> findByFechaOrderByHoraEntradaAsc(LocalDate fecha);

    Optional<AsistenciaEntity> findByPracticanteIdAndFecha(Long practicanteId, LocalDate fecha);

    long countByFechaAndEstado(LocalDate fecha, String estado);

    @Query("SELECT a FROM AsistenciaEntity a WHERE a.fecha = :fecha AND a.horaEntrada IS NOT NULL AND a.horaSalida IS NULL")
    List<AsistenciaEntity> findSinSalidaByFecha(@Param("fecha") LocalDate fecha);

    @Query("SELECT DISTINCT a.fecha FROM AsistenciaEntity a WHERE YEAR(a.fecha) = :year AND MONTH(a.fecha) = :month ORDER BY a.fecha")
    List<LocalDate> findFechasConRegistros(@Param("year") int year, @Param("month") int month);

    @Query("SELECT COUNT(a) FROM AsistenciaEntity a WHERE a.fecha = :fecha AND a.estado <> 'falto'")
    long countRegistradosHoy(@Param("fecha") LocalDate fecha);

    @Query("SELECT COUNT(a) FROM AsistenciaEntity a WHERE a.estado IN ('tarde', 'sobreHora')")
    @Cacheable("tardanzasAcumuladas")
    long countTardanzasAcumuladas();
}

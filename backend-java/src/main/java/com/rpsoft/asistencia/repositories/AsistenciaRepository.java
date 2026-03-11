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
public interface AsistenciaRepository extends JpaRepository<AsistenciaEntity, Integer> {

        List<AsistenciaEntity> findByFechaOrderByHoraEntradaAsc(LocalDate fecha);

        Optional<AsistenciaEntity> findByPracticanteIdAndFecha(Integer practicanteId, LocalDate fecha);

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

        @Query(value = "SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (hora_salida - hora_entrada))), 0) FROM asistencia WHERE practicante_id = :practicanteId AND estado IN ('temprano', 'tarde', 'sobreHora', 'clases')", nativeQuery = true)
        long sumDuracionAprobadaSegundos(@Param("practicanteId") Integer practicanteId);

        @Query(value = "SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (hora_salida - hora_entrada))), 0) FROM asistencia WHERE practicante_id = :practicanteId AND estado IN ('temprano', 'tarde', 'sobreHora', 'clases') AND fecha >= :startDate AND fecha <= :endDate", nativeQuery = true)
        long sumDuracionRangoSegundos(@Param("practicanteId") Integer practicanteId,
                        @Param("startDate") LocalDate startDate, @Param("endDate") LocalDate endDate);

        long countByPracticanteIdAndEstadoIn(Integer practicanteId, List<String> estados);

        @Query("SELECT a FROM AsistenciaEntity a WHERE a.practicante.id = :practicanteId ORDER BY a.fecha DESC")
        List<AsistenciaEntity> findUltimosRegistros(@Param("practicanteId") Integer practicanteId,
                        org.springframework.data.domain.Pageable pageable);
}

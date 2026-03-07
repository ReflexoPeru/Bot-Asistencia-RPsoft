package com.rpsoft.asistencia.services;

import com.rpsoft.asistencia.dtos.MetricaDiariaDto;
import com.rpsoft.asistencia.repositories.AsistenciaRepository;
import com.rpsoft.asistencia.repositories.PracticanteRepository;
import com.rpsoft.asistencia.repositories.ReporteRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.format.TextStyle;
import java.util.Locale;

/**
 * Servicio para calcular las 14 métricas del dashboard diario.
 * <p>
 * Réplica de la lógica del comando {@code /admin registros} del bot Python.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see AsistenciaRepository
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class MetricaService {

    private final PracticanteRepository practicanteRepository;
    private final AsistenciaRepository asistenciaRepository;
    private final ReporteRepository reporteRepository;

    /**
     * Calcula las 14 métricas del dashboard para la fecha indicada.
     *
     * @param fecha fecha a consultar
     * @return DTO con todas las métricas
     */
    public MetricaDiariaDto getMetricasDelDia(LocalDate fecha) {
        DayOfWeek dia = fecha.getDayOfWeek();
        String diaNombre = dia.getDisplayName(TextStyle.FULL, Locale.forLanguageTag("es"));

        // 1. Total inicial
        long totalInicial = practicanteRepository.count();

        // 2. Retirados
        long totalRetirados = practicanteRepository.countByEstado("retirado");

        // 3. Activos
        long totalActivos = practicanteRepository.countByEstado("activo");

        // 4. Ausentes por clases (practicantes activos que tienen clase hoy)
        long ausentesClases = countConClaseHoy(dia);

        // 5. Justificaciones hoy
        long justificaciones = reporteRepository.countByTipoAndFecha("justificacion", fecha);

        // 6. Deben asistir
        long debenAsistir = Math.max(0, totalActivos - ausentesClases - justificaciones);

        // 7. Presentes (temprano)
        long presentes = asistenciaRepository.countByFechaAndEstado(fecha, "temprano");

        // 8. Faltan llegar
        long registrados = asistenciaRepository.countRegistradosHoy(fecha);
        long faltanLlegar = Math.max(0, debenAsistir - registrados);

        // 9. Tardanzas
        long tardanzas = asistenciaRepository.countByFechaAndEstado(fecha, "tarde");

        // 10. Sobre hora
        long sobreHora = asistenciaRepository.countByFechaAndEstado(fecha, "sobreHora");

        // 11. Faltas (activos sin clase, sin asistencia, sin justificación)
        long faltas = Math.max(0, debenAsistir - registrados);

        // 12. Tardanzas acumuladas
        long tardanzasAcumuladas = asistenciaRepository.countTardanzasAcumuladas();

        // 13. Retirados hoy
        long retiradosHoy = practicanteRepository.findByEstado("retirado").stream()
                .filter(p -> fecha.equals(p.getFechaRetiro()))
                .count();

        return MetricaDiariaDto.builder()
                .fecha(fecha.toString())
                .diaSemana(diaNombre)
                .totalInicial(totalInicial)
                .totalRetirados(totalRetirados)
                .totalActivos(totalActivos)
                .ausentesClases(ausentesClases)
                .justificaciones(justificaciones)
                .debenAsistir(debenAsistir)
                .presentes(presentes)
                .faltanLlegar(faltanLlegar)
                .tardanzas(tardanzas)
                .sobreHora(sobreHora)
                .faltas(faltas)
                .tardanzasAcumuladas(tardanzasAcumuladas)
                .retiradosHoy(retiradosHoy)
                .build();
    }

    /**
     * Cuenta practicantes activos que tienen clase en el día de la semana dado.
     * Usa la columna correspondiente (clase_lunes, clase_martes, etc.)
     */
    private long countConClaseHoy(DayOfWeek dia) {
        return practicanteRepository.findByEstado("activo").stream()
                .filter(p -> switch (dia) {
                    case MONDAY -> Boolean.TRUE.equals(p.getClaseLunes());
                    case TUESDAY -> Boolean.TRUE.equals(p.getClaseMartes());
                    case WEDNESDAY -> Boolean.TRUE.equals(p.getClaseMiercoles());
                    case THURSDAY -> Boolean.TRUE.equals(p.getClaseJueves());
                    case FRIDAY -> Boolean.TRUE.equals(p.getClaseViernes());
                    case SATURDAY -> Boolean.TRUE.equals(p.getClaseSabado());
                    case SUNDAY -> false;
                })
                .count();
    }
}

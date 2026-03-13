package com.rpsoft.asistencia.services;

import com.rpsoft.asistencia.dtos.AsistenciaResponseDto;
import com.rpsoft.asistencia.entities.AsistenciaEntity;
import com.rpsoft.asistencia.exceptions.ResourceNotFoundException;
import com.rpsoft.asistencia.mappers.AsistenciaMapper;
import com.rpsoft.asistencia.repositories.AsistenciaRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.Set;

import com.rpsoft.asistencia.repositories.PracticanteRepository;
import com.rpsoft.asistencia.repositories.RecuperacionRepository;
import com.rpsoft.asistencia.repositories.ReporteRepository;
import com.rpsoft.asistencia.dtos.ResumenHistorialDto;
import org.springframework.data.domain.PageRequest;
import java.time.temporal.ChronoField;
import java.time.DayOfWeek;

/**
 * Servicio para consultar registros de asistencia.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see AsistenciaRepository
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AsistenciaService {

    private final AsistenciaRepository asistenciaRepository;
    private final RecuperacionRepository recuperacionRepository;
    private final PracticanteRepository practicanteRepository;
    private final ReporteRepository reporteRepository;
    private final AsistenciaMapper asistenciaMapper;

    /**
     * Obtiene todos los registros de asistencia para una fecha dada.
     *
     * @param fecha fecha a consultar
     * @return lista de registros ordenados por hora de entrada
     */
    public List<AsistenciaResponseDto> getByFecha(LocalDate fecha) {
        return asistenciaRepository.findByFechaOrderByHoraEntradaAsc(fecha).stream()
                .map(asistenciaMapper::toResponseDto)
                .toList();
    }

    public AsistenciaEntity getById(Integer id) {
        return asistenciaRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Asistencia", "ID", id));
    }

    @CacheEvict(value = "tardanzasAcumuladas", allEntries = true)
    @Transactional
    public AsistenciaEntity create(AsistenciaEntity entity) {
        return asistenciaRepository.save(entity);
    }

    @Transactional
    public AsistenciaEntity update(Integer id, AsistenciaEntity data) {
        AsistenciaEntity existing = getById(id);
        existing.setHoraEntrada(data.getHoraEntrada());
        existing.setHoraSalida(data.getHoraSalida());
        existing.setEstado(data.getEstado());
        existing.setSalidaAuto(data.getSalidaAuto());
        return asistenciaRepository.save(existing);
    }

    @CacheEvict(value = "tardanzasAcumuladas", allEntries = true)
    @Transactional
    public void delete(Integer id) {
        AsistenciaEntity existing = getById(id);
        asistenciaRepository.delete(existing);
    }

    /**
     * Obtiene las fechas de un mes que tienen registros de asistencia.
     *
     * @param year  año
     * @param month mes
     * @return lista de fechas con registros
     */
    public List<LocalDate> getFechasConRegistros(int year, int month) {
        return asistenciaRepository.findFechasConRegistros(year, month);
    }

    public ResumenHistorialDto getResumenHistorial(Long idDiscord) {
        var practicante = practicanteRepository.findByIdDiscord(idDiscord)
                .orElseThrow(() -> new ResourceNotFoundException("Practicante", "idDiscord", idDiscord));

        Integer pId = practicante.getId();

        LocalDate hoy = LocalDate.now();
        LocalDate inicioSemana = hoy.with(ChronoField.DAY_OF_WEEK, DayOfWeek.MONDAY.getValue());
        LocalDate finSemana = hoy.with(ChronoField.DAY_OF_WEEK, DayOfWeek.SUNDAY.getValue());

        long horasTotales = asistenciaRepository.sumDuracionAprobadaSegundos(pId);
        long horasSemanales = asistenciaRepository.sumDuracionRangoSegundos(pId, inicioSemana, finSemana);
        long horasRecuperacion = recuperacionRepository.sumDuracionAprobadaSegundos(pId);
        long horasRecuperacionSemanales = recuperacionRepository.sumDuracionRangoSegundos(pId, inicioSemana, finSemana);

        long horasBaseSegundos = 576 * 3600L;

        long incidenciasTardanza = reporteRepository.countByPracticanteIdAndTipo(pId, "tardanza");
        long incidenciasSobreHora = reporteRepository.countByPracticanteIdAndTipo(pId, "sobreHora");
        long incidenciasBaneo = reporteRepository.countByPracticanteIdAndTipo(pId, "baneo");
        long incidenciasFalta = reporteRepository.countByPracticanteIdAndTipo(pId, "falta");
        long incidenciasInasistencia = reporteRepository.countByPracticanteIdAndTipo(pId, "inasistencia");

        List<ResumenHistorialDto.ReporteResumenDto> reportes = reporteRepository
                .findByPracticanteId(pId, PageRequest.of(0, 20))
                .getContent().stream()
                .map(r -> ResumenHistorialDto.ReporteResumenDto.builder()
                        .tipo(r.getTipo())
                        .descripcion(r.getDescripcion())
                        .fecha(r.getFecha())
                        .build())
                .toList();

        List<AsistenciaEntity> uA = asistenciaRepository.findUltimosRegistros(pId, PageRequest.of(0, 10));
        List<com.rpsoft.asistencia.entities.RecuperacionEntity> uR = recuperacionRepository.findUltimosRegistros(pId,
                PageRequest.of(0, 5));

        List<ResumenHistorialDto.RegistroDiarioDto> registros = new ArrayList<>();
        Set<LocalDate> fechasConAsistencia = new HashSet<>();

        for (AsistenciaEntity a : uA) {
            long duracion = 0;
            if (a.getHoraSalida() != null && a.getHoraEntrada() != null) {
                duracion = java.time.Duration.between(a.getHoraEntrada(), a.getHoraSalida()).getSeconds();
            }
            fechasConAsistencia.add(a.getFecha());
            registros.add(ResumenHistorialDto.RegistroDiarioDto.builder()
                    .fecha(a.getFecha())
                    .diaSemana(obtenerDiaSemana(a.getFecha()))
                    .horaEntrada(a.getHoraEntrada() != null ? a.getHoraEntrada().toString() : "--:--")
                    .horaSalida(a.getHoraSalida() != null ? a.getHoraSalida().toString() : "--:--")
                    .estado(a.getEstado())
                    .esRecuperacion(false)
                    .soloRecuperacion(false)
                    .duracionSegundos(duracion)
                    .build());
        }

        for (com.rpsoft.asistencia.entities.RecuperacionEntity r : uR) {
            long duracion = 0;
            if (r.getHoraSalida() != null && r.getHoraEntrada() != null) {
                duracion = java.time.Duration.between(r.getHoraEntrada(), r.getHoraSalida()).getSeconds();
            }
            boolean soloRecuperacion = !fechasConAsistencia.contains(r.getFecha());
            registros.add(ResumenHistorialDto.RegistroDiarioDto.builder()
                    .fecha(r.getFecha())
                    .diaSemana(obtenerDiaSemana(r.getFecha()))
                    .horaEntrada(r.getHoraEntrada() != null ? r.getHoraEntrada().toString() : "--:--")
                    .horaSalida(r.getHoraSalida() != null ? r.getHoraSalida().toString() : "--:--")
                    .estado(r.getEstado())
                    .esRecuperacion(true)
                    .soloRecuperacion(soloRecuperacion)
                    .duracionSegundos(duracion)
                    .build());
        }

        registros.sort(Comparator.comparing(ResumenHistorialDto.RegistroDiarioDto::getFecha).reversed()
                .thenComparing(r -> r.isEsRecuperacion() ? 1 : 0));
        if (registros.size() > 7) {
            registros = registros.subList(0, 7);
        }

        return ResumenHistorialDto.builder()
                .nombreCompleto(practicante.getNombreCompleto())
                .idDiscord(practicante.getIdDiscord())
                .horasSemanalesSegundos(horasSemanales)
                .horasTotalesSegundos(horasTotales)
                .horasRecuperacionSegundos(horasRecuperacion)
                .horasRecuperacionSemanalesSegundos(horasRecuperacionSemanales)
                .horasBaseSegundos(horasBaseSegundos)
                .incidenciasTardanza(incidenciasTardanza)
                .incidenciasSobreHora(incidenciasSobreHora)
                .incidenciasBaneo(incidenciasBaneo)
                .incidenciasFalta(incidenciasFalta)
                .incidenciasInasistencia(incidenciasInasistencia)
                .reportes(reportes)
                .ultimosRegistros(registros)
                .build();
    }

    private String obtenerDiaSemana(LocalDate fecha) {
        String[] dias = { "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo" };
        return dias[fecha.getDayOfWeek().getValue() - 1];
    }
}

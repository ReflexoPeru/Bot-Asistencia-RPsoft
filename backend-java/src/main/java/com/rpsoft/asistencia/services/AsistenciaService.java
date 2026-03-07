package com.rpsoft.asistencia.services;

import com.rpsoft.asistencia.dtos.AsistenciaResponseDto;
import com.rpsoft.asistencia.mappers.AsistenciaMapper;
import com.rpsoft.asistencia.repositories.AsistenciaRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;

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
}

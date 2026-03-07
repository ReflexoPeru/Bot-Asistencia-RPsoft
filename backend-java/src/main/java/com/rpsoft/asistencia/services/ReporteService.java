package com.rpsoft.asistencia.services;

import com.rpsoft.asistencia.dtos.ReporteCreateDto;
import com.rpsoft.asistencia.dtos.ReporteResponseDto;
import com.rpsoft.asistencia.entities.PracticanteEntity;
import com.rpsoft.asistencia.entities.ReporteEntity;
import com.rpsoft.asistencia.exceptions.ResourceNotFoundException;
import com.rpsoft.asistencia.mappers.ReporteMapper;
import com.rpsoft.asistencia.repositories.PracticanteRepository;
import com.rpsoft.asistencia.repositories.ReporteRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Servicio para la gestión de reportes.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see ReporteRepository
 */
@Service
@RequiredArgsConstructor
@Transactional
public class ReporteService {

    public static final String ENTITY_NAME = "Reporte";
    private static final String PRACTICANTE = "Practicante";

    private final ReporteRepository reporteRepository;
    private final PracticanteRepository practicanteRepository;
    private final ReporteMapper reporteMapper;

    /**
     * Obtiene reportes paginados, opcionalmente filtrados por practicante.
     *
     * @param practicanteId filtro opcional por practicante
     * @param pageable      parámetros de paginación
     * @return página de reportes
     */
    @Transactional(readOnly = true)
    public Page<ReporteResponseDto> getAll(Integer practicanteId, Pageable pageable) {
        if (practicanteId != null) {
            return reporteRepository.findByPracticanteId(practicanteId, pageable)
                    .map(reporteMapper::toResponseDto);
        }
        return reporteRepository.findAll(pageable)
                .map(reporteMapper::toResponseDto);
    }

    /**
     * Crea un nuevo reporte.
     *
     * @param dto datos del reporte
     * @return reporte creado
     * @throws ResourceNotFoundException si el practicante no existe
     */
    public ReporteResponseDto create(ReporteCreateDto dto) {
        PracticanteEntity practicante = practicanteRepository.findById(dto.getPracticanteId())
                .orElseThrow(() -> new ResourceNotFoundException(PRACTICANTE, "ID", dto.getPracticanteId()));

        ReporteEntity entity = reporteMapper.toEntity(dto);
        entity.setPracticante(practicante);
        ReporteEntity saved = reporteRepository.save(entity);
        return reporteMapper.toResponseDto(saved);
    }

    /**
     * Marca un reporte como revisado.
     *
     * @param id identificador del reporte
     * @return reporte actualizado
     * @throws ResourceNotFoundException si no existe
     */
    public ReporteResponseDto marcarRevisado(Integer id) {
        ReporteEntity entity = reporteRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException(ENTITY_NAME, "ID", id));
        entity.setRevisado(true);
        return reporteMapper.toResponseDto(reporteRepository.save(entity));
    }
}

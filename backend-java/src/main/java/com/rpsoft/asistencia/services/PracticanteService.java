package com.rpsoft.asistencia.services;

import com.rpsoft.asistencia.dtos.DeleteResponseDto;
import com.rpsoft.asistencia.dtos.PracticanteCreateDto;
import com.rpsoft.asistencia.dtos.PracticanteResponseDto;
import com.rpsoft.asistencia.entities.PracticanteEntity;
import com.rpsoft.asistencia.exceptions.ResourceAlreadyExistsException;
import com.rpsoft.asistencia.exceptions.ResourceNotFoundException;
import com.rpsoft.asistencia.mappers.PracticanteMapper;
import com.rpsoft.asistencia.repositories.PracticanteRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;

/**
 * Servicio para la gestión de practicantes.
 * <p>
 * Maneja CRUD completo con soft-delete (estado→retirado).
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see PracticanteRepository
 */
@Service
@RequiredArgsConstructor
@Transactional
public class PracticanteService {

    public static final String ENTITY_NAME = "Practicante";

    private final PracticanteRepository practicanteRepository;
    private final PracticanteMapper practicanteMapper;

    /**
     * Obtiene un practicante por su ID.
     *
     * @param id identificador del practicante
     * @return datos del practicante
     * @throws ResourceNotFoundException si no existe
     */
    @Transactional(readOnly = true)
    public PracticanteResponseDto getById(Integer id) {
        PracticanteEntity entity = practicanteRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException(ENTITY_NAME, "ID", id));
        return practicanteMapper.toResponseDto(entity);
    }

    /**
     * Obtiene todos los practicantes con paginación.
     *
     * @param pageable parámetros de paginación
     * @return página de practicantes
     */
    @Transactional(readOnly = true)
    public Page<PracticanteResponseDto> getAll(Pageable pageable) {
        return practicanteRepository.findAll(pageable)
                .map(practicanteMapper::toResponseDto);
    }

    /**
     * Crea un nuevo practicante.
     *
     * @param dto datos del practicante
     * @return practicante creado
     * @throws ResourceAlreadyExistsException si ya existe con el mismo ID de
     *                                        Discord
     */
    @CacheEvict(value = { "practicantesActivosCount", "practicantesActivosList" }, allEntries = true)
    public PracticanteResponseDto create(PracticanteCreateDto dto) {
        practicanteRepository.findByIdDiscord(dto.getIdDiscord())
                .ifPresent(existing -> {
                    throw new ResourceAlreadyExistsException(ENTITY_NAME, "idDiscord", dto.getIdDiscord());
                });

        PracticanteEntity entity = practicanteMapper.toEntity(dto);
        PracticanteEntity saved = practicanteRepository.save(entity);
        return practicanteMapper.toResponseDto(saved);
    }

    /**
     * Actualiza un practicante existente.
     *
     * @param id  identificador del practicante
     * @param dto datos a actualizar
     * @return practicante actualizado
     * @throws ResourceNotFoundException si no existe
     */
    @CacheEvict(value = { "practicantesActivosCount", "practicantesActivosList" }, allEntries = true)
    public PracticanteResponseDto update(Integer id, PracticanteCreateDto dto) {
        PracticanteEntity entity = practicanteRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException(ENTITY_NAME, "ID", id));

        practicanteMapper.updateEntity(dto, entity);
        return practicanteMapper.toResponseDto(practicanteRepository.save(entity));
    }

    /**
     * Retira un practicante (soft-delete: estado → retirado).
     *
     * @param id     identificador del practicante
     * @param motivo motivo del retiro
     * @return confirmación de eliminación
     * @throws ResourceNotFoundException si no existe
     */
    @CacheEvict(value = { "practicantesActivosCount", "practicantesActivosList" }, allEntries = true)
    public DeleteResponseDto delete(Integer id, String motivo) {
        PracticanteEntity entity = practicanteRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException(ENTITY_NAME, "ID", id));

        entity.setEstado("retirado");
        entity.setFechaRetiro(LocalDate.now());
        entity.setMotivoRetiro(motivo != null ? motivo : "Retirado por admin");
        practicanteRepository.save(entity);

        return DeleteResponseDto.builder()
                .message("Practicante retirado exitosamente")
                .id(id)
                .deleted(true)
                .build();
    }
}

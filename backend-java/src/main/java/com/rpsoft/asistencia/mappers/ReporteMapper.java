package com.rpsoft.asistencia.mappers;

import com.rpsoft.asistencia.dtos.ReporteCreateDto;
import com.rpsoft.asistencia.dtos.ReporteResponseDto;
import com.rpsoft.asistencia.entities.ReporteEntity;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

/**
 * Mapper MapStruct para conversiones entre ReporteEntity y DTOs.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Mapper(componentModel = "spring")
public interface ReporteMapper {

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "practicante", ignore = true)
    @Mapping(target = "fecha", ignore = true)
    @Mapping(target = "revisado", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    ReporteEntity toEntity(ReporteCreateDto dto);

    @Mapping(source = "practicante.id", target = "practicanteId")
    @Mapping(source = "practicante.nombreCompleto", target = "practicanteNombre")
    ReporteResponseDto toResponseDto(ReporteEntity entity);
}

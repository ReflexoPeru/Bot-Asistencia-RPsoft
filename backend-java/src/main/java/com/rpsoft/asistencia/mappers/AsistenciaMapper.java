package com.rpsoft.asistencia.mappers;

import com.rpsoft.asistencia.dtos.AsistenciaResponseDto;
import com.rpsoft.asistencia.entities.AsistenciaEntity;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

/**
 * Mapper MapStruct para conversiones entre AsistenciaEntity y DTOs.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Mapper(componentModel = "spring")
public interface AsistenciaMapper {

    @Mapping(source = "practicante.id", target = "practicanteId")
    @Mapping(source = "practicante.nombreCompleto", target = "nombreCompleto")
    AsistenciaResponseDto toResponseDto(AsistenciaEntity entity);
}

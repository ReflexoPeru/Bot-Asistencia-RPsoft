package com.rpsoft.asistencia.mappers;

import com.rpsoft.asistencia.dtos.PracticanteCreateDto;
import com.rpsoft.asistencia.dtos.PracticanteResponseDto;
import com.rpsoft.asistencia.entities.PracticanteEntity;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.MappingTarget;

/**
 * Mapper MapStruct para conversiones entre PracticanteEntity y DTOs.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Mapper(componentModel = "spring")
public interface PracticanteMapper {

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "fechaInscripcion", ignore = true)
    @Mapping(target = "estado", ignore = true)
    @Mapping(target = "fechaRetiro", ignore = true)
    @Mapping(target = "motivoRetiro", ignore = true)
    @Mapping(target = "baneos", ignore = true)
    @Mapping(target = "horasBase", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "createdBy", ignore = true)
    @Mapping(target = "updatedBy", ignore = true)
    PracticanteEntity toEntity(PracticanteCreateDto dto);

    PracticanteResponseDto toResponseDto(PracticanteEntity entity);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "fechaInscripcion", ignore = true)
    @Mapping(target = "estado", ignore = true)
    @Mapping(target = "fechaRetiro", ignore = true)
    @Mapping(target = "motivoRetiro", ignore = true)
    @Mapping(target = "baneos", ignore = true)
    @Mapping(target = "horasBase", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "createdBy", ignore = true)
    @Mapping(target = "updatedBy", ignore = true)
    void updateEntity(PracticanteCreateDto dto, @MappingTarget PracticanteEntity entity);
}

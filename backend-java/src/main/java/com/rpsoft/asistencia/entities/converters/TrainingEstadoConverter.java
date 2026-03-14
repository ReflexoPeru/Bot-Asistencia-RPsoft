package com.rpsoft.asistencia.entities.converters;

import com.rpsoft.asistencia.entities.TrainingEstado;
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = false)
public class TrainingEstadoConverter implements AttributeConverter<TrainingEstado, String> {
    @Override
    public String convertToDatabaseColumn(TrainingEstado attribute) {
        return attribute == null ? null : attribute.toValue();
    }

    @Override
    public TrainingEstado convertToEntityAttribute(String dbData) {
        return dbData == null ? null : TrainingEstado.fromValue(dbData);
    }
}

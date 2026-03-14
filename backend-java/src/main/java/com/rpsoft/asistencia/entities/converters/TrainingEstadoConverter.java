package com.rpsoft.asistencia.entities.converters;

import com.rpsoft.asistencia.entities.TrainingEstado;
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;
import org.postgresql.util.PGobject;

/**
 * Convierte TrainingEstado a PGobject para que JDBC lo envíe como enum PostgreSQL.
 */
@Converter(autoApply = false)
public class TrainingEstadoConverter implements AttributeConverter<TrainingEstado, Object> {

    @Override
    public Object convertToDatabaseColumn(TrainingEstado attribute) {
        if (attribute == null) {
            return null;
        }
        try {
            PGobject obj = new PGobject();
            obj.setType("training_estado");
            obj.setValue(attribute.toValue());
            return obj;
        } catch (Exception e) {
            throw new IllegalStateException("No se pudo convertir estado", e);
        }
    }

    @Override
    public TrainingEstado convertToEntityAttribute(Object dbData) {
        if (dbData == null) {
            return null;
        }
        if (dbData instanceof PGobject pg && pg.getValue() != null) {
            return TrainingEstado.fromValue(pg.getValue());
        }
        return TrainingEstado.fromValue(dbData.toString());
    }
}

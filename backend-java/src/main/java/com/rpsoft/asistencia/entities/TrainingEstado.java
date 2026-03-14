package com.rpsoft.asistencia.entities;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Estados del flujo de capacitación.
 */
public enum TrainingEstado {
    PLANNED,
    IN_PROGRESS,
    PAUSED,
    FINISHED,
    CANCELLED;

    @JsonValue
    public String toValue() {
        return name().toLowerCase();
    }

    @JsonCreator
    public static TrainingEstado fromValue(String value) {
        if (value == null) {
            return null;
        }
        return TrainingEstado.valueOf(value.trim().toUpperCase());
    }
}

package com.rpsoft.asistencia.dtos;

import lombok.Builder;
import lombok.Value;

import java.time.LocalDate;
import java.util.List;

@Value
@Builder
public class ResumenHistorialDto {

    String nombreCompleto;
    Long idDiscord;

    // Resumen de tiempo
    long horasSemanalesSegundos; // Total de la semana actual
    long horasTotalesSegundos; // Total histórico
    long horasRecuperacionSegundos; // Total histórico en recuperación
    long horasRecuperacionSemanalesSegundos; // Total semanal en recuperación

    // Nueva información
    long horasBaseSegundos; // Límite total de horas (de practicante)
    long tardanzasTotales;
    List<ReporteResumenDto> reportes;

    // Listado de los últimos registros (ej. 7 días)
    List<RegistroDiarioDto> ultimosRegistros;

    @Value
    @Builder
    public static class ReporteResumenDto {
        String tipo;
        String descripcion;
        LocalDate fecha;
    }

    @Value
    @Builder
    public static class RegistroDiarioDto {
        LocalDate fecha;
        String diaSemana;
        String horaEntrada;
        String horaSalida;
        String estado;
        boolean esRecuperacion;
        long duracionSegundos;
    }
}

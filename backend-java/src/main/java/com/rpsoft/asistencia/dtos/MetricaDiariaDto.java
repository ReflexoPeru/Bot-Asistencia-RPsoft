package com.rpsoft.asistencia.dtos;

import lombok.Builder;
import lombok.Value;

/**
 * DTO con las 14 métricas del dashboard diario de asistencia.
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Value
@Builder
public class MetricaDiariaDto {
    String fecha;
    String diaSemana;

    // Practicantes
    long totalInicial;
    long totalRetirados;
    long totalActivos;

    // Asistencia hoy
    long ausentesClases;
    long justificaciones;
    long debenAsistir;

    // Detalle
    long presentes;
    long faltanLlegar;
    long tardanzas;
    long sobreHora;
    long faltas;

    // Acumulados
    long tardanzasAcumuladas;
    long retiradosHoy;
}

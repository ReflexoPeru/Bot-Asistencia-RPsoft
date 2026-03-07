package com.rpsoft.asistencia.controllers;

import com.rpsoft.asistencia.dtos.MetricaDiariaDto;
import com.rpsoft.asistencia.services.MetricaService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;

/**
 * Controlador REST para métricas del dashboard.
 * <p>
 * Base: {@code /api/metricas}.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see MetricaService
 */
@RestController
@RequestMapping("/api/metricas")
@RequiredArgsConstructor
public class MetricaController {

    private final MetricaService metricaService;

    /**
     * Obtiene las 14 métricas del dashboard para hoy.
     *
     * @return métricas del día
     */
    @GetMapping("/hoy")
    public ResponseEntity<MetricaDiariaDto> getMetricasHoy() {
        return ResponseEntity.ok(metricaService.getMetricasDelDia(LocalDate.now()));
    }
}

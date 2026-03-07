package com.rpsoft.asistencia.controllers;

import com.rpsoft.asistencia.dtos.AsistenciaResponseDto;
import com.rpsoft.asistencia.services.AsistenciaService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.time.YearMonth;
import java.util.List;
import java.util.Map;

/**
 * Controlador REST para consultar registros de asistencia.
 * <p>
 * Base: {@code /api/asistencia}.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see AsistenciaService
 */
@RestController
@RequestMapping("/api/asistencia")
@RequiredArgsConstructor
public class AsistenciaController {

    private final AsistenciaService asistenciaService;

    /**
     * Obtiene los registros de asistencia de una fecha específica.
     *
     * @param fecha fecha en formato YYYY-MM-DD (default: hoy)
     * @return lista de registros y la fecha consultada
     */
    @GetMapping
    public ResponseEntity<Map<String, Object>> getByFecha(
            @RequestParam(required = false) LocalDate fecha) {
        if (fecha == null) {
            fecha = LocalDate.now();
        }
        List<AsistenciaResponseDto> registros = asistenciaService.getByFecha(fecha);
        return ResponseEntity.ok(Map.of(
                "fecha", fecha.toString(),
                "registros", registros));
    }

    /**
     * Obtiene las fechas de un mes que tienen registros de asistencia.
     *
     * @param mes mes en formato YYYY-MM (default: mes actual)
     * @return lista de fechas con registros
     */
    @GetMapping("/fechas")
    public ResponseEntity<Map<String, Object>> getFechasConRegistros(
            @RequestParam(required = false) String mes) {
        int year, month;
        if (mes != null) {
            YearMonth ym = YearMonth.parse(mes);
            year = ym.getYear();
            month = ym.getMonthValue();
        } else {
            YearMonth now = YearMonth.now();
            year = now.getYear();
            month = now.getMonthValue();
        }

        List<LocalDate> fechas = asistenciaService.getFechasConRegistros(year, month);
        return ResponseEntity.ok(Map.of(
                "mes", String.format("%d-%02d", year, month),
                "fechas", fechas));
    }
}

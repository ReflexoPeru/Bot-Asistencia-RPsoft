package com.rpsoft.asistencia.controllers;

import com.rpsoft.asistencia.dtos.ReporteCreateDto;
import com.rpsoft.asistencia.dtos.ReporteResponseDto;
import com.rpsoft.asistencia.services.ReporteService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * Controlador REST para la gestión de reportes.
 * <p>
 * Base: {@code /api/reportes}.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see ReporteService
 */
@RestController
@RequestMapping("/api/reportes")
@RequiredArgsConstructor
public class ReporteController {

    private final ReporteService reporteService;

    /**
     * Obtiene reportes paginados, opcionalmente filtrados por practicante.
     *
     * @param practicanteId filtro opcional
     * @param page          número de página
     * @param size          tamaño de página
     * @param sortBy        campo para ordenar
     * @return página de reportes
     */
    @GetMapping
    public ResponseEntity<Page<ReporteResponseDto>> getAll(
            @RequestParam(required = false) Long practicanteId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "fecha") String sortBy) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, sortBy));
        return ResponseEntity.ok(reporteService.getAll(practicanteId, pageable));
    }

    /**
     * Crea un nuevo reporte.
     *
     * @param dto datos del reporte
     * @return reporte creado con 201 Created
     */
    @PostMapping
    public ResponseEntity<ReporteResponseDto> create(@Valid @RequestBody ReporteCreateDto dto) {
        return ResponseEntity.status(HttpStatus.CREATED).body(reporteService.create(dto));
    }

    /**
     * Marca un reporte como revisado.
     *
     * @param id identificador del reporte
     * @return reporte actualizado
     */
    @PutMapping("/{id}/revisar")
    public ResponseEntity<ReporteResponseDto> marcarRevisado(@PathVariable Long id) {
        return ResponseEntity.ok(reporteService.marcarRevisado(id));
    }
}

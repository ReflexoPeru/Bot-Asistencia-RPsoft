package com.rpsoft.asistencia.controllers;

import com.rpsoft.asistencia.dtos.DeleteResponseDto;
import com.rpsoft.asistencia.dtos.PracticanteCreateDto;
import com.rpsoft.asistencia.dtos.PracticanteResponseDto;
import com.rpsoft.asistencia.services.PracticanteService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;

/**
 * Controlador REST para la gestión de practicantes.
 * <p>
 * CRUD completo con soft-delete. Base: {@code /api/practicantes}.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see PracticanteService
 */
@RestController
@RequestMapping("/api/practicantes")
@RequiredArgsConstructor
public class PracticanteController {

    private final PracticanteService practicanteService;

    /**
     * Obtiene todos los practicantes con paginación.
     *
     * @param page   número de página (default: 0)
     * @param size   tamaño de página (default: 20)
     * @param sortBy campo para ordenar (default: id)
     * @return página de practicantes
     */
    @GetMapping
    public ResponseEntity<Page<PracticanteResponseDto>> getAll(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "id") String sortBy) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(sortBy));
        return ResponseEntity.ok(practicanteService.getAll(pageable));
    }

    /**
     * Obtiene un practicante por su ID.
     *
     * @param id identificador del practicante
     * @return datos del practicante
     */
    @GetMapping("/{id}")
    public ResponseEntity<PracticanteResponseDto> getById(@PathVariable Integer id) {
        return ResponseEntity.ok(practicanteService.getById(id));
    }

    /**
     * Crea un nuevo practicante.
     *
     * @param dto datos del practicante
     * @param ucb builder para generar la URI de Location
     * @return practicante creado con 201 Created
     */
    @PostMapping
    public ResponseEntity<PracticanteResponseDto> create(
            @Valid @RequestBody PracticanteCreateDto dto,
            UriComponentsBuilder ucb) {
        PracticanteResponseDto response = practicanteService.create(dto);
        URI location = ucb.path("/api/practicantes/{id}")
                .buildAndExpand(response.getId())
                .toUri();
        return ResponseEntity.created(location).body(response);
    }

    /**
     * Actualiza un practicante existente.
     *
     * @param id  identificador del practicante
     * @param dto datos a actualizar
     * @return practicante actualizado
     */
    @PutMapping("/{id}")
    public ResponseEntity<PracticanteResponseDto> update(
            @PathVariable Integer id,
            @Valid @RequestBody PracticanteCreateDto dto) {
        return ResponseEntity.ok(practicanteService.update(id, dto));
    }

    /**
     * Retira un practicante (soft-delete).
     *
     * @param id     identificador del practicante
     * @param motivo motivo del retiro (opcional)
     * @return confirmación de retiro
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<DeleteResponseDto> delete(
            @PathVariable Integer id,
            @RequestParam(required = false) String motivo) {
        return ResponseEntity.ok(practicanteService.delete(id, motivo));
    }
}

package com.rpsoft.asistencia.controllers;

import com.rpsoft.asistencia.dtos.capacitacion.*;
import com.rpsoft.asistencia.services.CapacitacionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/capacitacion")
@RequiredArgsConstructor
public class CapacitacionController {

    private final CapacitacionService capacitacionService;

    @GetMapping("/practicante/{id}")
    public ResponseEntity<CapacitacionPracticanteResponseDto> getByPracticante(
            @PathVariable("id") Integer practicanteId,
            @RequestParam(value = "curso", required = false) String cursoNombre) {
        return ResponseEntity.ok(capacitacionService.getProgresos(practicanteId, java.util.Optional.ofNullable(cursoNombre)));
    }

    @PostMapping("/curso")
    public ResponseEntity<CapacitacionCursoDto> crearCurso(
            @Valid @RequestBody CapacitacionCursoCreateRequest request) {
        CapacitacionCursoDto dto = capacitacionService.crearCurso(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    @PostMapping("/curso/{id}/temas")
    public ResponseEntity<CapacitacionCursoDto> agregarTemas(
            @PathVariable("id") Integer cursoId,
            @Valid @RequestBody CapacitacionAgregarTemasRequest request) {
        CapacitacionCursoDto dto = capacitacionService.agregarTemas(cursoId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    @PostMapping("/iniciar")
    public ResponseEntity<CapacitacionProgresoResponseDto> iniciar(
            @Valid @RequestBody CapacitacionIniciarRequest request) {
        CapacitacionProgresoResponseDto dto = capacitacionService.iniciar(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    @PostMapping("/pausar")
    public ResponseEntity<CapacitacionProgresoResponseDto> pausar(
            @Valid @RequestBody CapacitacionBaseRequest request) {
        return ResponseEntity.ok(capacitacionService.pausar(request));
    }

    @PostMapping("/reanudar")
    public ResponseEntity<CapacitacionProgresoResponseDto> reanudar(
            @Valid @RequestBody CapacitacionBaseRequest request) {
        return ResponseEntity.ok(capacitacionService.reanudar(request));
    }

    @PostMapping("/finalizar")
    public ResponseEntity<CapacitacionProgresoResponseDto> finalizar(
            @Valid @RequestBody CapacitacionBaseRequest request) {
        return ResponseEntity.ok(capacitacionService.finalizar(request));
    }

    @PatchMapping("/evaluador")
    public ResponseEntity<CapacitacionProgresoResponseDto> asignarEvaluador(
            @Valid @RequestBody CapacitacionAsignarEvaluadorRequest request) {
        return ResponseEntity.ok(capacitacionService.asignarEvaluador(request));
    }

    @PostMapping("/evaluador/activar")
    public ResponseEntity<CapacitacionEvaluadorDto> activarEvaluador(
            @Valid @RequestBody CapacitacionEvaluadorToggleRequest request) {
        return ResponseEntity.ok(capacitacionService.activarEvaluador(request));
    }

    @PostMapping("/evaluador/desactivar")
    public ResponseEntity<CapacitacionEvaluadorDto> desactivarEvaluador(
            @Valid @RequestBody CapacitacionEvaluadorToggleRequest request) {
        return ResponseEntity.ok(capacitacionService.desactivarEvaluador(request));
    }
}

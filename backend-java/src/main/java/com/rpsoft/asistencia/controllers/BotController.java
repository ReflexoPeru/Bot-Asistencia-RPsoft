package com.rpsoft.asistencia.controllers;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Controlador para recibir métricas y estado del bot de Discord.
 */
@RestController
@RequestMapping("/api/v1")
public class BotController {

    private static final Logger log = LoggerFactory.getLogger(BotController.class);

    @PostMapping(value = {"/metrics", "/metrics/"})
    public ResponseEntity<Map<String, String>> receiveMetrics(@RequestBody Map<String, Object> payload) {
        log.info("Métricas recibidas del bot: {}", payload);
        // Aquí podrías guardar las métricas en la base de datos o en memoria
        return ResponseEntity.ok(Map.of("message", "Métricas recibidas correctamente"));
    }

    @PostMapping(value = {"/status", "/status/"})
    public ResponseEntity<Map<String, String>> receiveStatus(@RequestBody Map<String, Object> payload) {
        log.info("Estado recibido del bot: {}", payload);
        return ResponseEntity.ok(Map.of("message", "Estado recibido correctamente"));
    }
}

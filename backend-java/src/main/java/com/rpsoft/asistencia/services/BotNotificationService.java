package com.rpsoft.asistencia.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Map;

/**
 * Servicio para enviar notificaciones a Discord via el bot Python.
 * <p>
 * Hace HTTP POST al endpoint interno del bot Python para que envíe
 * mensajes a los canales de Discord, ya que solo el bot tiene acceso
 * al API de Discord.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Service
public class BotNotificationService {

    private static final Logger log = LoggerFactory.getLogger(BotNotificationService.class);

    private final RestClient restClient;

    public BotNotificationService(
            @Value("${bot.internal.url:http://bot:10000}") String botBaseUrl) {
        this.restClient = RestClient.builder()
                .baseUrl(botBaseUrl)
                .build();
    }

    /**
     * Envía un mensaje a un canal de Discord a través del bot Python.
     *
     * @param channelId ID del canal de Discord
     * @param content   contenido del mensaje
     * @return true si se envió correctamente, false en caso de error
     */
    public boolean sendMessage(String channelId, String content) {
        try {
            restClient.post()
                    .uri("/api/internal/send-message")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of("channel_id", channelId, "content", content))
                    .retrieve()
                    .toBodilessEntity();
            log.info("Mensaje enviado al canal {}", channelId);
            return true;
        } catch (Exception e) {
            log.error("Error al enviar mensaje al bot: {}", e.getMessage());
            return false;
        }
    }
}

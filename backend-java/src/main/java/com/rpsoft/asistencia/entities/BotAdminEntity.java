package com.rpsoft.asistencia.entities;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

/**
 * Entidad que representa un administrador del bot.
 * <p>
 * Mapea la tabla {@code bot_admin}. La clave primaria es el discord_id.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Getter
@Setter
@Entity
@Table(name = "bot_admin")
public class BotAdminEntity {

    @Id
    @Column(name = "discord_id", nullable = false)
    private Long discordId;

    @Column(name = "nombre_discord", length = 255)
    private String nombreDiscord;

    @Column(name = "rol", length = 100)
    private String rol = "Developer";
}

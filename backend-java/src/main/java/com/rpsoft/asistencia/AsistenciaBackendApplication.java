package com.rpsoft.asistencia;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Clase principal del backend de asistencia de RPSoft.
 * <p>
 * Gestiona la API REST, automatizaciones programadas y auditoría de datos.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@SpringBootApplication
@EnableJpaAuditing
@EnableScheduling
@EnableCaching
public class AsistenciaBackendApplication {

	public static void main(String[] args) {
		SpringApplication.run(AsistenciaBackendApplication.class, args);
	}
}

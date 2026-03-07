package com.rpsoft.asistencia.scheduler;

import com.rpsoft.asistencia.entities.AsistenciaEntity;
import com.rpsoft.asistencia.entities.RecuperacionEntity;
import com.rpsoft.asistencia.repositories.AsistenciaRepository;
import com.rpsoft.asistencia.repositories.RecuperacionRepository;
import com.rpsoft.asistencia.services.BotNotificationService;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;

/**
 * Tareas programadas de asistencia migradas desde el bot Python.
 * <p>
 * - Auto-salida de asistencia a las 14:15 (L-S)
 * - Auto-cierre de recuperación a las 20:20 (L-S)
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 */
@Component
@RequiredArgsConstructor
public class AsistenciaScheduler {

    private static final Logger log = LoggerFactory.getLogger(AsistenciaScheduler.class);

    private static final LocalTime HORA_SALIDA_OFICIAL = LocalTime.of(14, 0);
    private static final LocalTime HORA_FIN_RECUPERACION = LocalTime.of(20, 0);

    private final AsistenciaRepository asistenciaRepository;
    private final RecuperacionRepository recuperacionRepository;
    private final BotNotificationService botNotificationService;

    @Value("${bot.channel.asistencia:}")
    private String canalAsistencia;

    /**
     * Auto-cierre de salida de asistencia a las 14:15 de lunes a sábado.
     * <p>
     * Busca registros de asistencia del día actual que tengan hora_entrada
     * pero sin hora_salida, y les asigna las 14:00 como hora de salida
     * con la marca de salida automática.
     * </p>
     */
    @Scheduled(cron = "0 15 14 * * MON-SAT", zone = "America/Lima")
    @Transactional
    public void autoSalidaAsistencia() {
        LocalDate hoy = LocalDate.now();
        List<AsistenciaEntity> sinSalida = asistenciaRepository.findSinSalidaByFecha(hoy);

        if (sinSalida.isEmpty()) {
            log.info("[Scheduler] No hay registros sin salida hoy ({}).", hoy);
            return;
        }

        int count = 0;
        for (AsistenciaEntity asistencia : sinSalida) {
            asistencia.setHoraSalida(HORA_SALIDA_OFICIAL);
            asistencia.setSalidaAuto(true);
            asistenciaRepository.save(asistencia);
            count++;
        }

        log.info("[Scheduler] Auto-salida aplicada a {} registros el {}.", count, hoy);

        if (!canalAsistencia.isBlank()) {
            botNotificationService.sendMessage(
                    canalAsistencia,
                    String.format("⏰ Se aplicó auto-salida (14:00) a %d practicantes que no registraron salida.",
                            count));
        }
    }

    /**
     * Auto-cierre de sesiones de recuperación a las 20:20 de lunes a sábado.
     * <p>
     * Busca sesiones de recuperación abiertas del día actual y las cierra
     * con estado 'valido' y hora_salida a las 20:00.
     * </p>
     */
    @Scheduled(cron = "0 20 20 * * MON-SAT", zone = "America/Lima")
    @Transactional
    public void autoCierreRecuperacion() {
        LocalDate hoy = LocalDate.now();
        List<RecuperacionEntity> abiertas = recuperacionRepository.findByFechaAndEstado(hoy, "abierto");

        if (abiertas.isEmpty()) {
            log.info("[Scheduler] No hay recuperaciones abiertas hoy ({}).", hoy);
            return;
        }

        int count = 0;
        for (RecuperacionEntity rec : abiertas) {
            rec.setHoraSalida(HORA_FIN_RECUPERACION);
            rec.setEstado("valido");
            rec.setSalidaAuto(true);
            recuperacionRepository.save(rec);
            count++;
        }

        log.info("[Scheduler] Auto-cierre de recuperación aplicado a {} sesiones el {}.", count, hoy);

        if (!canalAsistencia.isBlank()) {
            botNotificationService.sendMessage(
                    canalAsistencia,
                    String.format("🔄 Se cerró automáticamente %d sesiones de recuperación (20:00).", count));
        }
    }
}

package com.rpsoft.asistencia.scheduler;

import com.rpsoft.asistencia.entities.AsistenciaEntity;
import com.rpsoft.asistencia.entities.RecuperacionEntity;
import com.rpsoft.asistencia.entities.ReporteEntity;
import com.rpsoft.asistencia.repositories.AsistenciaRepository;
import com.rpsoft.asistencia.repositories.RecuperacionRepository;
import com.rpsoft.asistencia.repositories.ReporteRepository;
import com.rpsoft.asistencia.services.BotNotificationService;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.List;

/**
 * Tareas programadas para control automático de asistencia.
 * <p>
 * Contiene los jobs de auto-salida regular y auto-cierre de recuperaciones,
 * notificando al canal de Discord correspondiente.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.0
 * @since 2026-03-07
 * @see BotNotificationService
 */
@Component
@RequiredArgsConstructor
public class AsistenciaScheduler {

    private static final Logger log = LoggerFactory.getLogger(AsistenciaScheduler.class);

    private final AsistenciaRepository asistenciaRepository;
    private final RecuperacionRepository recuperacionRepository;
    private final ReporteRepository reporteRepository;
    private final BotNotificationService botNotificationService;

    @Value("${discord.bot.channels.asistencia}")
    private String canalAsistencia;

    private static final LocalTime HORA_SALIDA_OFICIAL = LocalTime.of(14, 0);
    private static final LocalTime HORA_FIN_RECUPERACION = LocalTime.of(20, 0);

    /**
     * Auto-salida de asistencia regular a las 14:17 de lunes a sábado.
     * <p>
     * Busca registros sin salida del día actual y les asigna 14:00. Se
     * ejecuta a las 14:17 para dar 2 minutos al script Python de enviar las
     * alertas de tardanza de recuperación (14:15).
     * </p>
     */
    @Scheduled(cron = "0 17 14 * * MON-SAT", zone = "America/Lima")
    @Transactional
    public void autoSalidaAsistencia() {
        LocalDate hoy = LocalDate.now(ZoneId.of("America/Lima"));
        LocalDateTime nowInfo = LocalDateTime.now(ZoneId.of("America/Lima")).truncatedTo(ChronoUnit.SECONDS);
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

            ReporteEntity reporte = new ReporteEntity();
            reporte.setPracticante(asistencia.getPracticante());
            reporte.setTipo("afk_salida");
            reporte.setDescripcion("Salida automática por sistema (Jornada regular).");
            reporte.setFecha(hoy);
            reporte.setCreatedAt(nowInfo);
            reporteRepository.save(reporte);

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
     * con estado 'valido' y hora_salida a las 20:00. Se ejecuta a las 20:22 para
     * dar 2 minutos al script Python de enviar las alertas.
     * </p>
     */
    @Scheduled(cron = "0 22 20 * * MON-SAT", zone = "America/Lima")
    @Transactional
    public void autoCierreRecuperacion() {
        LocalDate hoy = LocalDate.now(ZoneId.of("America/Lima"));
        LocalDateTime nowInfo = LocalDateTime.now(ZoneId.of("America/Lima")).truncatedTo(ChronoUnit.SECONDS);
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

            ReporteEntity reporte = new ReporteEntity();
            reporte.setPracticante(rec.getPracticante());
            reporte.setTipo("afk_salida");
            reporte.setDescripcion("Salida automática por sistema (Recuperación).");
            reporte.setFecha(hoy);
            reporte.setCreatedAt(nowInfo);
            reporteRepository.save(reporte);

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

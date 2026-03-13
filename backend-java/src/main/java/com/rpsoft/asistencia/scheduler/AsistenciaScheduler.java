package com.rpsoft.asistencia.scheduler;

import com.rpsoft.asistencia.entities.AsistenciaEntity;
import com.rpsoft.asistencia.entities.PracticanteEntity;
import com.rpsoft.asistencia.entities.RecuperacionEntity;
import com.rpsoft.asistencia.entities.ReporteEntity;
import com.rpsoft.asistencia.repositories.AsistenciaRepository;
import com.rpsoft.asistencia.repositories.PracticanteRepository;
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

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Objects;

/**
 * Tareas programadas para control automático de asistencia.
 * <p>
 * Contiene los jobs de auto-salida, auto-cierre de recuperaciones y la
 * verificación de faltas diarias con retiro automático.
 * </p>
 *
 * @author RPSoft Team
 * @version 1.1
 * @since 2026-03-11
 * @see BotNotificationService
 */
@Component
@RequiredArgsConstructor
public class AsistenciaScheduler {

    private static final Logger log = LoggerFactory.getLogger(AsistenciaScheduler.class);
    private static final ZoneId LIMA_ZONE = ZoneId.of("America/Lima");

    private final AsistenciaRepository asistenciaRepository;
    private final RecuperacionRepository recuperacionRepository;
    private final ReporteRepository reporteRepository;
    private final PracticanteRepository practicanteRepository;
    private final BotNotificationService botNotificationService;

    @Value("${discord.bot.channels.asistencia:}")
    private String canalAsistencia;

    private static final LocalTime HORA_SALIDA_OFICIAL = LocalTime.of(14, 0);
    private static final LocalTime HORA_FIN_RECUPERACION = LocalTime.of(20, 0);

    /**
     * Verifica diariamente las faltas de asistencia a las 14:20 (Lima).
     * <p>
     * Ignora los domingos. Para cada practicante activo, comprueba si ha
     * registrado asistencia. Si no lo ha hecho y no tiene clases, le asigna
     * una falta, le notifica y verifica si debe ser retirado por acumulación
     * de 3 faltas consecutivas.
     * </p>
     */
    @Scheduled(cron = "0 20 14 * * MON-SAT", zone = "America/Lima")
    @Transactional
    public void verificarFaltasDiarias() {
        LocalDate hoy = LocalDate.now(LIMA_ZONE);
        log.info("[Scheduler] Iniciando verificación de faltas para el día {}.", hoy);

        List<PracticanteEntity> activos = practicanteRepository.findByEstado("activo");
        log.info("[Scheduler] Se encontraron {} practicantes activos.", activos.size());

        for (PracticanteEntity practicante : activos) {
            procesarPracticante(practicante, hoy);
        }
        log.info("[Scheduler] Finalizada verificación de faltas para el día {}.", hoy);
    }

    private void procesarPracticante(PracticanteEntity practicante, LocalDate hoy) {
        boolean yaMarcoAsistencia = asistenciaRepository.findByPracticanteIdAndFecha(practicante.getId(), hoy)
                .isPresent();
        if (yaMarcoAsistencia) {
            return;
        }

        if (tieneClaseHoy(practicante, hoy)) {
            crearAsistenciaClases(practicante, hoy);
        } else {
            registrarFalta(practicante, hoy);
            verificarRetiroPorFaltas(practicante);
        }
    }

    private boolean tieneClaseHoy(PracticanteEntity practicante, LocalDate fecha) {
        DayOfWeek dia = fecha.getDayOfWeek();
        return switch (dia) {
            case MONDAY -> Boolean.TRUE.equals(practicante.getClaseLunes());
            case TUESDAY -> Boolean.TRUE.equals(practicante.getClaseMartes());
            case WEDNESDAY -> Boolean.TRUE.equals(practicante.getClaseMiercoles());
            case THURSDAY -> Boolean.TRUE.equals(practicante.getClaseJueves());
            case FRIDAY -> Boolean.TRUE.equals(practicante.getClaseViernes());
            case SATURDAY -> Boolean.TRUE.equals(practicante.getClaseSabado());
            default -> false;
        };
    }

    private void crearAsistenciaClases(PracticanteEntity practicante, LocalDate hoy) {
        AsistenciaEntity asistenciaClases = new AsistenciaEntity();
        asistenciaClases.setPracticante(practicante);
        asistenciaClases.setFecha(hoy);
        asistenciaClases.setEstado("clases");
        asistenciaRepository.save(asistenciaClases);
        log.info("[Scheduler] Creado registro de 'clases' para practicante ID: {}", practicante.getId());
    }

    private void registrarFalta(PracticanteEntity practicante, LocalDate hoy) {
        AsistenciaEntity falta = new AsistenciaEntity();
        falta.setPracticante(practicante);
        falta.setFecha(hoy);
        falta.setEstado("falto");
        asistenciaRepository.save(falta);

        ReporteEntity reporte = new ReporteEntity();
        reporte.setPracticante(practicante);
        reporte.setTipo("inasistencia");
        reporte.setDescripcion("Falta automática por no registrar asistencia.");
        reporte.setFecha(hoy);
        reporte.setCreatedAt(LocalDateTime.now(LIMA_ZONE));
        reporteRepository.save(reporte);

        log.warn("[Scheduler] Registrada FALTA para practicante ID: {}. Se enviará notificación.", practicante.getId());
        botNotificationService.sendDm(
                practicante.getIdDiscord(),
                "⚠️ **Tienes una falta por no registrar tu asistencia hoy.**\nRecuerda que acumular 3 faltas consecutivas es causal de retiro.");
    }

    private void verificarRetiroPorFaltas(PracticanteEntity practicante) {
        List<AsistenciaEntity> ultimasAsistencias = asistenciaRepository
                .findTop3ByPracticanteIdOrderByFechaDesc(practicante.getId());

        if (ultimasAsistencias.size() < 3) {
            return;
        }

        boolean tresFaltasConsecutivas = ultimasAsistencias.stream()
                .allMatch(a -> Objects.equals(a.getEstado(), "falto"));

        if (tresFaltasConsecutivas) {
            practicante.setEstado("retirado");
            practicante.setFechaRetiro(LocalDate.now(LIMA_ZONE));
            practicante.setMotivoRetiro("Retiro automático por 3 faltas consecutivas.");
            practicanteRepository.save(practicante);

            log.error("[Scheduler] RETIRO AUTOMÁTICO del practicante ID: {} por 3 faltas consecutivas.",
                    practicante.getId());
            botNotificationService.sendDm(
                    practicante.getIdDiscord(),
                    "❌ **Has sido retirado del programa de practicantes.**\n**Motivo:** Acumulación de 3 faltas consecutivas.");
        }
    }

    /**
     * Auto-salida de asistencia regular a las 14:17 de lunes a sábado.
     * <p>
     * Busca registros sin salida del día actual y les asigna 14:00. Se
     * ejecuta a las 14:17 para dar 2 minutos al script Python de enviar las
     * alertas de auto-salida (14:15). Sí, la intención es que el bot lea
     * los registros como "pendientes" a las 14:15, envíe los DMs, y luego
     * el backend los cierre definitivamente a las 14:17.
     * </p>
     */
    @Scheduled(cron = "0 17 14 * * MON-SAT", zone = "America/Lima")
    @Transactional
    public void autoSalidaAsistencia() {
        LocalDate hoy = LocalDate.now(LIMA_ZONE);
        LocalDateTime nowInfo = LocalDateTime.now(LIMA_ZONE).truncatedTo(ChronoUnit.SECONDS);
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
     * Auto-cierre de sesiones de recuperación a las 20:22 de lunes a sábado.
     * <p>
     * Busca sesiones de recuperación abiertas del día actual y las cierra
     * con estado 'valido' y hora_salida a las 20:00. Se ejecuta a las 20:22 para
     * dar 2 minutos al script Python para enviar las alertas de cierre (20:20)
     * antes de asentar los cambios en la base de datos.
     * </p>
     */
    @Scheduled(cron = "0 22 20 * * MON-SAT", zone = "America/Lima")
    @Transactional
    public void autoCierreRecuperacion() {
        LocalDate hoy = LocalDate.now(LIMA_ZONE);
        LocalDateTime nowInfo = LocalDateTime.now(LIMA_ZONE).truncatedTo(ChronoUnit.SECONDS);
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

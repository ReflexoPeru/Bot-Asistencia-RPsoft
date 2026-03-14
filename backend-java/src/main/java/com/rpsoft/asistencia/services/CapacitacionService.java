package com.rpsoft.asistencia.services;

import com.rpsoft.asistencia.dtos.capacitacion.*;
import com.rpsoft.asistencia.entities.PracticanteEntity;
import com.rpsoft.asistencia.entities.TrainingEstado;
import com.rpsoft.asistencia.entities.capacitacion.*;
import com.rpsoft.asistencia.exceptions.BadRequestException;
import com.rpsoft.asistencia.exceptions.ResourceAlreadyExistsException;
import com.rpsoft.asistencia.exceptions.ResourceNotFoundException;
import com.rpsoft.asistencia.repositories.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class CapacitacionService {

    private final PracticanteRepository practicanteRepository;
    private final CapacitacionCursoRepository cursoRepository;
    private final CapacitacionTemaRepository temaRepository;
    private final CapacitacionEvaluadorRepository evaluadorRepository;
    private final CapacitacionProgresoRepository progresoRepository;

    @Transactional(readOnly = true)
    public CapacitacionPracticanteResponseDto getProgresos(Integer practicanteId, Optional<String> cursoNombreOpt) {
        PracticanteEntity practicante = practicanteRepository.findById(practicanteId)
                .orElseThrow(() -> new ResourceNotFoundException("Practicante no encontrado"));

        List<CapacitacionCursoEntity> cursos = cursoNombreOpt
                .map(nombre -> List.of(cursoRepository.findByNombreIgnoreCase(nombre)
                        .orElseThrow(() -> new ResourceNotFoundException("Curso no encontrado"))))
                .orElseGet(cursoRepository::findAll);

        List<CapacitacionCursoProgresoDto> cursoDtos = new ArrayList<>();
        for (CapacitacionCursoEntity curso : cursos) {
            List<CapacitacionTemaEntity> temas = temaRepository.findByCursoOrderByOrdenAsc(curso);
            Map<Integer, CapacitacionProgresoEntity> progresoPorTema = progresoRepository
                    .findByPracticanteAndCurso(practicante, curso)
                    .stream()
                    .collect(Collectors.toMap(p -> p.getTema().getId(), p -> p));

            List<CapacitacionTemaProgresoDto> temasDto = temas.stream()
                    .map(tema -> {
                        CapacitacionProgresoEntity progreso = progresoPorTema.get(tema.getId());
                        return mapTemaProgreso(tema, progreso);
                    })
                    .toList();

            cursoDtos.add(CapacitacionCursoProgresoDto.builder()
                    .curso(curso.getNombre())
                    .temas(temasDto)
                    .build());
        }

        return CapacitacionPracticanteResponseDto.builder()
                .practicanteId(practicante.getId())
                .practicanteNombre(practicante.getNombreCompleto())
                .cursos(cursoDtos)
                .build();
    }

    @Transactional
    public CapacitacionProgresoResponseDto iniciar(CapacitacionIniciarRequest request) {
        CapacitacionContext ctx = loadContext(request.getPracticanteId(), request.getCursoNombre(), request.getTemaNombre());
        CapacitacionProgresoEntity progreso = progresoRepository.findByPracticanteAndTema(ctx.practicante(), ctx.tema())
                .orElseGet(() -> {
                    if (Boolean.TRUE.equals(request.getCrearSiNoExiste())) {
                        return createPlanned(ctx);
                    }
                    throw new ResourceNotFoundException("No existe progreso para este tema");
                });

        ensureNotCancelled(progreso);
        if (progreso.getEstado() != TrainingEstado.PLANNED) {
            throw new ResourceAlreadyExistsException("Progreso", "estado", progreso.getEstado().toValue());
        }

        if (request.getEvaluadorId() != null) {
            progreso.setEvaluador(resolveEvaluador(request.getEvaluadorId(), ctx.practicante().getId()));
        }

        LocalDateTime now = LocalDateTime.now();
        if (progreso.getFechaInicio() == null) {
            progreso.setFechaInicio(now);
        }
        progreso.setUltimaReanudacion(now);
        progreso.setEstado(TrainingEstado.IN_PROGRESS);
        progresoRepository.save(progreso);
        return mapProgreso(progreso);
    }

    @Transactional
    public CapacitacionProgresoResponseDto pausar(CapacitacionBaseRequest request) {
        CapacitacionProgresoEntity progreso = getProgresoOrThrow(request);
        ensureNotCancelled(progreso);
        if (progreso.getEstado() != TrainingEstado.IN_PROGRESS) {
            throw new ResourceAlreadyExistsException("Progreso", "estado", progreso.getEstado().toValue());
        }

        LocalDateTime now = LocalDateTime.now();
        progreso.setAcumulado(calcAcumulado(progreso, now));
        progreso.setUltimaReanudacion(null);
        progreso.setEstado(TrainingEstado.PAUSED);
        progresoRepository.save(progreso);
        return mapProgreso(progreso);
    }

    @Transactional
    public CapacitacionProgresoResponseDto reanudar(CapacitacionBaseRequest request) {
        CapacitacionProgresoEntity progreso = getProgresoOrThrow(request);
        ensureNotCancelled(progreso);
        if (progreso.getEstado() != TrainingEstado.PAUSED) {
            throw new ResourceAlreadyExistsException("Progreso", "estado", progreso.getEstado().toValue());
        }
        progreso.setEstado(TrainingEstado.IN_PROGRESS);
        progreso.setUltimaReanudacion(LocalDateTime.now());
        progresoRepository.save(progreso);
        return mapProgreso(progreso);
    }

    @Transactional
    public CapacitacionProgresoResponseDto finalizar(CapacitacionBaseRequest request) {
        CapacitacionProgresoEntity progreso = getProgresoOrThrow(request);
        ensureNotCancelled(progreso);
        if (progreso.getEstado() != TrainingEstado.IN_PROGRESS) {
            throw new ResourceAlreadyExistsException("Progreso", "estado", progreso.getEstado().toValue());
        }
        LocalDateTime now = LocalDateTime.now();
        Duration total = calcAcumulado(progreso, now);
        progreso.setAcumulado(total);
        progreso.setDuracionFinal(total);
        progreso.setFechaFin(now);
        progreso.setUltimaReanudacion(null);
        progreso.setEstado(TrainingEstado.FINISHED);
        progresoRepository.save(progreso);
        return mapProgreso(progreso);
    }

    @Transactional
    public CapacitacionProgresoResponseDto asignarEvaluador(CapacitacionAsignarEvaluadorRequest request) {
        CapacitacionContext ctx = loadContext(request.getPracticanteId(), request.getCursoNombre(), request.getTemaNombre());
        CapacitacionProgresoEntity progreso = progresoRepository.findByPracticanteAndTema(ctx.practicante(), ctx.tema())
                .orElseGet(() -> createPlanned(ctx));

        ensureNotCancelled(progreso);
        progreso.setEvaluador(resolveEvaluador(request.getEvaluadorId(), ctx.practicante().getId()));
        progresoRepository.save(progreso);
        return mapProgreso(progreso);
    }

    @Transactional
    public CapacitacionEvaluadorDto activarEvaluador(CapacitacionEvaluadorToggleRequest request) {
        PracticanteEntity practicante = practicanteRepository.findById(request.getPracticanteId())
                .orElseThrow(() -> new ResourceNotFoundException("Practicante no encontrado"));

        CapacitacionEvaluadorEntity evaluador = evaluadorRepository.findById(practicante.getId())
                .orElseGet(CapacitacionEvaluadorEntity::new);
        evaluador.setPracticanteId(practicante.getId());
        evaluador.setActivo(true);
        evaluador.setNotas(request.getNotas());
        evaluadorRepository.save(evaluador);
        return mapEvaluador(evaluador, practicante);
    }

    @Transactional
    public CapacitacionEvaluadorDto desactivarEvaluador(CapacitacionEvaluadorToggleRequest request) {
        PracticanteEntity practicante = practicanteRepository.findById(request.getPracticanteId())
                .orElseThrow(() -> new ResourceNotFoundException("Practicante no encontrado"));
        CapacitacionEvaluadorEntity evaluador = evaluadorRepository.findById(practicante.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Evaluador no encontrado"));
        evaluador.setActivo(false);
        evaluadorRepository.save(evaluador);
        return mapEvaluador(evaluador, practicante);
    }

    // -------------------- Helpers --------------------

    private Duration calcAcumulado(CapacitacionProgresoEntity progreso, LocalDateTime now) {
        Duration base = Optional.ofNullable(progreso.getAcumulado()).orElse(Duration.ZERO);
        if (progreso.getEstado() == TrainingEstado.IN_PROGRESS && progreso.getUltimaReanudacion() != null) {
            Duration delta = Duration.between(progreso.getUltimaReanudacion(), now);
            base = base.plus(delta);
        }
        return base.truncatedTo(ChronoUnit.SECONDS);
    }

    private CapacitacionProgresoEntity createPlanned(CapacitacionContext ctx) {
        CapacitacionProgresoEntity progreso = new CapacitacionProgresoEntity();
        progreso.setPracticante(ctx.practicante());
        progreso.setCurso(ctx.curso());
        progreso.setTema(ctx.tema());
        progreso.setEstado(TrainingEstado.PLANNED);
        progreso.setAcumulado(Duration.ZERO);
        return progresoRepository.save(progreso);
    }

    private CapacitacionProgresoEntity getProgresoOrThrow(CapacitacionBaseRequest request) {
        CapacitacionContext ctx = loadContext(request.getPracticanteId(), request.getCursoNombre(), request.getTemaNombre());
        return progresoRepository.findByPracticanteAndTema(ctx.practicante(), ctx.tema())
                .orElseThrow(() -> new ResourceNotFoundException("No existe progreso para este tema"));
    }

    private CapacitacionEvaluadorEntity resolveEvaluador(Integer evaluadorId, Integer practicanteId) {
        if (Objects.equals(evaluadorId, practicanteId)) {
            throw new BadRequestException("El evaluador no puede ser el mismo practicante");
        }
        CapacitacionEvaluadorEntity evaluador = evaluadorRepository.findById(evaluadorId)
                .orElseThrow(() -> new BadRequestException("Evaluador inválido o inactivo"));
        if (Boolean.FALSE.equals(evaluador.getActivo())) {
            throw new BadRequestException("Evaluador inválido o inactivo");
        }
        return evaluador;
    }

    private CapacitacionEvaluadorDto mapEvaluador(CapacitacionEvaluadorEntity evaluador, PracticanteEntity practicante) {
        return CapacitacionEvaluadorDto.builder()
                .id(evaluador.getPracticanteId())
                .nombre(practicante.getNombreCompleto())
                .activo(evaluador.getActivo())
                .notas(evaluador.getNotas())
                .build();
    }

    private CapacitacionTemaProgresoDto mapTemaProgreso(CapacitacionTemaEntity tema, CapacitacionProgresoEntity progreso) {
        if (progreso == null) {
            return CapacitacionTemaProgresoDto.builder()
                    .curso(tema.getCurso().getNombre())
                    .tema(tema.getNombre())
                    .orden(tema.getOrden())
                    .estado(TrainingEstado.PLANNED.toValue())
                    .build();
        }
        return CapacitacionTemaProgresoDto.builder()
                .curso(progreso.getCurso().getNombre())
                .tema(progreso.getTema().getNombre())
                .orden(progreso.getTema().getOrden())
                .estado(progreso.getEstado().toValue())
                .evaluador(mapEvaluadorMaybe(progreso.getEvaluador()))
                .fechaInicio(progreso.getFechaInicio())
                .fechaFin(progreso.getFechaFin())
                .ultimaReanudacion(progreso.getUltimaReanudacion())
                .acumulado(progreso.getEstado() == TrainingEstado.IN_PROGRESS
                        ? calcAcumulado(progreso, LocalDateTime.now())
                        : progreso.getAcumulado())
                .duracionFinal(progreso.getDuracionFinal())
                .build();
    }

    private CapacitacionProgresoResponseDto mapProgreso(CapacitacionProgresoEntity progreso) {
        return CapacitacionProgresoResponseDto.builder()
                .curso(progreso.getCurso().getNombre())
                .tema(progreso.getTema().getNombre())
                .orden(progreso.getTema().getOrden())
                .estado(progreso.getEstado().toValue())
                .evaluador(mapEvaluadorMaybe(progreso.getEvaluador()))
                .fechaInicio(progreso.getFechaInicio())
                .fechaFin(progreso.getFechaFin())
                .ultimaReanudacion(progreso.getUltimaReanudacion())
                .acumulado(progreso.getEstado() == TrainingEstado.IN_PROGRESS
                        ? calcAcumulado(progreso, LocalDateTime.now())
                        : progreso.getAcumulado())
                .duracionFinal(progreso.getDuracionFinal())
                .build();
    }

    private CapacitacionEvaluadorDto mapEvaluadorMaybe(CapacitacionEvaluadorEntity evaluador) {
        if (evaluador == null) {
            return null;
        }
        String nombre = Optional.ofNullable(evaluador.getPracticante())
                .map(PracticanteEntity::getNombreCompleto)
                .orElse(null);
        return CapacitacionEvaluadorDto.builder()
                .id(evaluador.getPracticanteId())
                .nombre(nombre)
                .activo(evaluador.getActivo())
                .notas(evaluador.getNotas())
                .build();
    }

    private void ensureNotCancelled(CapacitacionProgresoEntity progreso) {
        if (progreso.getEstado() == TrainingEstado.CANCELLED) {
            throw new ResourceAlreadyExistsException("Progreso", "estado", TrainingEstado.CANCELLED.toValue());
        }
    }

    private CapacitacionContext loadContext(Integer practicanteId, String cursoNombre, String temaNombre) {
        PracticanteEntity practicante = practicanteRepository.findById(practicanteId)
                .orElseThrow(() -> new ResourceNotFoundException("Practicante no encontrado"));
        CapacitacionCursoEntity curso = cursoRepository.findByNombreIgnoreCase(cursoNombre)
                .orElseThrow(() -> new ResourceNotFoundException("Curso no encontrado"));
        CapacitacionTemaEntity tema = temaRepository.findByCursoAndNombreIgnoreCase(curso, temaNombre)
                .orElseThrow(() -> new BadRequestException("El tema no corresponde al curso indicado"));
        return new CapacitacionContext(practicante, curso, tema);
    }

    private record CapacitacionContext(PracticanteEntity practicante,
                                       CapacitacionCursoEntity curso,
                                       CapacitacionTemaEntity tema) {
    }
}

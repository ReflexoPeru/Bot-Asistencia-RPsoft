---
name: Spring Boot CRUD API
description: Convenciones, arquitectura y buenas prácticas para proyectos Spring Boot con Layered Architecture, JPA, MapStruct, Lombok, Bean Validation y Spring Security + JWT.
---

# Spring Boot CRUD API — Skill Personalizada

## Arquitectura: Layered Architecture

Todos los proyectos Spring Boot deben seguir esta arquitectura por capas:

```
Controller → Service → Repository → Entity
     ↕           ↕
    DTOs       Mappers
```

### Estructura de paquetes obligatoria

```
src/main/java/com/{grupo}/{proyecto}/
├── {Proyecto}Application.java
├── config/           # Configuración de seguridad y beans globales
├── controllers/      # @RestController — solo HTTP, sin lógica de negocio
├── services/         # @Service — lógica de negocio y transacciones
├── repositories/     # JpaRepository — acceso a datos
├── entities/         # @Entity — modelos JPA + Enums
├── dtos/             # DTOs de entrada y salida
├── mappers/          # MapStruct interfaces
└── exceptions/       # Excepciones personalizadas + GlobalExceptionHandler
```

---

## Nomenclatura

| Elemento | Convención | Ejemplo |
|---|---|---|
| Entidades | `{Nombre}Entity` | `EmployeeEntity` |
| Repositorios | `{Nombre}Repository` | `EmployeeRepository` |
| Servicios | `{Nombre}Service` | `EmployeeService` |
| Controladores | `{Nombre}Controller` | `EmployeeController` |
| Mappers | `{Nombre}Mapper` | `EmployeeMapper` |
| DTOs de entrada | `{Nombre}CreateDto` | `EmployeeCreateDto` |
| DTOs de respuesta | `{Nombre}ResponseDto` | `EmployeeResponseDto` |
| Enums | PascalCase sin sufijo | `Department`, `Role` |
| Tablas BD | Nombre singular en `@Table(name = "...")` | `employee`, `branch` |

> **IMPORTANTE**: Mantener coherencia entre el nombre de la entidad y el nombre del repositorio.
> **Correcto**: `EmployeeEntity` → `EmployeeRepository`
> **Incorrecto**: `EmployeeEntity` → `EmployedRepository`

---

## Controllers — Reglas

### Responsabilidades
- Recibir requests HTTP
- Validar entrada con `@Valid`
- Delegar toda lógica al Service
- Construir `ResponseEntity` con el status HTTP correcto
- **NUNCA** contener lógica de negocio

### Convenciones de URLs REST

> **REGLA**: Los URLs deben ser sustantivos (recursos), NUNCA verbos.
> Los métodos HTTP (`GET`, `POST`, `PUT`, `DELETE`) ya expresan la acción.

```java
// ✅ CORRECTO — URLs limpias basadas en recursos
@RestController
@RequestMapping("/api/employees")
@RequiredArgsConstructor
public class EmployeeController {

    @PostMapping                         // POST   /api/employees
    @GetMapping("/{id}")                 // GET    /api/employees/{id}
    @GetMapping("/all")                  // GET    /api/employees/all
    @PutMapping("/{id}")                 // PUT    /api/employees/{id}
    @DeleteMapping("/{id}")              // DELETE /api/employees/{id}
}

// ❌ INCORRECTO — verbos en URLs
@GetMapping("/branch/{id}")    // redundante, ya estás en /api/branches
@PutMapping("/update/{id}")    // "update" es redundante con PUT
@DeleteMapping("/delete/{id}") // "delete" es redundante con DELETE
```

### HTTP Status obligatorios

```java
// CREATE → 201 Created + header Location
@PostMapping
public ResponseEntity<EmployeeResponseDto> create(
        @Valid @RequestBody EmployeeCreateDto dto,
        UriComponentsBuilder ucb) {
    EmployeeResponseDto response = service.create(dto);
    URI location = ucb.path("/api/employees/{id}")
            .buildAndExpand(response.getId())
            .toUri();
    return ResponseEntity.created(location).body(response);
}

// READ → 200 OK
@GetMapping("/{id}")
public ResponseEntity<EmployeeResponseDto> getById(@PathVariable Long id) {
    return ResponseEntity.ok(service.getById(id));
}

// UPDATE → 200 OK
@PutMapping("/{id}")
public ResponseEntity<EmployeeResponseDto> update(
        @PathVariable Long id,
        @Valid @RequestBody EmployeeCreateDto dto) {
    return ResponseEntity.ok(service.update(id, dto));
}

// DELETE → 200 OK con confirmación
@DeleteMapping("/{id}")
public ResponseEntity<DeleteResponseDto> delete(@PathVariable Long id) {
    return ResponseEntity.ok(service.delete(id));
}
```

### Paginación (obligatoria para listados)

> **REGLA**: Todo endpoint que retorne colecciones DEBE soportar paginación.

```java
@GetMapping
public ResponseEntity<Page<EmployeeResponseDto>> getAll(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "10") int size,
        @RequestParam(defaultValue = "id") String sortBy) {
    Pageable pageable = PageRequest.of(page, size, Sort.by(sortBy));
    return ResponseEntity.ok(service.getAll(pageable));
}
```

### Javadoc obligatorio en Controllers

```java
/**
 * Controlador REST para la gestión de empleados.
 * <p>
 * Proporciona endpoints HTTP para realizar operaciones CRUD sobre empleados.
 * Todos los endpoints están bajo la ruta base {@code /api/employees}.
 * </p>
 *
 * @author Nombre Apellido
 * @version 1.0
 * @since yyyy-MM-dd
 * @see EmployeeService
 */
```

---

## Services — Reglas

### Responsabilidades
- Toda la lógica de negocio
- Orquestación entre repositorios
- Gestión transaccional
- Lanzar excepciones de negocio

### Transacciones

```java
@Service
@RequiredArgsConstructor
@Transactional  // Transaccional a nivel de clase (escritura por defecto)
public class EmployeeService {

    // Métodos de solo lectura: override con readOnly = true
    @Transactional(readOnly = true)
    public EmployeeResponseDto getById(Long id) { ... }

    @Transactional(readOnly = true)
    public Page<EmployeeResponseDto> getAll(Pageable pageable) { ... }

    // Métodos de escritura: heredan @Transactional de la clase
    public EmployeeResponseDto create(EmployeeCreateDto dto) { ... }
    public EmployeeResponseDto update(Long id, EmployeeCreateDto dto) { ... }
    public DeleteResponseDto delete(Long id) { ... }
}
```

### Constantes para mensajes de excepción

```java
public static final String ENTITY_NAME = "Empleado";  // Nombre legible del recurso

// Uso:
.orElseThrow(() -> new ResourceNotFoundException(ENTITY_NAME, "ID", id));
```

### Patrón de Service completo

```java
public EmployeeResponseDto create(EmployeeCreateDto dto) {
    // 1. Validar relaciones (buscar entidades relacionadas)
    BranchEntity branch = branchRepository.findById(dto.getBranchId())
            .orElseThrow(() -> new ResourceNotFoundException(BRANCH, "ID", dto.getBranchId()));

    // 2. Mapear DTO → Entity
    EmployeeEntity employee = employeeMapper.toEntity(dto);

    // 3. Establecer relaciones manualmente (ignoradas por MapStruct)
    employee.setBranch(branch);

    // 4. Persistir
    EmployeeEntity saved = employeeRepository.save(employee);

    // 5. Mapear Entity → ResponseDTO y retornar
    return employeeMapper.toResponseDto(saved);
}

public EmployeeResponseDto update(Long id, EmployeeCreateDto dto) {
    // 1. Buscar entidad existente
    EmployeeEntity employee = employeeRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException(ENTITY_NAME, "ID", id));

    // 2. Validar relaciones
    BranchEntity branch = branchRepository.findById(dto.getBranchId())
            .orElseThrow(() -> new ResourceNotFoundException(BRANCH, "ID", dto.getBranchId()));

    // 3. Actualizar in-place con @MappingTarget
    employeeMapper.updateEntity(dto, employee);
    employee.setBranch(branch);

    // 4. Persistir y retornar
    return employeeMapper.toResponseDto(employeeRepository.save(employee));
}

public DeleteResponseDto delete(Long id) {
    EmployeeEntity employee = employeeRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException(ENTITY_NAME, "ID", id));

    employeeRepository.delete(employee);

    return DeleteResponseDto.builder()
            .message("Empleado eliminado exitosamente")
            .id(id)
            .deleted(true)
            .build();
}
```

---

## Entities — Reglas

### Annotations obligatorias

```java
@Getter
@Setter
@Entity
@Table(name = "nombre_tabla")
public class NombreEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    // Campos con constraints explícitos
    @Column(nullable = false, length = 50)
    private String name;

    // Enums como String
    @Enumerated(EnumType.STRING)
    @Column(length = 50, nullable = false)
    private Department department;

    // Monetary con BigDecimal
    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal salary;
}
```

### Timestamps automáticos

```java
@Column(nullable = false)
private LocalDateTime hiringDate;

@PrePersist
protected void onCreate() {
    this.hiringDate = LocalDateTime.now();
}
```

### Relaciones

```java
// Lado propietario (tiene la FK) — usar LAZY siempre
@ManyToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "branch_id", nullable = false)
private BranchEntity branch;

// Lado inverso — cascade + orphanRemoval
@OneToMany(mappedBy = "branch", cascade = CascadeType.ALL, orphanRemoval = true)
private List<EmployeeEntity> employees = new ArrayList<>();
```

> **REGLA**: Usar `@Getter` / `@Setter` en entidades, NUNCA `@Data` (evita problemas con `hashCode`/`equals` y relaciones bidireccionales).

---

## DTOs — Reglas

### DTOs de entrada (Create/Update)

```java
@Data
@AllArgsConstructor
@NoArgsConstructor
public class EmployeeCreateDto {

    @NotNull(message = "El nombre es obligatorio")
    @Length(min = 3, max = 50)
    @Pattern(regexp = "^[a-zA-ZáéíóúÁÉÍÓÚñÑ\\s]+$",
             message = "Solo puede contener letras y espacios")
    private String name;

    @NotNull(message = "El email es obligatorio")
    @Email(message = "Email inválido")
    private String email;

    @NotNull(message = "El salario es obligatorio")
    @Positive(message = "El salario debe ser positivo")
    @DecimalMax(value = "999999.99", message = "El salario es demasiado alto")
    private BigDecimal salary;

    @NotNull(message = "La sucursal es obligatoria")
    @Positive(message = "ID de sucursal inválido")
    private Long branchId;
}
```

### DTOs de respuesta (inmutables)

```java
@Value  // Hace todos los campos final, genera getters, equals, hashCode, toString
public class EmployeeResponseDto {
    Long id;
    String name;
    String lastName;
    String email;
    LocalDateTime hiringDate;
    Department department;
    BigDecimal salary;
    BranchResponseDto branch;
}
```

### DTO genérico de eliminación

```java
@Data
@Builder
public class DeleteResponseDto {
    @Builder.Default
    private String message = "Eliminación exitosa";
    private Long id;
    private Boolean deleted;
}
```

> **REGLA**: DTOs de respuesta SIEMPRE con `@Value` (inmutables). DTOs de entrada con `@Data`.

---

## Mappers (MapStruct) — Reglas

### Estructura de cada Mapper

Cada mapper DEBE tener al menos tres métodos:

```java
@Mapper(componentModel = "spring", uses = {OtroMapper.class})  // uses solo si necesita mappers anidados
public interface EmployeeMapper {

    // 1. DTO → Entity (ignora campos auto-generados y relaciones)
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "hiringDate", ignore = true)
    @Mapping(target = "branch", ignore = true)
    EmployeeEntity toEntity(EmployeeCreateDto dto);

    // 2. Entity → ResponseDTO (mapea todo, incluyendo relaciones anidadas)
    EmployeeResponseDto toResponseDto(EmployeeEntity entity);

    // 3. Update in-place con @MappingTarget (ignora id y campos inmutables)
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "hiringDate", ignore = true)
    @Mapping(target = "branch", ignore = true)
    void updateEntity(EmployeeCreateDto dto, @MappingTarget EmployeeEntity entity);
}
```

### Build config para Lombok + MapStruct

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <configuration>
        <annotationProcessorPaths>
            <path>
                <groupId>org.projectlombok</groupId>
                <artifactId>lombok</artifactId>
            </path>
            <path>
                <groupId>org.mapstruct</groupId>
                <artifactId>mapstruct-processor</artifactId>
                <version>1.6.3</version>
            </path>
            <path>
                <groupId>org.projectlombok</groupId>
                <artifactId>lombok-mapstruct-binding</artifactId>
                <version>0.2.0</version>
            </path>
        </annotationProcessorPaths>
    </configuration>
</plugin>
```

---

## Excepciones — Reglas

### Excepciones personalizadas obligatorias

```java
// 404 — Recurso no encontrado
public class ResourceNotFoundException extends RuntimeException {
    public ResourceNotFoundException(String message) {
        super(message);
    }
    public ResourceNotFoundException(String resource, String field, Object value) {
        super(String.format("%s no encontrado con %s: '%s'", resource, field, value));
    }
}

// 409 — Recurso ya existe
public class ResourceAlreadyExistsException extends RuntimeException {
    public ResourceAlreadyExistsException(String resource, String field, Object value) {
        super(String.format("%s ya existe con %s: '%s'", resource, field, value));
    }
}

// 400 — Bad Request genérico
public class BadRequestException extends RuntimeException {
    public BadRequestException(String message) {
        super(message);
    }
}
```

### GlobalExceptionHandler obligatorio

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    // 404
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleResourceNotFound(
            ResourceNotFoundException ex, HttpServletRequest request) { ... }

    // 400
    @ExceptionHandler(BadRequestException.class)
    public ResponseEntity<ErrorResponse> handleBadRequest(
            BadRequestException ex, HttpServletRequest request) { ... }

    // 400 — Errores de validación de Bean Validation
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidationErrors(
            MethodArgumentNotValidException ex, HttpServletRequest request) { ... }

    // 409
    @ExceptionHandler(ResourceAlreadyExistsException.class)
    public ResponseEntity<ErrorResponse> handleResourceAlreadyExists(
            ResourceAlreadyExistsException ex, HttpServletRequest request) { ... }

    // 500 — Catch-all (loguea error, retorna mensaje genérico)
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGenericException(
            Exception ex, HttpServletRequest request) {
        log.error("Error inesperado {} : {}", request.getRequestURI(), ex.getMessage(), ex);
        // NUNCA exponer stack traces al cliente
        ...
    }
}
```

### Estructura ErrorResponse estandarizada

```java
@Data
@Builder
public class ErrorResponse {
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "dd-MM-yy hh:mm:ss")
    private LocalDateTime timestamp;
    private int status;
    private String error;
    private String message;
    private String path;
    private List<ValidationError> validationErrors;  // null si no es error de validación

    @Data
    @Builder
    public static class ValidationError {
        private String field;
        private String message;
    }
}
```

---

## Seguridad (Spring Security + JWT) — Reglas

### Configuración base

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
@RequiredArgsConstructor
public class WebSecurityConfiguration {

    private final JwtAuthenticationFilter jwtAuthFilter;  // OBLIGATORIO
    private final UserDetailsService userDetailsService;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**").permitAll()
                .anyRequest().authenticated())
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authenticationProvider(authenticationProvider())
            // ⚠️ OBLIGATORIO: Registrar el filtro JWT antes de UsernamePasswordAuthenticationFilter
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
```

### JWT Filter obligatorio

> **REGLA**: Si usas JWT + STATELESS, DEBES implementar un `JwtAuthenticationFilter`.

```java
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtService jwtService;
    private final UserDetailsService userDetailsService;

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {

        final String authHeader = request.getHeader("Authorization");

        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            filterChain.doFilter(request, response);
            return;
        }

        final String jwt = authHeader.substring(7);
        final String userEmail = jwtService.extractUsername(jwt);

        if (userEmail != null && SecurityContextHolder.getContext().getAuthentication() == null) {
            UserDetails userDetails = userDetailsService.loadUserByUsername(userEmail);

            if (jwtService.isTokenValid(jwt, userDetails)) {
                UsernamePasswordAuthenticationToken authToken =
                        new UsernamePasswordAuthenticationToken(
                                userDetails, null, userDetails.getAuthorities());
                authToken.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                SecurityContextHolder.getContext().setAuthentication(authToken);
            }
        }
        filterChain.doFilter(request, response);
    }
}
```

### AuthController obligatorio

> **REGLA**: Si tienes `/api/auth/**` como permitAll, DEBES tener un AuthController con endpoints de login y registro.

```java
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/register")
    public ResponseEntity<AuthResponseDto> register(
            @Valid @RequestBody RegisterRequestDto dto) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(authService.register(dto));
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponseDto> login(
            @Valid @RequestBody LoginRequestDto dto) {
        return ResponseEntity.ok(authService.login(dto));
    }

    @PostMapping("/refresh-token")
    public ResponseEntity<AuthResponseDto> refreshToken(
            @Valid @RequestBody RefreshTokenRequestDto dto) {
        return ResponseEntity.ok(authService.refreshToken(dto));
    }
}
```

### UsersEntity implementa UserDetails

```java
@Getter
@Setter  // Usar @Getter/@Setter, NO @Data
@Entity
@Table(name = "users")
public class UsersEntity implements UserDetails {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 50)
    private String firstName;

    @Column(nullable = false, length = 50)
    private String lastName;

    @Column(nullable = false, length = 50, unique = true)
    private String email;

    @Column(nullable = false)
    private String password;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Role role;

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return List.of(new SimpleGrantedAuthority("ROLE_" + role.name()));
    }

    @Override
    public String getUsername() {
        return email;
    }

    // isAccountNonExpired, isAccountNonLocked, etc → return true
}
```

---

## Inyección de Dependencias — Reglas

```java
// ✅ CORRECTO — Constructor injection con Lombok
@RequiredArgsConstructor
public class EmployeeService {
    private final EmployeeRepository employeeRepository;  // SIEMPRE final
    private final EmployeeMapper employeeMapper;
}

// ❌ INCORRECTO — Field injection
@Autowired
private EmployeeRepository employeeRepository;  // NUNCA usar @Autowired
```

---

## Configuración y Entorno — Reglas

### Variables de entorno

```properties
# application.properties — NUNCA hardcodear credenciales
spring.datasource.url=${DB_URL}
spring.datasource.username=${DB_USERNAME}
spring.datasource.password=${DB_PASSWORD}
spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=true
```

### .gitignore — el `.env` SIEMPRE debe estar incluido

```gitignore
# Environment
.env
.env.local
.env.production
```

### Docker Compose para desarrollo

```yaml
services:
  postgres:
    image: 'postgres:latest'
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_USER=${DB_USERNAME}
    ports:
      - '5432:5432'
```

### Migraciones en producción

> **REGLA**: `spring.jpa.hibernate.ddl-auto=update` es aceptable SOLO en desarrollo.
> En producción, usar Flyway o Liquibase para controlar cambios de esquema.

---

## Javadoc — Reglas

### Idioma: Español

Todo el Javadoc se escribe en **español**.

### Etiquetas obligatorias

| Etiqueta | Dónde | Descripción |
|---|---|---|
| `@author` | Clases | Nombre del autor |
| `@version` | Clases | Versión del componente |
| `@since` | Clases | Fecha de creación `yyyy-MM-dd` |
| `@see` | Clases | Referencias a clases relacionadas |
| `@param` | Métodos | Descripción de cada parámetro |
| `@return` | Métodos | Descripción del valor de retorno |
| `@throws` | Métodos | Cada excepción que puede lanzar |

### Plantilla de clase

```java
/**
 * Breve descripción de la clase.
 * <p>
 * Descripción detallada con contexto adicional.
 * </p>
 *
 * @author Nombre Apellido
 * @version 1.0
 * @since yyyy-MM-dd
 * @see ClaseRelacionada
 */
```

### Plantilla de método

```java
/**
 * Breve descripción del método.
 * <p>
 * Detalles adicionales si son necesarios.
 * </p>
 *
 * @param id identificador único del recurso
 * @return datos completos del recurso encontrado
 * @throws ResourceNotFoundException si no existe el recurso con el ID especificado
 */
```

> **REGLA**: Todas las clases públicas y métodos públicos DEBEN tener Javadoc completo. Sin excepciones.

---

## Reglas de Ortografía y Consistencia

1. **Endpoints sin typos**: Revisar todos los strings de rutas antes de commit
2. **Mensajes de error coherentes**: "no encontrado con", "ya existe con"
3. **Constantes para nombres de recurso**: `public static final String ENTITY_NAME = "Empleado";`
4. **Mensajes de validación siempre en español**: `@NotNull(message = "El nombre es obligatorio")`

---

## Checklist para nuevas entidades de dominio

Al agregar una nueva entidad al proyecto, crear SIEMPRE los siguientes archivos:

- [ ] `entities/{Nombre}Entity.java` — Entidad JPA con Javadoc
- [ ] `repositories/{Nombre}Repository.java` — Interface JpaRepository
- [ ] `dtos/{Nombre}CreateDto.java` — DTO de entrada con validaciones
- [ ] `dtos/{Nombre}ResponseDto.java` — DTO de respuesta inmutable (`@Value`)
- [ ] `mappers/{Nombre}Mapper.java` — MapStruct con `toEntity`, `toResponseDto`, `updateEntity`
- [ ] `services/{Nombre}Service.java` — Service con `@Transactional` y Javadoc
- [ ] `controllers/{Nombre}Controller.java` — Controller con URLs REST limpias y paginación
- [ ] Tests unitarios para el Service
- [ ] Tests de integración para el Controller

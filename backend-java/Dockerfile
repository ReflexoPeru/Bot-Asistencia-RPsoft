# ==============================================================
# Build stage
# ==============================================================
FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app

# Copiar Maven wrapper y pom.xml primero (cachear dependencias)
COPY .mvn/ .mvn/
COPY mvnw pom.xml ./
RUN chmod +x mvnw && ./mvnw dependency:go-offline -B

# Copiar el código fuente y compilar
COPY src/ src/
RUN ./mvnw clean package -DskipTests -B

# ==============================================================
# Runtime stage
# ==============================================================
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

# Copiar el JAR generado
COPY --from=build /app/target/*.jar app.jar

# Timezone
ENV TZ=America/Lima
RUN apk add --no-cache tzdata

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]

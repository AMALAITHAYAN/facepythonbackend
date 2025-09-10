# Use a JDK image to build the app
FROM maven:3.9.4-eclipse-temurin-17 AS build
WORKDIR /app
COPY . .
RUN mvn clean package -DskipTests

# Use a lightweight JRE image to run the app
FROM eclipse-temurin:17-jdk
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar

# Expose the port (Spring Boot default is 8080)
EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
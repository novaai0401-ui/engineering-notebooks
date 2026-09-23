FROM node:24-alpine AS ui
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app
COPY java/pom.xml ./
COPY java/src ./src
COPY --from=ui /src/java/src/main/resources/static ./src/main/resources/static
RUN mvn -B -ntp -DskipTests package
FROM eclipse-temurin:21-jre
WORKDIR /app
RUN mkdir /data && chown 10001:10001 /data
COPY --from=build /app/target/study-coach-1.0.0.jar /app/coach.jar
USER 10001:10001
ENV SERVER_ADDRESS=0.0.0.0 COACH_DB=jdbc:h2:file:/data/coach
EXPOSE 8091
ENTRYPOINT ["java","-jar","/app/coach.jar"]

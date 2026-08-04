FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn package -DskipTests -B

FROM eclipse-temurin:17-jre-jammy
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8080
# -TieredStopAtLevel=1: skip the C2 JIT compiler entirely -- it exists to
#   optimize long-running hot loops, which this short-lived-per-cold-start
#   process never benefits from; skipping it is the single biggest lever
#   for JVM startup time.
# -Xshare:auto: use Class Data Sharing if the base image has an archive,
#   skips re-parsing core class files on every boot.
# -XX:+UseSerialGC: lower init overhead than the default G1 collector, and
#   appropriate for a small heap on a single-core free-tier instance.
# -Xmx256m -Xms128m: explicit modest heap so the JVM doesn't spend time
#   probing/negotiating a heap size against the container's cgroup limits.
ENTRYPOINT ["java", "-XX:TieredStopAtLevel=1", "-Xshare:auto", "-XX:+UseSerialGC", "-Xmx256m", "-Xms128m", "-jar", "app.jar"]

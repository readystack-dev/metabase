# GENERATED L-009 hermetic Java build (--network=none, SBOM+SLSA-attestation-producing).
# Pinned bases; vendored source + clojure cache(s) + toolchain/runtime debs from Dockerfile.vendor.
FROM eclipse-temurin:25-jdk-noble@sha256:589ff4cc3f71aab462e7048a47a0d10edf57fbccde3fceea2281e610bf5880b4 AS jbuild
# dpkg-install the vendored build toolchain (git/unzip) — no apt, fully offline.
RUN --mount=type=bind,source=vendored/build-debs,target=/tmp/bdebs \
    set --; for f in /tmp/bdebs/*.deb; do [ -e "$f" ] && set -- "$@" "$f"; done; \
    for pass in 1 2 3 4 5; do [ $# -eq 0 ] || dpkg -i --skip-same-version "$@" >/dev/null 2>&1 && break; done; \
    dpkg --configure -a && bad= && for d in "$@"; do p=$(dpkg-deb -f "$d" Package) v=$(dpkg-deb -f "$d" Version); \
      case "$(dpkg-query -W -f='${Version} ${db:Status-Abbrev}' "$p" 2>/dev/null)" in "$v ii"*) ;; *) bad="$bad $p=$v" ;; esac; done && \
    { [ -z "$bad" ] || { echo "vendored debs not installed at their vendored version:$bad" >&2; false; }; }
WORKDIR /src
COPY vendored/metabase-src/ .
COPY vendored/caches/opt/node/ /opt/node/
COPY vendored/caches/opt/clojure/ /opt/clojure/
COPY vendored/caches/root/.m2/repository/ /root/.m2/repository/
COPY vendored/caches/root/.gitlibs/ /root/.gitlibs/
ENV PATH="/opt/node/bin:/opt/clojure/bin:/root/.local/bin:$PATH"
ENV MB_EDITION="oss"
ENV INTERACTIVE="false"
ENV HUSKY="0"
ENV CYPRESS_INSTALL_BINARY="0"
COPY kitforge-cljdeps.py /kitforge-cljdeps.py
RUN python3 /kitforge-cljdeps.py hashagent /kitforge-namehash.jar
RUN python3 /kitforge-cljdeps.py shadowdet shadow-cljs.edn /kitforge-namehash.jar
ENV JAVA_TOOL_OPTIONS="-XX:+UnlockExperimentalVMOptions -XX:hashCode=2 -javaagent:/kitforge-namehash.jar=reflect:clojure/,dirsort"
RUN CI=true bin/build.sh :edition :oss :version '"v0.65.7.4"' :steps '[:translations :frontend :licenses :uberjar]'
RUN mkdir -p /app && cp target/uberjar/metabase.jar /app/metabase.jar && ls -l /app/metabase.jar
ARG SOURCE_DATE_EPOCH=1795849182
RUN python3 /kitforge-cljdeps.py normalize /app "$SOURCE_DATE_EPOCH"
RUN rm -f /kitforge-cljdeps.py /kitforge-namehash.jar
FROM eclipse-temurin:25-jre-noble@sha256:f3dd0838e69b881cc382237d5901e74ae3705b1056ad964b2e0e523b174fef99
ENV DEBIAN_FRONTEND=noninteractive MB_JETTY_HOST=0.0.0.0 MB_JETTY_PORT=3000 MB_DB_TYPE=h2 MB_DB_FILE=/metabase-data/metabase.db MB_PLUGINS_DIR=/plugins FC_LANG=en-US LC_CTYPE=en_US.UTF-8
RUN --mount=type=bind,source=vendored/debs,target=/tmp/debs \
    set --; for f in /tmp/debs/*.deb; do [ -e "$f" ] && set -- "$@" "$f"; done; \
    for pass in 1 2 3 4 5; do [ $# -eq 0 ] || dpkg -i --skip-same-version "$@" >/dev/null 2>&1 && break; done; \
    dpkg --configure -a && bad= && for d in "$@"; do p=$(dpkg-deb -f "$d" Package) v=$(dpkg-deb -f "$d" Version); \
      case "$(dpkg-query -W -f='${Version} ${db:Status-Abbrev}' "$p" 2>/dev/null)" in "$v ii"*) ;; *) bad="$bad $p=$v" ;; esac; done && \
    { [ -z "$bad" ] || { echo "vendored debs not installed at their vendored version:$bad" >&2; false; }; } && \
    rm -rf /var/lib/apt/lists/* \
           /var/log/dpkg.log /var/log/alternatives.log /var/log/apt /var/cache/ldconfig/aux-cache /var/cache/fontconfig
ARG SOURCE_DATE_EPOCH=1795849182
RUN groupadd -r metabase && useradd -r -g metabase -d /app -m metabase && \
    : "${SOURCE_DATE_EPOCH:?SOURCE_DATE_EPOCH must be set for a reproducible build}" && \
    sed -ri "s/^([^:]*:[^:]*):[0-9]*:/\1:$((SOURCE_DATE_EPOCH/86400)):/" /etc/shadow && \
    rm -f /etc/passwd- /etc/shadow- /etc/group- /etc/gshadow-
COPY --from=jbuild /app /app
RUN mkdir -p /metabase-data /app/target /plugins && chown -R metabase:metabase /metabase-data /app/target /plugins
LABEL org.opencontainers.image.licenses="AGPL-3.0"
LABEL org.opencontainers.image.title="Metabase"
LABEL org.opencontainers.image.source="https://github.com/readystack-dev/metabase"
LABEL org.opencontainers.image.url="https://readystack.dev/products/metabase"
LABEL org.opencontainers.image.version="v0.65.7.4-CE-ubuntu24.04-r1"
LABEL org.opencontainers.image.description="Metabase Community Edition — open-source business intelligence and analytics (dashboards, questions, SQL) on a self-contained JVM uberjar"
LABEL org.opencontainers.image.vendor="ReadyStack.dev"
LABEL com.readystack.license.disclosure="This image includes Metabase (https://github.com/metabase/metabase), Community/OSS edition, licensed under AGPL-3.0 (all source outside the upstream top-level enterprise/ directory). The proprietary enterprise/ subtree (Metabase Commercial License) is EXCLUDED from this build (MB_EDITION=oss; the :ee classpath is never used; enterprise/ and LICENSE-MCL.txt are removed). Modifications: shadow-cljs.edn compiles the ClojureScript frontend serially (:parallel-build false) and loads ReadyStack's build-time JSChunk name-hash agent through :jvm-opts, so the frontend bundle reproduces; deps.edn is not changed; full diff at https://readystack.dev/source/metabase/v0.65.7.4/metabase-v0.65.7.4-readystack.patch. Other security patches are applied only via vendored updates to upstream-published Clojure/Maven and apt dependencies (unmodified). ReadyStack license holders have access to the image build recipe and patched-package manifest on request via contact@readystack.dev."
LABEL org.opencontainers.image.revision="615478ea918fa1488412a846f0380609d7f3d54b"
LABEL readystack.upstream.source="https://github.com/metabase/metabase"
LABEL readystack.upstream.url="https://www.metabase.com/"
LABEL org.opencontainers.image.documentation="https://github.com/readystack-dev/metabase#readme"
LABEL org.opencontainers.image.authors="ReadyStack <contact@readystack.dev>"
LABEL readystack.upstream.vendor="Metabase"
HEALTHCHECK --interval=5s --timeout=120s --start-period=90s \
  CMD curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/api/health || exit 1
WORKDIR /app
USER metabase
EXPOSE 3000
ENTRYPOINT ["java", "-XX:+IgnoreUnrecognizedVMOptions", "-Dfile.encoding=UTF-8", "-Dlogfile.path=/app/target/log", "-XX:+CrashOnOutOfMemoryError", "-server", "--add-opens", "java.base/java.nio=ALL-UNNAMED", "--enable-native-access=ALL-UNNAMED", "-jar", "/app/metabase.jar"]

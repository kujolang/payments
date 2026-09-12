# Platform-specific official base digest avoids a mutable tag and multiarch ambiguity.
FROM ubuntu@sha256:1e0a86e57d247923571b75e0aaf48a1449cf8c543d51fb3e07a4a7d7bfa79316 AS runtime
COPY deployment/.runtime/kujo /usr/local/bin/kujo
RUN echo '1c7f960df366f213146577fefa0c5e8ec3a1581dab822356c4e3ca295334c26c  /usr/local/bin/kujo' | sha256sum -c -
WORKDIR /app
USER 65532:65532

FROM runtime AS gateway
COPY --chown=65532:65532 src /app/src
COPY --chown=65532:65532 contracts /app/contracts
COPY --chown=65532:65532 kennel.toml kennel.lock /app/
COPY --chown=65532:65532 kennel_packages/ability /app/kennel_packages/ability
ENTRYPOINT ["/usr/local/bin/kujo", "run", "src/executor/gateway.kujo", "--interpreter"]

FROM runtime AS agent-probe
COPY --chown=65532:65532 src/client /app/src/client
COPY --chown=65532:65532 tests/network/agent_probe.kujo /app/probe.kujo
ENTRYPOINT ["/usr/local/bin/kujo", "run", "/app/probe.kujo", "--interpreter"]

FROM runtime AS harness-probe
COPY --chown=65532:65532 tests/network/harness.kujo /app/harness.kujo
ENTRYPOINT ["/usr/local/bin/kujo", "run", "/app/harness.kujo", "--interpreter"]

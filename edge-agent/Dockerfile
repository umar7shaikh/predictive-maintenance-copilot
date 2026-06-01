# Multi-stage build. The agent is plain-HTTP + pure Rust (no TLS/C deps), so it
# compiles on the default toolchain and runs on a slim Debian base.
FROM rust:1-slim AS build
WORKDIR /app
COPY Cargo.toml ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
RUN useradd -r -u 10001 edge
COPY --from=build /app/target/release/pdm-edge-agent /usr/local/bin/pdm-edge-agent
USER edge
ENTRYPOINT ["pdm-edge-agent"]

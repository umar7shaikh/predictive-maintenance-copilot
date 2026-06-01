# Multi-stage build -> tiny static, non-root distroless image.
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY *.go ./
# Stdlib only, so no module download is needed. Static binary (CGO off).
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /gateway .

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /gateway /gateway
EXPOSE 8080
ENTRYPOINT ["/gateway"]

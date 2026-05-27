# Multi-stage: сборка в golang, запуск в distroless
FROM golang:1.22-alpine AS builder
WORKDIR /app

# Зависимости отдельным слоем для кеша
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-w -s" \
    -o collector \
    ./cmd/collector

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=builder /app/collector .
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/app/collector"]

FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-w -s" \
    -o arrowsrv \
    ./cmd/arrowsrv

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=builder /app/arrowsrv .
EXPOSE 8815
USER nonroot:nonroot
ENTRYPOINT ["/app/arrowsrv"]

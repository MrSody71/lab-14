FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o mockowm ./cmd/mockowm

FROM alpine:3.19
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /app/mockowm .
EXPOSE 8081
ENV MOCK_OWM_ADDR=":8081"
CMD ["./mockowm"]

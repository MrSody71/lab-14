# Промт 09-11: govet shadow + staticcheck SA1019

## Задача

Починить оставшиеся 2 ошибки golangci-lint после упрощения конфига
(промт 09-10).

## Диагностика

Установлен golangci-lint v1.64.8 (совместим с Go 1.26.2),
запущен с новым `.golangci.yml`:

```
go-collector/cmd/collector/main.go:93:7:
  shadow: declaration of "err" shadows declaration at line 52 (govet)

arrow-server/cmd/arrowsrv/main.go:76:9:
  SA1019: flight.NewFlightServer is deprecated: prefer to use
  NewServerWithMiddleware (staticcheck)
```

## ОШИБКА 1 — govet shadow в collector/main.go

В горутине `go func() { if err := ... }()` переменная `err` объявлена
через `:=`, хотя внешний `err` со строки 52 уже существует в scope.

**Исправление:** переименовать inner-переменную:

```go
// было:
if err := shardManager.Register(ctx); err != nil {
    logger.Warn("shard register ended", "err", err)
}

// стало:
if regErr := shardManager.Register(ctx); regErr != nil {
    logger.Warn("shard register ended", "err", regErr)
}
```

## ОШИБКА 2 — staticcheck SA1019 в arrowsrv/main.go

`flight.NewFlightServer()` deprecated в apache/arrow-go v17.
Нужно использовать `flight.NewServerWithMiddleware(nil)`.

**Исправление:**

```go
// было:
srv := flight.NewFlightServer()

// стало:
srv := flight.NewServerWithMiddleware(nil)
```

API идентичен — оба возвращают `*flight.Server`.

## Результат (2026-05-29)

```
golangci-lint run ./go-collector/... ./arrow-server/... ./mock-owm/...
(no output — 0 issues)  ✅

go build ./...  ✅
go test ./...   all packages pass  ✅
```

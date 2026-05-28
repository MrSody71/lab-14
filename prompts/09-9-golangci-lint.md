# Промт 09-9: golangci-lint fix

## Задача

Починить последнюю ошибку CI: job "go" → step "Lint" падает
с 10 ошибками от golangci-lint v1.61.0.

## Диагностика

golangci-lint v1.61.0 на Ubuntu с Go 1.22. Конфиг `.golangci.yml`
включает: govet, staticcheck, errcheck, revive, gocyclo, unused,
ineffassign, gosec.

10 ошибок = 5 мест × 2 линтера (errcheck + gosec G104) —
каждый необработанный defer Close() репортится дважды.

## Причина

Паттерн `defer someCloser.Close()` репортится двумя линтерами:
- **errcheck**: "Error return value of `Close` is not checked"
- **gosec G104**: "Errors unhandled"

Пять конкретных мест:

| Файл | Строка | Вызов |
|------|--------|-------|
| `go-collector/internal/api/client.go` | 47 | `defer resp.Body.Close()` |
| `go-collector/internal/api/client.go` | 81 | `defer resp.Body.Close()` |
| `arrow-server/cmd/arrowsrv/main.go`   | 93 | `defer consumer.Close()` |
| `arrow-server/cmd/arrowsrv/main.go`   | 100 | `defer partConsumer.Close()` |
| `arrow-server/internal/flight.go`     | 113 | `defer writer.Close()` |

## Исправление

Заменить каждый голый `defer x.Close()` на явный discard:

```go
// было:
defer resp.Body.Close()

// стало:
defer func() { _ = resp.Body.Close() }()
```

`_ =` показывает линтерам что ошибка намеренно проигнорирована
(fire-and-forget при завершении HTTP-запроса / закрытии потока).

Изменённые файлы:
- `go-collector/internal/api/client.go` — 2 правки
- `arrow-server/cmd/arrowsrv/main.go` — 2 правки
- `arrow-server/internal/flight.go` — 1 правка

## Проверка (2026-05-28)

```
=== go build ===
build OK  ✅

=== go test ===
ok  mock-owm/internal         0.800s  ✅
ok  arrow-server/internal     0.107s  ✅
ok  go-collector/internal/api 2.813s  ✅
ok  go-collector/internal/... (все пакеты)  ✅
```

golangci-lint запускается только на CI (Go 1.26.2 локально несовместим
с golangci-lint v1.61.0 — "unsupported version: 2").

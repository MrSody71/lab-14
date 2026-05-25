# Промт 0.3 — Go workspace

Прочитай CLAUDE.md, оттуда возьми USERNAME для module path.

Создай Go workspace и три модуля-заглушки.

ЗАДАЧИ:

1. В корне репозитория: go.work
   go 1.22
   use (
       ./go-collector
       ./arrow-server
       ./mock-owm
   )

2. go-collector/go.mod
   module github.com/<USERNAME>/weather-pipeline/go-collector
   go 1.22

3. arrow-server/go.mod
   module github.com/<USERNAME>/weather-pipeline/arrow-server
   go 1.22

4. mock-owm/go.mod
   module github.com/<USERNAME>/weather-pipeline/mock-owm
   go 1.22

5. Три main.go заглушки, каждая печатает имя и версию через log.Println:

   go-collector/cmd/collector/main.go:
   package main
   import "log"
   const version = "0.0.0"
   func main() { log.Printf("go-collector v%s starting", version) }

   arrow-server/cmd/arrowsrv/main.go:
   package main
   import "log"
   const version = "0.0.0"
   func main() { log.Printf("arrow-server v%s starting", version) }

   mock-owm/cmd/mockowm/main.go:
   package main
   import "log"
   const version = "0.0.0"
   func main() { log.Printf("mock-owm v%s starting", version) }

6. Удали .gitkeep в тех каталогах, где теперь лежит main.go или go.mod.

7. .golangci.yml в корне:
   run:
     timeout: 5m
   linters:
     enable:
       - govet
       - staticcheck
       - errcheck
       - revive
       - gocyclo
       - unused
       - ineffassign
       - gosec
   linters-settings:
     gocyclo:
       min-complexity: 15

ПРОВЕРКА (выполни последовательно, покажи мне вывод КАЖДОЙ команды):
  go work sync
  go build ./go-collector/...
  go build ./arrow-server/...
  go build ./mock-owm/...
  go run ./go-collector/cmd/collector
  go run ./arrow-server/cmd/arrowsrv
  go run ./mock-owm/cmd/mockowm

Все три должны напечатать строку "starting" и завершиться с кодом 0.

Если установлен golangci-lint, дополнительно запусти:
  golangci-lint run ./...
(если не установлен — пропусти молча).

prompts/00-3-go-workspace.md — этот промт целиком.

В конце: git status.

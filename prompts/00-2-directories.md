# Промт 0.2 — Структура каталогов

Прочитай CLAUDE.md.

Создай ТОЛЬКО структуру каталогов с .gitkeep файлами. Никакого кода,
конфигов, манифестов на этом шаге.

КАТАЛОГИ (создай через mkdir -p, в каждом — пустой .gitkeep):

go-collector/cmd/collector
go-collector/internal/api
go-collector/internal/shard
go-collector/internal/window
go-collector/internal/sink
go-collector/internal/metrics
go-collector/internal/config
go-collector/pkg

arrow-server/cmd/arrowsrv
arrow-server/internal

mock-owm/cmd/mockowm
mock-owm/internal

rust-validator/src
rust-validator/tests

py-analyzer/src/analyzer
py-analyzer/tests
py-analyzer/notebooks

py-asyncio-collector/src

dashboard/

k8s/base
k8s/overlays/dev
k8s/overlays/prod

bench/scenarios
bench/results
bench/plots

docs/screenshots
docs/diagrams

prompts/

ПРОВЕРКА:
tree -L 3 -I '.git' покажи мне результат. Должно быть видно все каталоги,
в каждом по одному .gitkeep.

Затем создай prompts/00-2-directories.md с этим промтом целиком.

В конце: git status (должно быть много новых .gitkeep файлов).

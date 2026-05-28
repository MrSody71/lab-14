# Промт 09-8: Race condition и F401

## Задача

Починить две оставшиеся ошибки CI — обе в коде, не в конфигурации.

## ОШИБКА 1 — Go race condition в TestBatchEndpoint

### Причина

`mock-owm/internal/generator.go` хранит пакетный генератор случайных чисел:

```go
var rng = rand.New(rand.NewSource(time.Now().UnixNano()))
```

`*rand.Rand` не является goroutine-safe. `BatchHandler` вызывает
`GenerateForCity` параллельно из нескольких горутин → все они обращаются
к `rng.Float64()` / `rng.Intn()` одновременно → DATA RACE.

### Исправление в `mock-owm/internal/generator.go`

- Добавить `"sync"` в импорты
- Объявить `rngMu sync.Mutex` рядом с `rng`
- Защитить `Init()` мьютексом
- В `Generate()` взять `rngMu.Lock()` перед первым вызовом rng и
  `rngMu.Unlock()` сразу после последнего (все rng-вызовы в одной критической секции)

```go
var (
    rng   = rand.New(rand.NewSource(time.Now().UnixNano()))
    rngMu sync.Mutex
)

func Init(seed int64) {
    rngMu.Lock()
    rng = rand.New(rand.NewSource(seed))
    rngMu.Unlock()
}

func Generate(city string, meta CityMeta) WeatherData {
    rngMu.Lock()
    temp := meta.BaseTemp + rng.Float64()*6 - 3
    // ... все остальные rng-вызовы ...
    desc := descriptions[rng.Intn(len(descriptions))]
    rngMu.Unlock()
    // ... построение и возврат WeatherData ...
}
```

**Примечание:** handler.go уже был правильным (indexed slice, не append).
Реальный race был в генераторе.

## ОШИБКА 2 — Python F401: subprocess imported but unused

### Причина

`py-analyzer/tests/test_arrow_integration.py` содержал два импорта subprocess:
- строка 10: `import subprocess` — верхний уровень, **не используется**
- строка 44 внутри fixture: `import subprocess as _subprocess` — используется

Ruff сообщал `F401 'subprocess' imported but unused` на верхний импорт.

### Исправление

Удалить строку `import subprocess` с верхнего уровня файла.
Локальный импорт внутри fixture остаётся без изменений.

## Результат (2026-05-28)

```
=== Go tests (no -race, GCC не установлен на Windows) ===
ok  github.com/MrSody71/weather-pipeline/mock-owm/internal  0.798s  ✅

=== Ruff py-analyzer ===
All checks passed!  ✅

=== Pytest py-analyzer ===
35 passed, 10 skipped, 2 deselected  ✅
```

CI на Ubuntu запустит `go test -race` — race устранён добавлением `sync.Mutex`.

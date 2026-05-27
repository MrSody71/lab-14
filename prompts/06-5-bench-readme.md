Создай bench/README.md с описанием результатов бенчмарка.

=== bench/README.md ===

Структура файла:

# Benchmark: Go vs Python asyncio

## Методология

Раздел описывает:
- Что измеряем: throughput (req/s), latency percentiles (P50/P95/P99)
- Тестовое окружение: мок-сервер OWM, 10 городов, N раундов
- Параметры: BENCH_ROUNDS, BENCH_CONCURRENCY
- Как запустить самому: блок кода с командами

## Результаты

Вставь сюда реальные числа из bench/results/*.json:
- Таблицу сравнения Go vs Python asyncio
- Вывод: кто быстрее и насколько (throughput ratio)

## Графики

Вставь ссылки на 4 PNG в bench/plots/:
  ![Throughput](plots/throughput.png)
  ![Latency Percentiles](plots/latency_percentiles.png)
  ![Success Rate](plots/success_rate.png)
  ![Summary](plots/summary_card.png)

## Анализ

3-4 параграфа:

1. Почему Go быстрее по throughput:
   горутины легче goroutine-stack (~2KB) vs Python coroutine +
   GIL + asyncio overhead. Go HTTP-клиент без GIL.

2. Почему Python asyncio всё равно достойный результат:
   aiohttp + asyncio убирает I/O-блокировки, GIL не мешает
   при HTTP-запросах (I/O bound). Python хорош для прототипа.

3. Latency: у обоих p95 низкий т.к. мок-сервер локальный.
   В реальном окружении с сетевой задержкой разница сгладится.

4. Вывод: Go для production-сборщика где важен throughput,
   Python asyncio — для быстрого прототипа или аналитического
   коллектора где throughput менее критичен.

## Воспроизведение

Блок кода с полными командами для запуска бенчмарка с нуля.

После создания README — добавь ссылку на него из корневого
README.md в раздел ## Бенчмарки.

ПРОВЕРКА:
  cat bench/README.md | wc -l
  # должно быть > 40 строк

  grep -c "png" bench/README.md
  # должно быть >= 4 ссылки на изображения

prompts/06-5-bench-readme.md — этот промт целиком.

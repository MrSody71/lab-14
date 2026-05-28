Нужно запустить дашборд, сделать скриншоты и добавить
их в репозиторий.

ШАГ 1 — Убедись что зависимости установлены:
  cd dashboard
  uv sync
  cd ..

ШАГ 2 — Запусти дашборд в mock-режиме:
  cd dashboard
  uv run streamlit run src/dashboard/app.py \
    --server.port 8501 \
    --server.headless false 2>&1 &
  cd ..

  На Windows (в отдельном терминале):
  cd dashboard
  uv run streamlit run src/dashboard/app.py --server.port 8501
  cd ..

ШАГ 3 — Открой браузер на http://localhost:8501
  Дай дашборду 5-10 секунд загрузиться.

ШАГ 4 — Сделай скриншоты следующих видов:
  1. Полный вид дашборда (весь экран)
  2. KPI-карточки крупным планом
  3. График температурного timeline
  4. Comfort gauges

  Сохрани как:
  docs/screenshots/dashboard-full.png
  docs/screenshots/dashboard-kpi.png
  docs/screenshots/dashboard-timeline.png
  docs/screenshots/dashboard-gauges.png

ШАГ 5 — Если сделать реальные скриншоты невозможно,
  создай placeholder-файлы:
  
  Создай docs/screenshots/dashboard-full.png.placeholder
  Создай docs/screenshots/dashboard-kpi.png.placeholder
  Создай docs/screenshots/dashboard-timeline.png.placeholder
  Создай docs/screenshots/dashboard-gauges.png.placeholder
  
  Каждый содержит текст:
  "Screenshot: <название> — replace with real screenshot"

ШАГ 6 — Добавь ссылки на скриншоты в docs/architecture.md.
  Найди TODO или соответствующий раздел и добавь:

  ## Dashboard Screenshots
  
  ### Full View
  ![Dashboard Full View](../docs/screenshots/dashboard-full.png)
  
  ### KPI Cards
  ![KPI Cards](../docs/screenshots/dashboard-kpi.png)

ШАГ 7 — Останови дашборд:
  kill %1  # Linux/Mac
  # Windows: закрой терминал

ПРОВЕРКА:
  ls docs/screenshots/
  # Должно быть минимум 4 файла dashboard-*.png (или .placeholder)

  grep -c "dashboard" docs/architecture.md || \
  grep -c "Dashboard" docs/architecture.md
  # Должно быть >= 1

prompts/08-4-screenshots.md — этот промт целиком.

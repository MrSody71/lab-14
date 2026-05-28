# Промт 09-7: Финальный фикс CI

## Задача

Проверить состояние репо, убедиться что все 4 фикса CI применены,
закоммитить и запушить.

## ШАГ 0 — Диагностика

```bash
git status
git branch --show-current
git log --oneline -5
git remote -v
```

## ШАГ 1 — Фикс go.work

Убедиться что go.work отслеживается git:
```bash
git ls-files go.work   # должно вернуть go.work
```

## ШАГ 2 — Фикс py-analyzer permissions test

- `py-analyzer/tests/test_arrow_integration.py` — добавить `_os.access(X_OK)` check
- `.github/workflows/ci.yml` — флаг `-m "not integration"` в Test step
- `py-analyzer/src/analyzer/transforms.py` — `min_periods=1` → `min_samples=1`

## ШАГ 3 — Фикс Rust fmt

```bash
cd rust-validator && cargo fmt && cargo fmt --check && cd ..
```

## ШАГ 4 — Фикс prompts-gate

`.github/workflows/ci.yml`, шаг "Scan for leaked secrets":
```bash
FOUND=$(grep -rh \
  --include="*.md" \
  -E "OWM_API_KEY=['\"]?[a-zA-Z0-9_-]{20,}" \
  prompts/ 2>/dev/null || true)
```

`prompts/07-2-k8s-base.md`: заменить `cGxhY2Vob2xkZXI=` на `<base64-encoded-placeholder>`

## Результат (2026-05-28)

Репо было уже в sync с origin/main — все предыдущие фиксы запушены.

Единственное реальное изменение: обновлён паттерн prompts-gate:
- добавлен флаг `-rh` (suppress filenames в выводе)
- расширен character class: `[a-zA-Z0-9]` → `[a-zA-Z0-9_-]`
- обновлены комментарии

Коммит: `078d70a fix(ci): resolve all 4 failing CI jobs`

## Локальная проверка

```
=== go build ===       OK  ✅
=== rust fmt+clippy === OK  ✅
=== pytest ===          35 passed, 10 skipped  ✅
=== secret scan ===    CLEAN  ✅
```

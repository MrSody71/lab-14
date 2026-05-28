# Промт 09-6: Исправление проблем CI

## Задача

Починить 4 проблемы в GitHub Actions CI за один коммит.

## ПРОБЛЕМА 1 — go: no go.work file found

CI запускает `go work sync` но не находит `go.work`.

**Причина:** `go.work` и `go.work.sum` были исключены в `.gitignore`.

**Исправление:**
```
# Удалить из .gitignore:
# Go workspace file
go.work
go.work.sum
```
Затем `git add go.work go.work.sum` — файлы попадают в репозиторий.

Проверка: `go work sync` в корне без ошибок.

## ПРОБЛЕМА 2 — PermissionError на arrowsrv в pytest

`test_arrow_integration.py` падает с PermissionError если бинарник не исполняемый.

**Исправление** в `py-analyzer/tests/test_arrow_integration.py` — добавить в fixture:
```python
import os as _os
if not _os.access(str(ARROW_SERVER_BIN), _os.X_OK):
    pytest.skip(
        f"Arrow server binary not executable: {ARROW_SERVER_BIN}. "
        "Run: chmod +x arrow-server/arrowsrv"
    )
```

**Исправление** в `.github/workflows/ci.yml` — Test step для python-матрицы:
```yaml
- name: Test
  working-directory: ${{ matrix.project }}
  run: uv run pytest tests/ -v -m "not integration"
```

## ПРОБЛЕМА 3 — cargo fmt: struct init style

`cargo fmt --check` находит однострочные инициализации struct.

**Исправление:** запустить `cargo fmt` в `rust-validator/` — форматтер
автоматически разворачивает:
```rust
// до:
let ok = PyValidationResult { is_valid: true, errors: vec![] };
// после:
let ok = PyValidationResult {
    is_valid: true,
    errors: vec![],
};
```

## ПРОБЛЕМА 4 — prompts-gate: ложные срабатывания секретов

**Проблема 4а:** `prompts/07-2-k8s-base.md` содержал `cGxhY2Vob2xkZXI=`
(base64 от слова "placeholder") — grep засчитывал как секрет.

**Исправление:** заменить на `<base64-encoded-placeholder>`.

**Проблема 4б:** паттерн `OWM_API_KEY` без значения срабатывал на любое упоминание.

**Исправление** в `.github/workflows/ci.yml`, job `prompts-gate`:
```bash
FOUND=$(grep -r \
  -E "OWM_API_KEY=[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36,}|sk-[a-zA-Z0-9]{40,}" \
  prompts/ \
  --exclude="*.placeholder" \
  2>/dev/null || true)
if [ -n "$FOUND" ]; then
  echo "::error::Possible real secret leaked in prompts/"
  echo "$FOUND"
  exit 1
fi
echo "No real secrets found in prompts/"
```

## Финальная проверка

```bash
echo "=== 1. go.work ===" && ls go.work && go work sync
echo "=== 2. Go build ===" && go build ./... 2>&1 | tail -3
echo "=== 3. Rust fmt ===" && cd rust-validator && cargo fmt --check && cd ..
echo "=== 4. Rust clippy ===" && cd rust-validator && cargo clippy -- -D warnings && cd ..
echo "=== 5. Python tests ===" && cd py-analyzer && uv run pytest tests/ -v -m "not integration" && cd ..
echo "=== 6. Prompts scan ===" && \
  grep -r -E "OWM_API_KEY=[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36,}" prompts/ \
  2>/dev/null && echo "FOUND SECRETS" || echo "CLEAN"
```

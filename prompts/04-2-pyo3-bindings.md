Прочитай CLAUDE.md.

Оберни Rust-логику валидации в PyO3 биндинги.

=== rust-validator/src/lib.rs ===

Полная реализация:

use pyo3::prelude::*;
use pyo3::types::{PyAny, PyList};

pub mod rules;
use rules::{validate, validate_batch, Bounds, WeatherInput};

PyValidationError (#[pyclass]): field: String, message: String
  #[pymethods]: __repr__

PyValidationResult (#[pyclass]): is_valid: bool, errors: Vec<PyValidationError>
  #[pymethods]: __repr__ ("ValidationResult(valid)" или "ValidationResult(invalid, N errors)")

fn current_unix() -> i64 — SystemTime::now().duration_since(UNIX_EPOCH)

#[pyfunction] validate_reading(city, temperature, humidity, pressure,
                               wind_speed, timestamp_unix, now_unix=0)
  -> PyValidationResult
  Если now_unix == 0 — использовать current_unix().
  Создаёт WeatherInput, вызывает rules::validate, конвертирует результат.

#[pyfunction] validate_batch_records(py, records: &Bound<'_, PyList>, now_unix=0)
  -> PyResult<Bound<'py, PyAny>>
  Парсит список dict-ов (city, temperature, humidity, pressure, wind_speed,
  timestamp_unix), вызывает rules::validate_batch.
  Возвращает dict: {"valid": usize, "invalid": usize,
                    "errors": [{"index": usize, "field": str, "message": str}]}

#[pymodule] weather_validator — регистрирует оба класса и обе функции.

#[cfg(test)] mod tests: test_pyo3_result_repr — проверяет __repr__ обоих классов.

=== rust-validator/Cargo.toml ===

pyo3 = { version = "0.23", features = ["extension-module", "abi3-py311"] }
(PyO3 0.22 генерирует useless PyErr→PyErr conversion в #[pyfunction] макросе,
что триггерит clippy::useless_conversion. В 0.23 исправлено.)

ПРОВЕРКА:
  cd rust-validator
  cargo fmt --check 2>&1
  PYO3_PYTHON=<path-to-python> cargo clippy -- -D warnings 2>&1
  PYO3_PYTHON=<path-to-python> cargo test --lib 2>&1
  PYO3_PYTHON=<path-to-python> cargo build --release 2>&1 && echo "RELEASE BUILD OK"

9 тестов зелёных (8 из rules + 1 из lib.rs::tests).

prompts/04-2-pyo3-bindings.md — этот промт целиком.

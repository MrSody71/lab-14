Прочитай CLAUDE.md.

Нужно собрать Rust-расширение как Python .so/.pyd файл
и написать pytest-тесты которые импортируют его напрямую.

ШАГ 1 — добавить maturin в py-analyzer

В py-analyzer/pyproject.toml добавь в [dependency-groups] dev:
  "maturin>=1.7,<2"

Выполни:
  cd py-analyzer && uv sync && cd ..

ШАГ 2 — собрать .so через maturin develop

  cd rust-validator
  
  На Linux/Mac:
    uv run --directory ../py-analyzer maturin develop \
      --manifest-path Cargo.toml \
      --uv 2>&1

  На Windows (PowerShell):
    cd ../py-analyzer
    uv run maturin develop --manifest-path ../rust-validator/Cargo.toml
    cd ../rust-validator

  Это соберёт .so/.pyd и установит его прямо в .venv py-analyzer.
  cd ..

ШАГ 3 — убедиться что импорт работает:
  cd py-analyzer
  uv run python -c "import weather_validator; print('OK')" 2>&1
  cd ..

Если OK — продолжай. Если ошибка — покажи вывод и исправь.

ШАГ 4 — написать pytest-тесты

=== py-analyzer/tests/test_rust_validator.py ===

"""Tests for Rust weather_validator module (via PyO3)."""
import time
import pytest

try:
    import weather_validator as wv
    HAS_VALIDATOR = True
except ImportError:
    HAS_VALIDATOR = False

pytestmark = pytest.mark.skipif(
    not HAS_VALIDATOR,
    reason="weather_validator native module not built. "
           "Run: maturin develop in rust-validator/"
)

NOW = int(time.time())


class TestValidateReading:

    def test_valid_reading(self):
        r = wv.validate_reading(
            city="Moscow",
            temperature=15.0,
            humidity=65,
            pressure=1013,
            wind_speed=5.0,
            timestamp_unix=NOW - 10,
            now_unix=NOW,
        )
        assert r.is_valid is True
        assert len(r.errors) == 0

    def test_invalid_temperature(self):
        r = wv.validate_reading(
            city="Moscow",
            temperature=999.0,
            humidity=65,
            pressure=1013,
            wind_speed=5.0,
            timestamp_unix=NOW - 10,
            now_unix=NOW,
        )
        assert r.is_valid is False
        fields = [e.field for e in r.errors]
        assert "temperature" in fields

    def test_invalid_humidity(self):
        r = wv.validate_reading(
            city="Moscow",
            temperature=15.0,
            humidity=150,
            pressure=1013,
            wind_speed=5.0,
            timestamp_unix=NOW - 10,
            now_unix=NOW,
        )
        assert r.is_valid is False
        assert any(e.field == "humidity" for e in r.errors)

    def test_empty_city(self):
        r = wv.validate_reading(
            city="",
            temperature=15.0,
            humidity=65,
            pressure=1013,
            wind_speed=5.0,
            timestamp_unix=NOW - 10,
            now_unix=NOW,
        )
        assert r.is_valid is False
        assert any(e.field == "city" for e in r.errors)

    def test_future_timestamp(self):
        r = wv.validate_reading(
            city="Moscow",
            temperature=15.0,
            humidity=65,
            pressure=1013,
            wind_speed=5.0,
            timestamp_unix=NOW + 9999,
            now_unix=NOW,
        )
        assert r.is_valid is False
        assert any(e.field == "timestamp" for e in r.errors)

    def test_repr_valid(self):
        r = wv.validate_reading("Moscow", 15.0, 65, 1013, 5.0,
                                NOW - 10, NOW)
        assert "valid" in repr(r).lower()

    def test_repr_invalid(self):
        r = wv.validate_reading("", 999.0, 150, 500, -1.0,
                                NOW + 9999, NOW)
        assert "invalid" in repr(r).lower()


class TestValidateBatch:

    def _record(self, **kwargs):
        base = {
            "city": "Moscow",
            "temperature": 15.0,
            "humidity": 65,
            "pressure": 1013,
            "wind_speed": 5.0,
            "timestamp_unix": NOW - 10,
        }
        base.update(kwargs)
        return base

    def test_all_valid(self):
        records = [self._record(), self._record(city="London")]
        result = wv.validate_batch_records(records, now_unix=NOW)
        assert result["valid"] == 2
        assert result["invalid"] == 0
        assert result["errors"] == []

    def test_one_invalid(self):
        records = [
            self._record(),
            self._record(temperature=999.0),
            self._record(city="Berlin"),
        ]
        result = wv.validate_batch_records(records, now_unix=NOW)
        assert result["valid"] == 2
        assert result["invalid"] == 1
        assert result["errors"][0]["index"] == 1
        assert result["errors"][0]["field"] == "temperature"

    def test_empty_batch(self):
        result = wv.validate_batch_records([], now_unix=NOW)
        assert result["valid"] == 0
        assert result["invalid"] == 0

ПРОВЕРКА:
  cd py-analyzer
  uv run pytest tests/test_rust_validator.py -v 2>&1
  cd ..

10 тестов зелёных. Если skipif сработал — значит .so не собралось,
исправь сборку на предыдущем шаге.

prompts/04-3-maturin-tests.md — этот промт целиком.

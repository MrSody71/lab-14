Прочитай CLAUDE.md.

Реализуй бизнес-логику валидации погодных данных в Rust.
Пока только чистые функции без PyO3 — чтобы легко тестировать.

=== rust-validator/src/rules.rs ===

Структуры: Bounds (Default), ValidationError, ValidationResult, WeatherInput.

pub fn validate(input: &WeatherInput, bounds: &Bounds, now_unix: i64) -> ValidationResult
  Правила: city не пустой, temperature в [temp_min_c, temp_max_c],
  humidity в [0,100], pressure в [870,1085], wind_speed в [0,120],
  timestamp не в будущем и не старше timestamp_max_lag_sec.
  Возвращает все найденные ошибки.

pub fn validate_batch(inputs: &[WeatherInput], bounds: &Bounds, now_unix: i64)
  -> (usize, usize, Vec<(usize, Vec<ValidationError>)>)

#[cfg(test)] — 8 тестов:
  test_valid_reading, test_temperature_too_high, test_temperature_too_low,
  test_humidity_out_of_range, test_empty_city, test_future_timestamp,
  test_multiple_errors (5 полей невалидны, timestamp валидный → ровно 5 ошибок),
  test_validate_batch

Примечание: в test_multiple_errors использовать timestamp_unix: now() - 10
(валидный), иначе получится 6 ошибок вместо 5.

=== rust-validator/src/lib.rs ===

Добавить: pub mod rules;

ПРОВЕРКА:
  cd rust-validator
  PYO3_PYTHON=<path-to-python> cargo test --lib 2>&1

9 тестов зелёных (8 из rules + 1 dummy из lib.rs).

prompts/04-1-rust-rules.md — этот промт целиком.

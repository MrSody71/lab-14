# Промт 0.4 — Rust crate заглушка

Прочитай CLAUDE.md.

Создай Rust crate rust-validator — заглушку с PyO3, которая собирается
и проходит smoke-тест. Бизнес-логики НЕТ, только проверка, что toolchain
настроен и PyO3 линкуется.

ФАЙЛЫ:

1. rust-validator/Cargo.toml:
   [package]
   name = "weather_validator"
   version = "0.0.0"
   edition = "2021"

   [lib]
   name = "weather_validator"
   crate-type = ["cdylib", "rlib"]

   [dependencies]
   pyo3 = { version = "0.22", features = ["extension-module", "abi3-py311"] }

   [dev-dependencies]
   # тесты Rust-only, без Python

2. rust-validator/src/lib.rs:
   use pyo3::prelude::*;

   /// Заглушка: всегда возвращает true. Заменим на реальную валидацию
   /// в этапе 4.
   #[pyfunction]
   fn validate_dummy() -> bool {
       true
   }

   #[pymodule]
   fn weather_validator(m: &Bound<'_, PyModule>) -> PyResult<()> {
       m.add_function(wrap_pyfunction!(validate_dummy, m)?)?;
       Ok(())
   }

   #[cfg(test)]
   mod tests {
       use super::*;
       #[test]
       fn dummy_returns_true() {
           assert!(validate_dummy());
       }
   }

3. rust-validator/tests/smoke.rs:
   // Интеграционный smoke-тест. Реальные интеграционные тесты с Python
   // добавим в этапе 4 через pytest.
   #[test]
   fn crate_links() {
       // Если этот тест компилируется, значит crate собирается.
       assert_eq!(2 + 2, 4);
   }

4. rust-validator/.gitignore:
   target/
   Cargo.lock

5. Удали .gitkeep в rust-validator/src и rust-validator/tests, если он там
   ещё есть.

ПРОВЕРКА (покажи вывод каждой команды):
  cd rust-validator
  cargo fmt --check
  cargo clippy --all-targets -- -D warnings
  cargo test
  cargo build --release
  cd ..

Все четыре должны пройти. Если clippy ругается — почини и повтори.

prompts/00-4-rust-stub.md — этот промт целиком.

В конце: git status.

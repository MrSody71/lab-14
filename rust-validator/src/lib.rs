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

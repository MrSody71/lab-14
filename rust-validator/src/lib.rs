use pyo3::prelude::*;
use pyo3::types::{PyAny, PyList};

pub mod rules;
use rules::{validate, validate_batch, Bounds, WeatherInput};

/// Python-класс: одна ошибка валидации.
#[pyclass]
#[derive(Clone)]
pub struct PyValidationError {
    #[pyo3(get)]
    pub field: String,
    #[pyo3(get)]
    pub message: String,
}

#[pymethods]
impl PyValidationError {
    fn __repr__(&self) -> String {
        format!(
            "ValidationError(field={}, msg={})",
            self.field, self.message
        )
    }
}

/// Python-класс: результат валидации одной записи.
#[pyclass]
#[derive(Clone)]
pub struct PyValidationResult {
    #[pyo3(get)]
    pub is_valid: bool,
    #[pyo3(get)]
    pub errors: Vec<PyValidationError>,
}

#[pymethods]
impl PyValidationResult {
    fn __repr__(&self) -> String {
        if self.is_valid {
            "ValidationResult(valid)".to_string()
        } else {
            format!("ValidationResult(invalid, {} errors)", self.errors.len())
        }
    }
}

fn current_unix() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

/// Валидирует одну погодную запись.
#[pyfunction]
#[pyo3(signature = (city, temperature, humidity, pressure,
                    wind_speed, timestamp_unix, now_unix=0))]
fn validate_reading(
    city: String,
    temperature: f64,
    humidity: i32,
    pressure: i32,
    wind_speed: f64,
    timestamp_unix: i64,
    now_unix: i64,
) -> PyValidationResult {
    let now = if now_unix == 0 {
        current_unix()
    } else {
        now_unix
    };

    let input = WeatherInput {
        city,
        temperature,
        humidity,
        pressure,
        wind_speed,
        timestamp_unix,
    };

    let result = validate(&input, &Bounds::default(), now);
    PyValidationResult {
        is_valid: result.is_valid,
        errors: result
            .errors
            .iter()
            .map(|e| PyValidationError {
                field: e.field.clone(),
                message: e.message.clone(),
            })
            .collect(),
    }
}

/// Валидирует список записей разом.
#[pyfunction]
#[pyo3(signature = (records, now_unix=0))]
fn validate_batch_records<'py>(
    py: Python<'py>,
    records: &Bound<'_, PyList>,
    now_unix: i64,
) -> PyResult<Bound<'py, PyAny>> {
    let now = if now_unix == 0 {
        current_unix()
    } else {
        now_unix
    };

    let mut inputs = Vec::with_capacity(records.len());
    for item in records.iter() {
        let d = item.downcast::<pyo3::types::PyDict>()?;

        let get_str = |k: &str| -> PyResult<String> {
            d.get_item(k)?
                .map(|v| v.extract::<String>())
                .unwrap_or(Ok(String::new()))
        };
        let get_f64 = |k: &str| -> PyResult<f64> {
            d.get_item(k)?
                .map(|v| v.extract::<f64>())
                .unwrap_or(Ok(0.0))
        };
        let get_i32 = |k: &str| -> PyResult<i32> {
            d.get_item(k)?.map(|v| v.extract::<i32>()).unwrap_or(Ok(0))
        };
        let get_i64 = |k: &str| -> PyResult<i64> {
            d.get_item(k)?.map(|v| v.extract::<i64>()).unwrap_or(Ok(0))
        };

        inputs.push(WeatherInput {
            city: get_str("city")?,
            temperature: get_f64("temperature")?,
            humidity: get_i32("humidity")?,
            pressure: get_i32("pressure")?,
            wind_speed: get_f64("wind_speed")?,
            timestamp_unix: get_i64("timestamp_unix")?,
        });
    }

    let (valid, invalid, errors) = validate_batch(&inputs, &Bounds::default(), now);

    let result = pyo3::types::PyDict::new(py);
    result.set_item("valid", valid)?;
    result.set_item("invalid", invalid)?;

    let err_list = pyo3::types::PyList::empty(py);
    for (idx, errs) in errors {
        for e in errs {
            let ed = pyo3::types::PyDict::new(py);
            ed.set_item("index", idx)?;
            ed.set_item("field", &e.field)?;
            ed.set_item("message", &e.message)?;
            err_list.append(ed)?;
        }
    }
    result.set_item("errors", err_list)?;
    Ok(result.into_any())
}

#[pymodule]
fn weather_validator(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyValidationResult>()?;
    m.add_class::<PyValidationError>()?;
    m.add_function(wrap_pyfunction!(validate_reading, m)?)?;
    m.add_function(wrap_pyfunction!(validate_batch_records, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pyo3_result_repr() {
        let err = PyValidationError {
            field: "city".to_string(),
            message: "city name is empty".to_string(),
        };
        assert!(err.__repr__().contains("city"));

        let ok = PyValidationResult { is_valid: true, errors: vec![] };
        assert_eq!(ok.__repr__(), "ValidationResult(valid)");

        let bad = PyValidationResult { is_valid: false, errors: vec![err] };
        assert!(bad.__repr__().contains("1 errors"));
    }
}

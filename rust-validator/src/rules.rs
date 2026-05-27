//! Правила валидации погодных показаний.
//! Все функции — чистые, без side-эффектов, легко тестируются.

/// Диапазоны допустимых значений для погодных показаний.
pub struct Bounds {
    pub temp_min_c: f64,
    pub temp_max_c: f64,
    pub humidity_min: i32,
    pub humidity_max: i32,
    pub pressure_min: i32,
    pub pressure_max: i32,
    pub wind_speed_max: f64,
    pub timestamp_max_lag_sec: i64,
}

impl Default for Bounds {
    fn default() -> Self {
        Self {
            temp_min_c: -80.0,
            temp_max_c: 60.0,
            humidity_min: 0,
            humidity_max: 100,
            pressure_min: 870,
            pressure_max: 1085,
            wind_speed_max: 120.0,
            timestamp_max_lag_sec: 3600,
        }
    }
}

/// Одна ошибка валидации.
#[derive(Debug, Clone, PartialEq)]
pub struct ValidationError {
    pub field: String,
    pub message: String,
}

impl ValidationError {
    pub fn new(field: &str, message: &str) -> Self {
        Self {
            field: field.to_string(),
            message: message.to_string(),
        }
    }
}

/// Результат валидации одной записи.
#[derive(Debug, Clone)]
pub struct ValidationResult {
    pub is_valid: bool,
    pub errors: Vec<ValidationError>,
}

impl ValidationResult {
    pub fn ok() -> Self {
        Self { is_valid: true, errors: vec![] }
    }
    pub fn fail(errors: Vec<ValidationError>) -> Self {
        Self { is_valid: false, errors }
    }
}

/// Входные данные для валидации.
#[derive(Debug, Clone)]
pub struct WeatherInput {
    pub city: String,
    pub temperature: f64,
    pub humidity: i32,
    pub pressure: i32,
    pub wind_speed: f64,
    pub timestamp_unix: i64,
}

/// Валидирует одну запись по заданным правилам.
pub fn validate(input: &WeatherInput, bounds: &Bounds,
                now_unix: i64) -> ValidationResult {
    let mut errors = Vec::new();

    // 1. city не пустой
    if input.city.trim().is_empty() {
        errors.push(ValidationError::new("city", "city name is empty"));
    }

    // 2. температура
    if input.temperature < bounds.temp_min_c || input.temperature > bounds.temp_max_c {
        errors.push(ValidationError::new(
            "temperature",
            &format!(
                "temperature {:.1} °C out of range [{}, {}]",
                input.temperature, bounds.temp_min_c, bounds.temp_max_c
            ),
        ));
    }

    // 3. влажность
    if input.humidity < bounds.humidity_min || input.humidity > bounds.humidity_max {
        errors.push(ValidationError::new(
            "humidity",
            &format!(
                "humidity {} out of range [{}, {}]",
                input.humidity, bounds.humidity_min, bounds.humidity_max
            ),
        ));
    }

    // 4. давление
    if input.pressure < bounds.pressure_min || input.pressure > bounds.pressure_max {
        errors.push(ValidationError::new(
            "pressure",
            &format!(
                "pressure {} hPa out of range [{}, {}]",
                input.pressure, bounds.pressure_min, bounds.pressure_max
            ),
        ));
    }

    // 5. скорость ветра
    if input.wind_speed < 0.0 || input.wind_speed > bounds.wind_speed_max {
        errors.push(ValidationError::new(
            "wind_speed",
            &format!(
                "wind_speed {:.1} m/s out of range [0, {}]",
                input.wind_speed, bounds.wind_speed_max
            ),
        ));
    }

    // 6. timestamp
    let lag = now_unix - input.timestamp_unix;
    if lag < 0 {
        errors.push(ValidationError::new(
            "timestamp",
            "timestamp is in the future",
        ));
    } else if lag > bounds.timestamp_max_lag_sec {
        errors.push(ValidationError::new(
            "timestamp",
            &format!(
                "timestamp is {} seconds old (max {})",
                lag, bounds.timestamp_max_lag_sec
            ),
        ));
    }

    if errors.is_empty() {
        ValidationResult::ok()
    } else {
        ValidationResult::fail(errors)
    }
}

/// Валидирует пакет записей.
/// Возвращает (valid_count, invalid_count, все ошибки).
pub fn validate_batch(
    inputs: &[WeatherInput],
    bounds: &Bounds,
    now_unix: i64,
) -> (usize, usize, Vec<(usize, Vec<ValidationError>)>) {
    let mut valid = 0usize;
    let mut invalid = 0usize;
    let mut all_errors: Vec<(usize, Vec<ValidationError>)> = Vec::new();

    for (i, input) in inputs.iter().enumerate() {
        let result = validate(input, bounds, now_unix);
        if result.is_valid {
            valid += 1;
        } else {
            invalid += 1;
            all_errors.push((i, result.errors));
        }
    }
    (valid, invalid, all_errors)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn now() -> i64 {
        1_700_000_000i64
    }

    fn valid_input() -> WeatherInput {
        WeatherInput {
            city: "Moscow".to_string(),
            temperature: 15.0,
            humidity: 65,
            pressure: 1013,
            wind_speed: 5.0,
            timestamp_unix: now() - 10,
        }
    }

    #[test]
    fn test_valid_reading() {
        let result = validate(&valid_input(), &Bounds::default(), now());
        assert!(result.is_valid);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn test_temperature_too_high() {
        let mut input = valid_input();
        input.temperature = 100.0;
        let result = validate(&input, &Bounds::default(), now());
        assert!(!result.is_valid);
        assert_eq!(result.errors[0].field, "temperature");
    }

    #[test]
    fn test_temperature_too_low() {
        let mut input = valid_input();
        input.temperature = -100.0;
        let result = validate(&input, &Bounds::default(), now());
        assert!(!result.is_valid);
        assert_eq!(result.errors[0].field, "temperature");
    }

    #[test]
    fn test_humidity_out_of_range() {
        let mut input = valid_input();
        input.humidity = 150;
        let result = validate(&input, &Bounds::default(), now());
        assert!(!result.is_valid);
        assert_eq!(result.errors[0].field, "humidity");
    }

    #[test]
    fn test_empty_city() {
        let mut input = valid_input();
        input.city = "   ".to_string();
        let result = validate(&input, &Bounds::default(), now());
        assert!(!result.is_valid);
        assert_eq!(result.errors[0].field, "city");
    }

    #[test]
    fn test_future_timestamp() {
        let mut input = valid_input();
        input.timestamp_unix = now() + 9999;
        let result = validate(&input, &Bounds::default(), now());
        assert!(!result.is_valid);
        assert_eq!(result.errors[0].field, "timestamp");
    }

    #[test]
    fn test_multiple_errors() {
        let input = WeatherInput {
            city: "".to_string(),
            temperature: 999.0,
            humidity: -1,
            pressure: 500,
            wind_speed: -5.0,
            timestamp_unix: now() - 10, // валидный timestamp — чтобы получить ровно 5 ошибок
        };
        let result = validate(&input, &Bounds::default(), now());
        assert!(!result.is_valid);
        // 5 ошибок: city, temp, humidity, pressure, wind
        assert_eq!(result.errors.len(), 5);
    }

    #[test]
    fn test_validate_batch() {
        let inputs = vec![
            valid_input(),
            WeatherInput { temperature: 999.0, ..valid_input() },
            valid_input(),
        ];
        let (valid, invalid, errors) =
            validate_batch(&inputs, &Bounds::default(), now());
        assert_eq!(valid, 2);
        assert_eq!(invalid, 1);
        assert_eq!(errors[0].0, 1);
    }
}

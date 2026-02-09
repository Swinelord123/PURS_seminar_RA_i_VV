-- ======================================================
-- DATABASE: ESP32 CLIMATE CONTROL SYSTEM
-- ======================================================

-- Create database
CREATE DATABASE IF NOT EXISTS esp32_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE esp32_db;

-- ======================================================
-- USERS TABLE (ADMIN AUTHENTICATION)
-- ======================================================

DROP USER IF EXISTS 'esp32_app'@'localhost';

-- Create user with a known password
CREATE USER 'esp32_app'@'localhost'
IDENTIFIED WITH mysql_native_password
BY 'esp32pass';

-- Give full access to your database
GRANT ALL PRIVILEGES ON esp32_db.* TO 'esp32_app'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_admin TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ======================================================
-- SETTINGS TABLE (CONTROL & THRESHOLDS)
-- ONE ROW ONLY (id = 1)
-- ======================================================
CREATE TABLE IF NOT EXISTS settings (
    id TINYINT PRIMARY KEY,
    temp_low FLOAT NOT NULL,
    temp_high FLOAT NOT NULL,
    hum_high FLOAT NOT NULL,
    auto_control TINYINT NOT NULL,
    fan_manual TINYINT NOT NULL,
    heater_manual TINYINT NOT NULL
);

-- Insert default settings (IMPORTANT)
INSERT INTO settings (
    id, temp_low, temp_high, hum_high,
    auto_control, fan_manual, heater_manual
)
VALUES (
    1,       -- id
    22.0,    -- temp_low
    30.0,    -- temp_high
    70.0,    -- hum_high
    1,       -- auto_control (AUTO)
    0,       -- fan_manual
    0        -- heater_manual
)
ON DUPLICATE KEY UPDATE id = id;

-- ======================================================
-- ALARM LOG TABLE (HISTORY)
-- ======================================================
CREATE TABLE IF NOT EXISTS alarm_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    temperature FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    alarm_type ENUM('temperature', 'humidity', 'both') NOT NULL
);

CREATE TABLE IF NOT EXISTS sensor_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    temperature FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO sensor_data (temperature, humidity)
VALUES (23.5, 45.2);

CREATE TABLE IF NOT EXISTS control_state (
    id INT PRIMARY KEY DEFAULT 1,
    fan_on BOOLEAN DEFAULT 0,
    heater_on BOOLEAN DEFAULT 0,
    temp_threshold FLOAT DEFAULT 30.0,
    humidity_threshold FLOAT DEFAULT 70.0
);
-- Ensure single row
INSERT IGNORE INTO control_state (id) VALUES (1);

-- ======================================================
-- OPTIONAL INDEXES (PERFORMANCE)
-- ======================================================
CREATE INDEX idx_alarm_timestamp ON alarm_log (timestamp);
CREATE INDEX idx_alarm_type ON alarm_log (alarm_type);


SELECT username FROM users;
INSERT INTO users (username, password_hash, is_admin)
VALUES (
    'admin',
    'scrypt:32768:8:1$T54kVjbmlvRYSrh1$935532754584963655719fce861e21934fa43be8dc016ab0f608e053e52616c4d35f5b28fb64bff45547ae0a6e2b71d7982d114a6766912e119f942865e6648f',
    1
);
SHOW CREATE TABLE users;
-- ======================================================
-- DONE
-- ======================================================
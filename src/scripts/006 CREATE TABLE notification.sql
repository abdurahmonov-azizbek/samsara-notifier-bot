CREATE TABLE notification(
    id SERIAL NOT NULL PRIMARY KEY,
    telegram_id BIGINT,
    truck_id BIGINT,
    notification_type_id INTEGER REFERENCES notification_type(id),
    every_minutes INTEGER,
    last_send_time TIMESTAMP WITHOUT TIME ZONE,
    warning_type VARCHAR(100),
    engine_status VARCHAR(100))
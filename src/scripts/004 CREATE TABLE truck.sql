CREATE TABLE truck (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    truck_id BIGINT,
    company_id BIGINT)
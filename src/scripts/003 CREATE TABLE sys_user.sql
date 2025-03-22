CREATE TABLE sys_user(
    id SERIAL NOT NULL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    full_name VARCHAR(100),
    company_id INTEGER NOT NULL REFERENCES company(id),
    balance INTEGER NOT NULL DEFAULT 0);

CREATE TABLE sys_user
(
    id          SERIAL  NOT NULL PRIMARY KEY,
    telegram_id BIGINT  NOT NULL,
    full_name   VARCHAR(100),
    company_id  BIGINT[] NOT NULL, -- REFERENCES yo'q
    balance     INTEGER NOT NULL DEFAULT 0
);

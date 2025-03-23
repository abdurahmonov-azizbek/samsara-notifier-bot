CREATE TABLE notification_type(
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULl);


 INSERT INTO notification_type(id, name)
 VALUES
 (1, 'Warnings'),
 (2, 'Engine status'),
 (3, 'Timer');
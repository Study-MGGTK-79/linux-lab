-- Mock Database Initial Schema & Sample Records
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(128) NOT NULL,
    role VARCHAR(32) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    amount NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, email, role) VALUES
('alice_admin', 'alice@enterprise.internal', 'superadmin'),
('bob_dev', 'bob@enterprise.internal', 'developer'),
('charlie_ops', 'charlie@enterprise.internal', 'devops'),
('diana_qa', 'diana@enterprise.internal', 'tester');

INSERT INTO orders (user_id, amount, status) VALUES
(1, 1499.90, 'COMPLETED'),
(2, 299.50, 'PROCESSING'),
(3, 4999.00, 'COMPLETED'),
(4, 89.00, 'PENDING');

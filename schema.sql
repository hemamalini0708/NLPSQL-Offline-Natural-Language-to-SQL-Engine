-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    gender VARCHAR(50),
    age INT,
    email VARCHAR(255),
    phone VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    signup_date DATE,
    loyalty_score INT,
    annual_income DECIMAL(15, 2),
    preferred_category VARCHAR(100),
    account_status VARCHAR(50)
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    product_name VARCHAR(255),
    product_category VARCHAR(100),
    quantity INT,
    unit_price DECIMAL(12, 2),
    discount_percent DECIMAL(5, 2),
    shipping_cost DECIMAL(12, 2),
    order_status VARCHAR(50),
    payment_method VARCHAR(50),
    order_date DATE,
    warehouse_city VARCHAR(100),
    sales_channel VARCHAR(100),
    total_amount DECIMAL(12, 2),
    delivery_date DATE
);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(order_id),
    customer_id INT REFERENCES customers(customer_id),
    payment_date DATE,
    payment_status VARCHAR(50),
    payment_gateway VARCHAR(50),
    transaction_amount DECIMAL(12, 2),
    tax_amount DECIMAL(12, 2),
    refund_amount DECIMAL(12, 2),
    currency VARCHAR(10),
    fraud_flag VARCHAR(10),
    installment_months INT,
    processing_fee DECIMAL(12, 2),
    transaction_reference VARCHAR(255),
    device_type VARCHAR(50)
);

-- NL-SQL Pairs table for RAG
CREATE TABLE IF NOT EXISTS nl_sql_pairs (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    intent VARCHAR(50),
    question_embedding vector(768)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_customer_id ON payments(customer_id);

-- Query History Table
CREATE TABLE IF NOT EXISTS nlpsql_query_history (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    complexity VARCHAR(50),
    was_valid BOOLEAN,
    execution_time_ms INTEGER,
    row_count INTEGER,
    error_message TEXT,
    feedback INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

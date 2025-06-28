Show databases;
create database productDataset;
Use productDataset;

CREATE TABLE products (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10, 2)
);

CREATE TABLE products_addresses (
    address_id INT PRIMARY KEY,
    product_id INT,
    address_line VARCHAR(200),
    city VARCHAR(50),
    country VARCHAR(50),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE products_addresses_customfields (
    field_id INT PRIMARY KEY,
    address_id INT,
    field_key VARCHAR(50),
    field_value VARCHAR(100),
    FOREIGN KEY (address_id) REFERENCES products_addresses(address_id)
);

-- Insert data into products (parent)
INSERT INTO products (product_id, product_name, category, price) VALUES
(1, 'Laptop X', 'Electronics', 799.99),
(2, 'Smartphone Y', 'Electronics', 599.49),
(3, 'Coffee Maker Z', 'Home Appliances', 129.99),
(4, 'Phone', 'Electronics', 799.99),
(5, 'Fridge', 'Electronics', 599.49),
(6, 'Cycle', 'Transport', 129.99)
;

-- Insert data into products_addresses (child)
INSERT IGNORE INTO products_addresses (address_id, product_id, address_line, city, country) VALUES
(101, 1, '123 Tech Park', 'San Francisco', 'USA'),
(102, 2, '456 Mobile Ave', 'New York', 'USA'),
(103, 3, 'kolahpur road', 'Sangli', 'IN'),
(104, 4, '44 ganesh mala', 'Miraj', 'IN'),
(105, 4, '567 Gaonbhag', 'Pune', 'IN'),
(106, 3, 'kolahpur road', 'Sangli', 'IN'),
(107, 5, '44 ganesh mala', 'Miraj', 'IN'),
(108, 5, '567 Gaonbhag', 'Pune', 'IN'),
(109, 6, '567 Gaonbhag', 'Pune', 'IN'),
(110, 2, '456 Mobile Ave', 'Mumbai', 'IN')
;

-- Insert data into products_addresses_customfields (grandchild)
INSERT IGNORE INTO products_addresses_customfields (field_id, address_id, field_key, field_value) VALUES
(1001, 101, 'Warehouse Zone', 'A1'),
(1002, 101, 'Storage Temp', '22C'),
(1003, 102, 'Delivery Type', 'Express'),
(1004, 103, 'Warehouse Zone', 'B2'),
(1005, 104, 'Solar Zone', '199'),
(1006, 105, 'Market area', 'hh4'),
(1007, 106, 'Red Light', '09p'),
(1008, 106, 'Open Park', '123M')
;


-- Testing Queries-------------------------------------------------------------------------------

DROP table products;
DROP TABLE products_addresses;
TRUNCATE TABLE products_addresses;
DROP TABLE products_addresses_customfields;

select * from products;
select * from products_addresses;
select * from products_addresses_customfields;

SELECT *
FROM products
LEFT JOIN products_addresses ON products.product_id = products_addresses.product_id
LEFT JOIN products_addresses_customfields ON products_addresses.address_id = products_addresses_customfields.address_id;

SELECT 
    p.product_id,
    p.product_name,
    p.category,
    p.price,
    pa.address_id,
    pa.address_line,
    pa.city,
    pa.country,
    pac.field_id,
    pac.field_key,
    pac.field_value
FROM products p
JOIN products_addresses pa ON p.product_id = pa.product_id
JOIN products_addresses_customfields pac ON pa.address_id = pac.address_id;

-- Get the top 2 cities where the most expensive product in each category is most frequently ordered

SELECT pa.city, COUNT(*) AS order_count
FROM products p
JOIN products_addresses pa ON p.product_id = pa.product_id
WHERE (p.price, p.category) IN (
    SELECT MAX(price), category
    FROM products
    GROUP BY category
)
GROUP BY pa.city
ORDER BY order_count DESC
LIMIT 2;

-- What is the city and country of the product 'Coffee Maker Z'?

SELECT pa.city, pa.country
FROM products p
JOIN products_addresses pa ON p.product_id = pa.product_id
WHERE p.product_name = 'Coffee Maker Z';

SELECT p.product_id, p.product_name, p.category, p.price
FROM products p
WHERE p.price > 500

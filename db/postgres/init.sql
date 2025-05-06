CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE persons (
    id SERIAL PRIMARY KEY,
    firstname VARCHAR(100),
    lastname VARCHAR(100),
    prsaddress TEXT,
    city VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(30),
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- function to update the updated_at field
CREATE OR REPLACE FUNCTION update_last_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_modified = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- trigger to call the function before insert or update
CREATE TRIGGER trigger_update_last_modified
BEFORE INSERT OR UPDATE ON persons
FOR EACH ROW
EXECUTE FUNCTION update_last_modified();
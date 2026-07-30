CREATE TABLE IF NOT EXISTS stats (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(255),
    group_name VARCHAR(255),
    sub_title VARCHAR(255),
    synced_sources INT DEFAULT 1
);

-- Insert default stats row
INSERT INTO stats (user_name, group_name, sub_title, synced_sources) 
VALUES ('Minh', 'Nhóm G12 · Zone 1', 'SVK3 VinAI · E403', 1)
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS deadlines (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500),
    course VARCHAR(255),
    due_date VARCHAR(255),
    due_relative VARCHAR(255),
    source VARCHAR(255),
    status VARCHAR(255),
    priority VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500),
    summary TEXT,
    course VARCHAR(255),
    source VARCHAR(255),
    time_relative VARCHAR(255),
    content TEXT,
    is_read BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500),
    file_type VARCHAR(255),
    course VARCHAR(255),
    source VARCHAR(255),
    updated_date VARCHAR(255),
    url TEXT
);

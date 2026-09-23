CREATE TABLE jobs (
 id VARCHAR(36) PRIMARY KEY,
 owner_name VARCHAR(80) NOT NULL,
 request_key VARCHAR(80) NOT NULL,
 question VARCHAR(500) NOT NULL,
 status VARCHAR(20) NOT NULL,
 answer_text CLOB NOT NULL,
 attempt INT NOT NULL DEFAULT 0,
 lease_token VARCHAR(36),
 lease_until BIGINT NOT NULL DEFAULT 0,
 created_at BIGINT NOT NULL,
 UNIQUE(owner_name, request_key)
);
CREATE INDEX jobs_due ON jobs(status, lease_until);

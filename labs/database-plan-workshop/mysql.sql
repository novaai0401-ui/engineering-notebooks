-- Executed on MySQL 8.4.11; see mysql-report.json and mysql-plans.txt.
-- Select a disposable schema first. No DROP commands; a second run intentionally
-- stops on existing object names instead of deleting someone else's data.
CREATE TABLE nb_tickets (
  id BIGINT PRIMARY KEY,
  tenant_id INT NOT NULL,
  status VARCHAR(12) NOT NULL,
  created_at DATETIME NOT NULL,
  price_minor INT NOT NULL
);
INSERT INTO nb_tickets(id,tenant_id,status,created_at,price_minor)
WITH RECURSIVE seq(n) AS (
  SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n<1000
)
SELECT n,MOD(n,10),
  CASE WHEN MOD(FLOOR(n/10),3)=0 THEN 'PENDING' ELSE 'SETTLED' END,
  TIMESTAMPADD(MINUTE,n,'2026-01-01 00:00:00'),1200+MOD(n,5)*100
FROM seq;
SELECT COUNT(*) AS seeded_rows FROM nb_tickets;
-- Baseline before adding the candidate index.
EXPLAIN SELECT id,created_at FROM nb_tickets
WHERE tenant_id=3 AND status='SETTLED'
ORDER BY created_at,id LIMIT 20;
EXPLAIN ANALYZE SELECT id,created_at FROM nb_tickets
WHERE tenant_id=3 AND status='SETTLED'
ORDER BY created_at,id LIMIT 20;
CREATE INDEX nb_tickets_lookup ON nb_tickets(tenant_id,status,created_at,id);
ANALYZE TABLE nb_tickets;
-- Repeat the same query and compare actual work, not only the key name.
EXPLAIN ANALYZE SELECT id,created_at FROM nb_tickets
WHERE tenant_id=3 AND status='SETTLED'
ORDER BY created_at,id LIMIT 20;
-- A changed query may need a different index: status is no longer fixed.
EXPLAIN ANALYZE SELECT id,created_at FROM nb_tickets
WHERE tenant_id=3 ORDER BY created_at,id LIMIT 20;
-- Small synthetic data is not a production performance benchmark.

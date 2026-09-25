-- Oracle 19c-style teaching recipe. NOT executed in the recorded environment.
-- Use a disposable schema. DDL has implicit-commit implications; do not run
-- this inside a transaction containing unrelated work. No DROP commands.
CREATE TABLE nb_tickets (
  id NUMBER(19) PRIMARY KEY,
  tenant_id NUMBER(10) NOT NULL,
  status VARCHAR2(12) NOT NULL,
  created_at DATE NOT NULL,
  price_minor NUMBER(10) NOT NULL
);
INSERT INTO nb_tickets(id,tenant_id,status,created_at,price_minor)
SELECT LEVEL,MOD(LEVEL,10),
  CASE WHEN MOD(FLOOR(LEVEL/10),3)=0 THEN 'PENDING' ELSE 'SETTLED' END,
  DATE '2026-01-01'+LEVEL/1440,1200+MOD(LEVEL,5)*100
FROM dual CONNECT BY LEVEL<=1000;
COMMIT;
SELECT COUNT(*) AS seeded_rows FROM nb_tickets;
EXPLAIN PLAN SET STATEMENT_ID='NB_BEFORE' FOR
SELECT id,created_at FROM nb_tickets
WHERE tenant_id=3 AND status='SETTLED'
ORDER BY created_at,id FETCH FIRST 20 ROWS ONLY;
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(NULL,'NB_BEFORE','TYPICAL'));
CREATE INDEX nb_tickets_lookup ON nb_tickets(tenant_id,status,created_at,id);
BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(USER,'NB_TICKETS',cascade=>TRUE);
END;
/
SELECT /*+ gather_plan_statistics */ /* nb_after */ id,created_at
FROM nb_tickets WHERE tenant_id=3 AND status='SETTLED'
ORDER BY created_at,id FETCH FIRST 20 ROWS ONLY;
-- Fetch all rows above. With appropriate diagnostic privileges, identify the cursor:
SELECT sql_id,child_number,plan_hash_value,last_active_time
FROM v$sql
WHERE sql_text LIKE 'SELECT /*+ gather_plan_statistics */ /* nb_after */%'
ORDER BY last_active_time DESC;
-- Then substitute the observed SQL_ID and CHILD_NUMBER explicitly:
-- SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR('observed_sql_id',0,'ALLSTATS LAST +PREDICATE'));
-- Compare E-Rows/A-Rows, starts, buffers, predicates and the actual index operation.

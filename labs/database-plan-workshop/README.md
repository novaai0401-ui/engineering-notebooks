# MySQL / Oracle execution-plan workshop

MySQL has now executed successfully on 8.4.11; see [mysql-report.json](mysql-report.json) and [mysql-plans.txt](mysql-plans.txt). Oracle Free 23.26.3 also passed; see [oracle-report.json](oracle-report.json) and [oracle-plans.txt](oracle-plans.txt). This does not certify Oracle 19c. SQLite/H2 results are not substituted for either engine.

1. Choose a disposable schema in MySQL 8.4 or an appropriate Oracle 19c environment. Use your client's secure connection method; do not put passwords in shell history or this repository.
2. Run mysql.sql or oracle.sql through the corresponding client. The table name is nb_tickets and the index is nb_tickets_lookup. Scripts deliberately contain no DROP commands; use a fresh schema rather than automatically deleting existing data.
3. Confirm 1,000 seeded rows. Record engine version, row distribution, query and parameter types, before/after plans, actual rows/loops or buffers, elapsed samples and cache conditions.
4. In Oracle, collect the indicated cursor's runtime statistics and use its observed SQL_ID/child number. Diagnostic privileges may be needed. DDL can commit implicitly, so keep unrelated work out of the session.
5. Compare the query with and without a fixed status predicate. Explain a chosen scan or sort instead of forcing the expected index blindly.

Small synthetic data does not determine production performance. EXPLAIN ANALYZE and the Oracle measured SELECT execute reads; run them in an appropriate environment. Retain observed failures and plan changes. The disposable Docker runner provisions the actual engine and records its version/image digest. It also restores a MySQL logical backup into a separate database and reconciles every row.

## Recorded MySQL evidence

| Item | Recorded observation |
| --- | --- |
| Engine/version | MySQL 8.4.11, disposable Docker container |
| Seed count | 1,000 rows |
| Baseline | Full table scan, filtered matches, sort, LIMIT 20 |
| Indexed query | Covering index lookup on tenant/status; returns 20 without explicit sort |
| Without status equality | Tenant index lookup still requires sorting |
| Backup/restore | Separate restored database; all 1,000 rows and fields matched |

The timings in mysql-plans.txt came from a tiny dataset on a shared machine and are not capacity estimates. See oracle-report.json for the independently recorded Oracle attempt; do not copy MySQL observations into Oracle's result.


Oracle seeded 1,000 rows, collected optimizer statistics, captured EXPLAIN PLAN and the executed cursor with ALLSTATS LAST, and observed full table access before the index and an index range scan afterward. An earlier readiness failure is retained: the CDB answered a query before FREEPDB1 was open. The runner now waits for READ WRITE.

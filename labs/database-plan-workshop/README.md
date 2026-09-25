# MySQL / Oracle execution-plan workshop

These are engine-specific teaching scripts, not recorded passing engine tests. The notebook's executed SQLite/H2 experiments do not establish their execution plans.

1. Choose a disposable schema in MySQL 8.4 or an appropriate Oracle 19c environment. Use your client's secure connection method; do not put passwords in shell history or this repository.
2. Run mysql.sql or oracle.sql through the corresponding client. The table name is nb_tickets and the index is nb_tickets_lookup. Scripts deliberately contain no DROP commands; use a fresh schema rather than automatically deleting existing data.
3. Confirm 1,000 seeded rows. Record engine version, row distribution, query and parameter types, before/after plans, actual rows/loops or buffers, elapsed samples and cache conditions.
4. In Oracle, collect the indicated cursor's runtime statistics and use its observed SQL_ID/child number. Diagnostic privileges may be needed. DDL can commit implicitly, so keep unrelated work out of the session.
5. Compare the query with and without a fixed status predicate. Explain a chosen scan or sort instead of forcing the expected index blindly.

Small synthetic data does not determine production performance. EXPLAIN ANALYZE and the Oracle measured SELECT execute reads; run them in an appropriate environment. Retain observed failures and plan changes. No MySQL or Oracle server was provisioned by writing these files.

## Evidence worksheet

| Item | Recorded observation |
| --- | --- |
| Engine/version and schema | NOT RUN |
| Seed count and distribution | NOT RUN |
| Baseline plan and actual work | NOT RUN |
| Indexed plan and actual work | NOT RUN |
| Changed-query plan | NOT RUN |
| Correctness and performance interpretation | NOT RUN |

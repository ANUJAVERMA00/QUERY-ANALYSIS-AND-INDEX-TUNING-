-- ================================================================
--  DBA Lab — Complete SQL Setup Script
--  File    : sql/setup.sql
--  Run as  : root (or admin user)
--  Server  : MySQL 8.0+  |  Port 3306
--  DB      : market_db
-- ================================================================


-- ── 0. DATABASE ──────────────────────────────────────────────────
DROP DATABASE IF EXISTS market_db;
CREATE DATABASE market_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE market_db;


-- ── 1. CORE TABLE (no idx_symbol — Phase 1 baseline) ─────────────
CREATE TABLE market_records (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol      VARCHAR(10)     NOT NULL COMMENT 'Crypto ticker e.g. BTC',
    price       DECIMAL(18, 6)  NOT NULL,
    volume      DECIMAL(18, 6)  NOT NULL DEFAULT 0,
    `timestamp` DATETIME        NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_timestamp (`timestamp`)
    -- NOTE: idx_symbol is ABSENT here intentionally.
    --       Section 5 below adds it to simulate Phase 2.
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '100,000-row crypto market dataset for DBA benchmarking';


-- ── 2. AUDIT TABLE ───────────────────────────────────────────────
CREATE TABLE audit_log (
    log_id      INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    record_id   INT UNSIGNED    NOT NULL,
    symbol      VARCHAR(10)     NOT NULL,
    old_price   DECIMAL(18, 6)  NOT NULL,
    new_price   DECIMAL(18, 6)  NOT NULL,
    changed_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by  VARCHAR(64)     NOT NULL DEFAULT (CURRENT_USER()),
    PRIMARY KEY (log_id),
    INDEX idx_audit_symbol (symbol),
    INDEX idx_audit_time   (changed_at)
) ENGINE = InnoDB
  COMMENT = 'Populated automatically by the price_update_audit trigger';


-- ── 3. TRIGGER — price_update_audit ─────────────────────────────
DELIMITER $$

CREATE TRIGGER price_update_audit
AFTER UPDATE ON market_records
FOR EACH ROW
BEGIN
    IF OLD.price <> NEW.price THEN
        INSERT INTO audit_log (record_id, symbol, old_price, new_price)
        VALUES (OLD.id, OLD.symbol, OLD.price, NEW.price);
    END IF;
END$$

DELIMITER ;

-- Verify trigger was created
SHOW TRIGGERS LIKE 'market_records';


-- ── 4. PHASE 1 VALIDATION (run BEFORE adding idx_symbol) ─────────
--
--  EXPLAIN SELECT SQL_NO_CACHE id, symbol, price, `timestamp`
--  FROM   market_records IGNORE INDEX (idx_symbol)
--  WHERE  symbol = 'BTC'
--  LIMIT  500;
--
--  Expected: type = ALL, rows ≈ 100000  →  Full Table Scan


-- ── 5. PHASE 2 — ADD B-TREE INDEX ON symbol ──────────────────────
ALTER TABLE market_records
    ADD INDEX idx_symbol (symbol);

-- Composite index — bonus optimisation for symbol + time-range queries
ALTER TABLE market_records
    ADD INDEX idx_symbol_time (symbol, `timestamp`);

-- Confirm indexes
SHOW INDEX FROM market_records;


-- ── 6. PHASE 2 VALIDATION ────────────────────────────────────────
--
--  EXPLAIN SELECT SQL_NO_CACHE id, symbol, price, `timestamp`
--  FROM   market_records USE INDEX (idx_symbol)
--  WHERE  symbol = 'BTC'
--  LIMIT  500;
--
--  Expected: type = ref, key = idx_symbol, rows ≈ 5000


-- ── 7. USER PRIVILEGES ───────────────────────────────────────────
DROP USER IF EXISTS 'developer_user'@'localhost';
DROP USER IF EXISTS 'viewer_user'@'localhost';

-- developer_user: full DML + DDL (Flask backend admin endpoints)
CREATE USER 'developer_user'@'localhost'
    IDENTIFIED BY 'Dev@Secure123';

GRANT SELECT, INSERT, UPDATE, DELETE,
      CREATE, ALTER, INDEX, DROP,
      REFERENCES, SHOW VIEW,
      CREATE ROUTINE, ALTER ROUTINE, EXECUTE
ON market_db.*
TO 'developer_user'@'localhost';

-- viewer_user: read-only (all benchmark queries)
CREATE USER 'viewer_user'@'localhost'
    IDENTIFIED BY 'View@Readonly456';

GRANT SELECT ON market_db.*
TO 'viewer_user'@'localhost';

FLUSH PRIVILEGES;

SHOW GRANTS FOR 'developer_user'@'localhost';
SHOW GRANTS FOR 'viewer_user'@'localhost';


-- ── 8. SERVER VARIABLE REFERENCE ─────────────────────────────────
-- Set in my.ini (Windows) or my.cnf (Linux) — requires server restart.
--
-- [mysqld]
-- innodb_buffer_pool_size        = 1G     # default: 128M
-- innodb_buffer_pool_instances   = 2
-- innodb_log_file_size           = 256M
-- innodb_flush_log_at_trx_commit = 1
-- max_connections                = 200
-- slow_query_log                 = ON
-- long_query_time                = 0.5
-- log_queries_not_using_indexes  = ON

-- Check current values
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'max_connections';
SHOW VARIABLES LIKE 'version';


-- ── 9. TABLE SIZE REPORT ─────────────────────────────────────────
SELECT
    TABLE_NAME,
    FORMAT(TABLE_ROWS, 0)                             AS approx_rows,
    CONCAT(ROUND(DATA_LENGTH  / 1048576, 1), ' MB')  AS data_size,
    CONCAT(ROUND(INDEX_LENGTH / 1048576, 1), ' MB')  AS index_size
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'market_db';

-- ================================================================
-- END OF SETUP SCRIPT
-- ================================================================
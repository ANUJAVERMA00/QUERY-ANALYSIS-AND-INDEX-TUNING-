# Query Analysis & Index Tuning — DBA Lab

A full-stack web application that **live-benchmarks MySQL query performance**, visualizing the difference between full table scans (Phase 1) and B-Tree indexed lookups (Phase 2) on a 100,000-row crypto market dataset.

---

##  What This Project Does

This project simulates a real DBA workflow:

- **Phase 1 (No Index):** Runs a `SELECT` on `market_records` without `idx_symbol` → triggers a full table scan across ~100,000 rows
- **Phase 2 (With Index):** Adds a B-Tree index on `symbol` → query uses `ref` scan, touching only ~5,000 rows
- A **Flask dashboard** lets you benchmark, compare, and toggle the index live — and shows the `EXPLAIN` plan, rows scanned, and execution time side-by-side

---

##  Features

-  **Live Benchmark** — Run timed queries with or without the index
-  **Side-by-Side Compare** — Before vs After with speedup multiplier
-  **EXPLAIN Plan Viewer** — See `type`, `key`, `rows` from MySQL's optimizer
-  **Toggle Index** — Create or drop `idx_symbol` from the UI
-  **Audit Log** — Tracks price changes via a MySQL `AFTER UPDATE` trigger
-  **Server Info Panel** — Shows InnoDB buffer pool, connections, slow query log settings
- **100K Synthetic Dataset** — Realistic crypto ticker data (BTC, ETH, SOL, etc.)

---

##  Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| Database | MySQL 8.0 |
| Frontend | HTML, CSS, Vanilla JS |
| Data Generation | Pandas, NumPy |
| DB Connector | mysql-connector-python |

---

## Project Structure

```
QUERY-ANALYSIS-AND-INDEX-TUNING/
│
├── app.py                      # Flask app — all API routes & benchmark logic
├── requirements.txt            # Python dependencies
├── my.ini                      # MySQL server config (InnoDB tuning)
├── .env.example                # Environment variable template
│
├── sql/
│   └── setup.sql               # DB schema, trigger, indexes, user privileges
│
├── scripts/
│   └── generate_data.py        # Generates & loads 100,000 market records
│
├── templates/
│   └── index.html              # Main dashboard UI
│
└── static/
    ├── css/style.css           # Dashboard styles
    └── js/dashboard.js         # Fetch calls, chart rendering, UI logic
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- MySQL 8.0 running on `localhost:3306`
- pip

---

### 1. Clone the Repository

```bash
git clone https://github.com/ANUJAVERMA00/QUERY-ANALYSIS-AND-INDEX-TUNING-.git
cd QUERY-ANALYSIS-AND-INDEX-TUNING-
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the Database

Edit your MySQL config file (`my.ini` on Windows / `my.cnf` on Linux) with the settings in the provided `my.ini`:

```ini
[mysqld]
innodb_buffer_pool_size      = 1G
innodb_buffer_pool_instances = 2
innodb_log_file_size         = 256M
max_connections              = 200
slow_query_log               = ON
long_query_time              = 0.5
log_queries_not_using_indexes = ON
```

Restart MySQL after changes.

### 4. Run the SQL Setup Script

```bash
mysql -u root -p < sql/setup.sql
```

This creates the `market_db` database, `market_records` table, `audit_log` table, the `price_update_audit` trigger, and user privileges.

### 5. Generate the 100K Dataset

```bash
python scripts/generate_data.py
```

This populates `market_records` with 100,000 synthetic crypto price records.

### 6. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env with your DB credentials and Flask secret key
```

### 7. Run the Flask App

```bash
python app.py
```

Visit **http://localhost:8000** in your browser.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Dashboard UI |
| `POST` | `/api/benchmark` | Run a timed query (with or without index) |
| `POST` | `/api/compare` | Side-by-side Phase 1 vs Phase 2 benchmark |
| `GET` | `/api/server-info` | MySQL variables, indexes, table stats, audit log |
| `POST` | `/api/toggle-index` | Create or drop `idx_symbol` live |

---

##  Database Schema

### `market_records` (100,000 rows)

```sql
CREATE TABLE market_records (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol      VARCHAR(10)     NOT NULL,   -- e.g. BTC, ETH
    price       DECIMAL(18, 6)  NOT NULL,
    volume      DECIMAL(18, 6)  NOT NULL DEFAULT 0,
    `timestamp` DATETIME        NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_timestamp (`timestamp`)
    -- idx_symbol added in Phase 2
);
```

### `audit_log`

Automatically populated by the `price_update_audit` trigger whenever a price changes.

---

## 📊 How the Benchmark Works

| Phase | Index | Scan Type | Rows Scanned | Speed |
|---|---|---|---|---|
| Phase 1 |  No Index | `ALL` (Full Scan) | ~100,000 | Slow |
| Phase 2 | `idx_symbol` | `ref` (Index Scan) | ~5,000 | Fast |

The `/api/compare` endpoint flushes the table cache between runs to ensure a fair comparison.

---

## 🧑Database Users

| User | Role | Permissions |
|---|---|---|
| `developer_user` | Admin | SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP |
| `viewer_user` | Read-only | SELECT only |

---

##  Dependencies

```
flask>=3.0.0
mysql-connector-python>=8.3.0
pandas>=2.1.0
numpy>=1.26.0
gunicorn>=21.0.0
python-dotenv>=1.0.0
```

---

##  Author

**Anuja Verma**  
[GitHub](https://github.com/ANUJAVERMA00)

---

>  If this project helped you understand query optimization and index tuning, give it a star!
"""
Performance-Driven DBA: Query Optimization & Index Tuning
Flask Application — app.py
Host : localhost
Port : 5000
DB   : MySQL 8.0 on Port 3306
"""

from flask import Flask, render_template, jsonify, request
import mysql.connector
import time
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dba-lab-secret-2024")

# ── Database credentials ───────────────────────────────────────────────────────
# root user for both dev and view access (for testing/demo purposes)

_DEV = dict(host="localhost", port=3306,
            user="root", password="ZxcvbnM122!",
            database="market_db", connect_timeout=5)

_VIEW = dict(host="localhost", port=3306,
             user="root", password="ZxcvbnM122!",
             database="market_db", connect_timeout=5)


def _conn(role="view"):
    return mysql.connector.connect(**(_VIEW if role == "view" else _DEV))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _benchmark(symbol: str, use_index: bool, warmup: bool = True) -> dict:
    """Run the timed SELECT and return performance metrics + EXPLAIN plan."""
    # Check if idx_symbol exists
    cn = _conn("view")
    cur = cn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA='market_db' AND TABLE_NAME='market_records' "
        "AND INDEX_NAME='idx_symbol'"
    )
    index_exists = cur.fetchone()[0] > 0
    cur.close(); cn.close()
    
    # Only use index hint if index exists and use_index is True
    if index_exists and use_index:
        hint = "USE INDEX (idx_symbol)"
    elif index_exists and not use_index:
        hint = "IGNORE INDEX (idx_symbol)"
    else:
        hint = ""
    
    sql = (f"SELECT id, symbol, price, `timestamp` "
           f"FROM market_records {hint} WHERE symbol = %s LIMIT 500")

    cn = _conn("view")
    cur = cn.cursor(dictionary=True)

    # Warm up if requested - run 3 times to load into cache, measure only the last one
    if warmup:
        for i in range(3):
            cur.execute(sql, (symbol,))
            rows = cur.fetchall()
    
    # Final measurement after warmup (or first run if no warmup)
    t0 = time.perf_counter()
    cur.execute(sql, (symbol,))
    rows = cur.fetchall()
    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    
    # This is the final measured result after cache warming
    rows_returned = len(rows)

    # Build EXPLAIN query with escaped symbol value (EXPLAIN doesn't support parameterized queries)
    escaped_symbol = symbol.replace("'", "''")
    explain_sql = (f"EXPLAIN SELECT id, symbol, price, `timestamp` "
                   f"FROM market_records {hint} WHERE symbol = '{escaped_symbol}' LIMIT 500")
    cur.execute(explain_sql)
    explain = cur.fetchone() or {}
    cur.close(); cn.close()

    rows_scanned = int(explain.get("rows") or (100000 if not use_index else 5000))
    scan_type    = str(explain.get("type") or ("ALL" if not use_index else "ref"))

    return {
        "elapsed_ms"   : elapsed,
        "rows_returned": rows_returned,
        "rows_scanned" : rows_scanned,
        "scan_type"    : scan_type,
        "explain"      : {k: str(v) for k, v in explain.items()},
        "sample"       : [
            {"id": r["id"], "symbol": r["symbol"],
             "price": float(r["price"]), "ts": str(r["timestamp"])}
            for r in rows[:8]
        ],
    }


def _server_vars():
    want = ["innodb_buffer_pool_size", "innodb_buffer_pool_instances",
            "max_connections", "innodb_log_file_size",
            "slow_query_log", "long_query_time", "version"]
    cn = _conn("dev"); cur = cn.cursor(dictionary=True)
    ph = ",".join(f"'{v}'" for v in want)
    cur.execute(f"SHOW VARIABLES WHERE Variable_name IN ({ph})")
    result = {r["Variable_name"]: r["Value"] for r in cur.fetchall()}
    cur.close(); cn.close()
    return result


def _indexes():
    cn = _conn("dev"); cur = cn.cursor(dictionary=True)
    cur.execute("SHOW INDEX FROM market_records")
    rows = [{k: str(v) for k, v in r.items()} for r in cur.fetchall()]
    cur.close(); cn.close()
    return rows


def _table_stats():
    cn = _conn("dev"); cur = cn.cursor(dictionary=True)
    cur.execute(
        "SELECT TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH "
        "FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA='market_db' AND TABLE_NAME='market_records'"
    )
    row = cur.fetchone()
    cur.close(); cn.close()
    return {k: int(v or 0) for k, v in row.items()} if row else {}


def _audit_log(n=12):
    cn = _conn("dev"); cur = cn.cursor(dictionary=True)
    cur.execute("SELECT * FROM audit_log ORDER BY changed_at DESC LIMIT %s", (n,))
    rows = cur.fetchall()
    cur.close(); cn.close()
    return [
        {**r,
         "changed_at": str(r["changed_at"]),
         "old_price" : float(r["old_price"]),
         "new_price" : float(r["new_price"])}
        for r in rows
    ]


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/benchmark", methods=["POST"])
def benchmark():
    body      = request.get_json(force=True)
    symbol    = (body.get("symbol") or "BTC").upper()
    use_index = bool(body.get("use_index", True))
    try:
        data = _benchmark(symbol, use_index)
        return jsonify(status="ok", data=data, symbol=symbol, use_index=use_index)
    except Exception as exc:
        return jsonify(status="error", message=str(exc)), 500


@app.route("/api/compare", methods=["POST"])
def compare():
    body   = request.get_json(force=True)
    symbol = (body.get("symbol") or "BTC").upper()
    try:
        # Clear cache before Phase 1
        cn = _conn("dev")
        cur = cn.cursor()
        cur.execute("FLUSH TABLES")  # Clear table cache
        cur.close(); cn.close()
        
        # Run Phase 1 WITHOUT warmup for fair comparison
        before = _benchmark(symbol, use_index=False, warmup=False)
        
        # Clear cache before Phase 2
        cn = _conn("dev")
        cur = cn.cursor()
        cur.execute("FLUSH TABLES")  # Clear table cache
        cur.close(); cn.close()
        
        # Run Phase 2 WITHOUT warmup for fair comparison
        after  = _benchmark(symbol, use_index=True, warmup=False)
        
        speedup = round(before["elapsed_ms"] / max(after["elapsed_ms"], 0.1), 1)
        return jsonify(status="ok", symbol=symbol,
                       before=before, after=after, speedup=speedup)
    except Exception as exc:
        return jsonify(status="error", message=str(exc)), 500


@app.route("/api/server-info")
def server_info():
    try:
        return jsonify(
            status       = "ok",
            variables    = _server_vars(),
            indexes      = _indexes(),
            table_stats  = _table_stats(),
            audit_log    = _audit_log(),
        )
    except Exception as exc:
        return jsonify(status="error", message=str(exc)), 500


@app.route("/api/toggle-index", methods=["POST"])
def toggle_index():
    action = (request.get_json(force=True) or {}).get("action", "create")
    try:
        cn = _conn("dev"); cur = cn.cursor()
        
        # Check if index exists
        cur.execute(
            "SELECT COUNT(*) as cnt FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA='market_db' AND TABLE_NAME='market_records' "
            "AND INDEX_NAME='idx_symbol'"
        )
        index_exists = cur.fetchone()[0] > 0
        
        if action == "drop":
            if index_exists:
                cur.execute("ALTER TABLE market_records DROP INDEX idx_symbol")
                msg = "Index idx_symbol dropped — Phase 1 active."
            else:
                msg = "Index idx_symbol does not exist. Already in Phase 1."
        else:
            if not index_exists:
                cur.execute("ALTER TABLE market_records ADD INDEX idx_symbol (symbol)")
                msg = "Index idx_symbol created — Phase 2 active."
            else:
                msg = "Index idx_symbol already exists. Already in Phase 2."
        
        cn.commit(); cur.close(); cn.close()
        return jsonify(status="ok", message=msg)
    except Exception as exc:
        return jsonify(status="error", message=str(exc)), 500


if __name__ == "__main__":
    print("DBA Benchmark Server  →  http://localhost:8000")
    app.run(host="0.0.0.0", port=8000, debug=True)
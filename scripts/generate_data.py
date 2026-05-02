"""
scripts/generate_data.py
Generates 100,000 synthetic crypto market records using Pandas + NumPy.

Usage:
    python scripts/generate_data.py

Pre-requisites:
    pip install pandas numpy mysql-connector-python
    Make sure setup.sql has already been run.
"""

import pandas as pd
import numpy as np
import mysql.connector
from datetime import datetime, timedelta
import time

# ── Config ─────────────────────────────────────────────────
DB = dict(
    host     = "localhost",
    port     = 3306,
    user     = "root",
    password = "ZxcvbnM122!",      # change if needed
    database = "market_db",
)

NUM_RECORDS = 100_000
BATCH_SIZE  = 5_000

SYMBOLS = [
    "BTC","ETH","BNB","SOL","XRP","ADA","DOGE","AVAX","DOT","MATIC",
    "LINK","LTC","UNI","ATOM","XLM","ALGO","VET","FIL","THETA","TRX",
]

WEIGHTS = [
    .20,.15,.08,.07,.06,
    .05,.05,.04,.04,.04,
    .03,.03,.03,.02,.02,
    .02,.02,.02,.01,.01,
]

BASE_PRICES = {
    "BTC":42000,"ETH":2500,"BNB":310,"SOL":100,"XRP":.55,
    "ADA":.45,"DOGE":.08,"AVAX":35,"DOT":7,"MATIC":.85,
    "LINK":14,"LTC":75,"UNI":6,"ATOM":9,"XLM":.11,
    "ALGO":.17,"VET":.025,"FIL":5,"THETA":1.1,"TRX":.11,
}


def generate(n: int) -> pd.DataFrame:
    print(f"  Generating {n:,} records …")
    rng     = np.random.default_rng(42)
    symbols = rng.choice(SYMBOLS, size=n, p=WEIGHTS)
    bases   = np.array([BASE_PRICES[s] for s in symbols])
    prices  = np.round(bases * (1 + rng.uniform(-.05, .05, n)), 6)
    volumes = np.round(rng.uniform(.001, 500, n), 6)
    start   = datetime(2024, 1, 1)
    offsets = rng.integers(0, 365 * 86400, n)
    stamps  = [start + timedelta(seconds=int(o)) for o in offsets]
    df = pd.DataFrame({"symbol": symbols, "price": prices,
                       "volume": volumes, "timestamp": stamps})
    print(f"  Done — {len(df):,} rows ready")
    return df


def load(df: pd.DataFrame):
    cn  = mysql.connector.connect(**DB)
    cur = cn.cursor()
    print("  Truncating existing data …")
    cur.execute("TRUNCATE TABLE market_records")
    cn.commit()

    records = list(df.itertuples(index=False, name=None))
    sql     = ("INSERT INTO market_records (symbol, price, volume, `timestamp`) "
               "VALUES (%s, %s, %s, %s)")
    t0 = time.time()
    for i in range(0, len(records), BATCH_SIZE):
        cur.executemany(sql, records[i : i + BATCH_SIZE])
        cn.commit()
        done = min(i + BATCH_SIZE, len(records))
        print(f"  {done:,} / {len(records):,}  ({done/len(records)*100:.0f}%)", end="\r")

    print(f"\n  Loaded {len(records):,} rows in {time.time()-t0:.1f}s")
    cur.close(); cn.close()


def seed_audit():
    cn  = mysql.connector.connect(**DB)
    cur = cn.cursor()
    cur.executemany(
        "INSERT INTO audit_log (record_id, symbol, old_price, new_price) VALUES (%s,%s,%s,%s)",
        [(1,"BTC",41800.00,42150.50),(2,"ETH",2480.00,2510.75),(3,"SOL",98.30,101.20)]
    )
    cn.commit(); cur.close(); cn.close()
    print("  Audit log seeded with 3 demo rows")


if __name__ == "__main__":
    print("\n=== DBA Lab · Data Generator ===\n")
    print("[1/3] Generating …"); df = generate(NUM_RECORDS)
    print("[2/3] Loading into MySQL …"); load(df)
    print("[3/3] Seeding audit log …"); seed_audit()
    print("\nDone! market_db is ready.\n")
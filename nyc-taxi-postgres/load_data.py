"""Load NYC yellow taxi trips (Parquet) and the zone lookup (CSV) into PostgreSQL.

Run from this folder:  python load_data.py
Connection: database `nyc_taxi` on localhost. The password is NOT in this file;
libpq reads it from pgpass.conf (Windows: %APPDATA%\\postgresql\\pgpass.conf),
or set the PGPASSWORD environment variable.
"""
import csv
import glob
import os

import psycopg
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CONN = os.environ.get("NYC_TAXI_DSN", "host=localhost dbname=nyc_taxi user=postgres")

TRIPS_DDL = """
DROP TABLE IF EXISTS trips_raw;
CREATE TABLE trips_raw (
    vendor_id              integer,
    pickup_at              timestamp,
    dropoff_at             timestamp,
    passenger_count        integer,
    trip_distance          double precision,
    rate_code_id           integer,
    store_and_fwd_flag     text,
    pu_location_id         integer,
    do_location_id         integer,
    payment_type           integer,
    fare_amount            double precision,
    extra                  double precision,
    mta_tax                double precision,
    tip_amount             double precision,
    tolls_amount           double precision,
    improvement_surcharge  double precision,
    total_amount           double precision,
    congestion_surcharge   double precision,
    airport_fee            double precision,
    cbd_congestion_fee     double precision,
    request_source         text,
    source_file            text
);
"""

ZONES_DDL = """
DROP TABLE IF EXISTS zones;
CREATE TABLE zones (
    location_id  integer PRIMARY KEY,
    borough      text,
    zone         text,
    service_zone text
);
"""

# Parquet column order -> trips_raw column order (source_file is appended)
PARQUET_COLUMNS = [
    "VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count",
    "trip_distance", "RatecodeID", "store_and_fwd_flag", "PULocationID", "DOLocationID",
    "payment_type", "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
    "improvement_surcharge", "total_amount", "congestion_surcharge", "Airport_fee",
    "cbd_congestion_fee", "request_source",
]


def clean(value):
    """Parquet nulls arrive as None; NaN floats must also become NULL."""
    if value is None or (isinstance(value, float) and value != value):
        return None
    return value


def load_trips(conn):
    conn.execute(TRIPS_DDL)
    for path in sorted(glob.glob(os.path.join(DATA, "yellow_tripdata_*.parquet"))):
        name = os.path.basename(path)
        pf = pq.ParquetFile(path)
        total = 0
        with conn.cursor() as cur, cur.copy("COPY trips_raw FROM STDIN") as copy:
            for batch in pf.iter_batches(batch_size=200_000, columns=PARQUET_COLUMNS):
                cols = [batch.column(c).to_pylist() for c in PARQUET_COLUMNS]
                for row in zip(*cols):
                    copy.write_row([clean(v) for v in row] + [name])
                total += batch.num_rows
        print(f"{name}: {total:,} rows loaded")


def load_zones(conn):
    conn.execute(ZONES_DDL)
    with open(os.path.join(DATA, "taxi_zone_lookup.csv"), newline="", encoding="utf-8") as f, \
            conn.cursor() as cur, cur.copy("COPY zones FROM STDIN") as copy:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            copy.write_row([int(row[0]), row[1], row[2], row[3]])
    print("zones loaded")


if __name__ == "__main__":
    with psycopg.connect(CONN, autocommit=True) as conn:
        load_trips(conn)
        load_zones(conn)
        conn.execute("ANALYZE trips_raw")
        n = conn.execute("SELECT count(*) FROM trips_raw").fetchone()[0]
        print(f"trips_raw total: {n:,}")

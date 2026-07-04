#!/usr/bin/env python3
"""Block until Postgres accepts connections, or fail after --timeout seconds.
Called by entrypoint.sh before exec'ing Odoo so the worker does not crash
when the DB service is slower to start than the app container."""
import argparse
import sys
import time

import psycopg2


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db_host", required=True)
    p.add_argument("--db_port", required=True)
    p.add_argument("--db_user", required=True)
    p.add_argument("--db_password", required=True)
    p.add_argument("--timeout", type=int, default=5)
    args = p.parse_args()

    start = time.time()
    error = ""
    while (time.time() - start) < args.timeout:
        try:
            conn = psycopg2.connect(
                user=args.db_user,
                host=args.db_host,
                port=args.db_port,
                password=args.db_password,
                dbname="postgres",
            )
            error = ""
            conn.close()
            break
        except psycopg2.OperationalError as e:
            error = e
        time.sleep(1)

    if error:
        print(f"Database connection failure: {error}", file=sys.stderr)
        sys.exit(1)

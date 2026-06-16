"""Phase 5 / CDC — register (or update) the Debezium Postgres connector.

POSTs the connector config to the Kafka Connect REST API. Debezium then takes an
initial snapshot of public.film_lifecycle and streams every subsequent change to
the Kafka topic `flicker_cdc.public.film_lifecycle`.

Converters are pinned per-connector to JSON WITHOUT schemas, so each message is a
compact change envelope: {before, after, source, op, ts_ms}. op = c(reate) /
u(pdate) / d(elete) / r(ead, i.e. snapshot).

Usage:
    python streaming/cdc/register_connector.py            # create/update
    python streaming/cdc/register_connector.py --status   # show status only
    python streaming/cdc/register_connector.py --delete    # remove connector
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

CONNECT_URL = os.getenv("CONNECT_URL", "http://localhost:8083")
NAME = "flicker-postgres-connector"

CONFIG = {
    "name": NAME,
    "config": {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        "tasks.max": "1",
        "database.hostname": "postgres",     # service name on the compose network
        "database.port": "5432",
        "database.user": "flicker",
        "database.password": "flicker",
        "database.dbname": "flicker_ops",
        "topic.prefix": "flicker_cdc",
        "table.include.list": "public.film_lifecycle",
        "plugin.name": "pgoutput",            # built into modern Postgres
        "publication.autocreate.mode": "filtered",
        "slot.name": "flicker_slot",
        "snapshot.mode": "initial",
        "decimal.handling.mode": "double",    # NUMERIC -> plain float, not base64
        # compact JSON output (no per-message schema)
        "key.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "key.converter.schemas.enable": "false",
        "value.converter.schemas.enable": "false",
    },
}


def _req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{CONNECT_URL}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--delete", action="store_true")
    args = ap.parse_args()

    if args.delete:
        code, _ = _req("DELETE", f"/connectors/{NAME}")
        print(f"DELETE {NAME} -> {code}")
        return

    if args.status:
        code, body = _req("GET", f"/connectors/{NAME}/status")
        print(json.dumps(body, indent=2) if code == 200 else f"not found ({code})")
        return

    # PUT the config (idempotent create-or-update)
    code, body = _req("PUT", f"/connectors/{NAME}/config", CONFIG["config"])
    if code in (200, 201):
        print(f"Connector '{NAME}' registered (HTTP {code}).")
        print("Topic: flicker_cdc.public.film_lifecycle")
    else:
        print(f"FAILED (HTTP {code}):\n{json.dumps(body, indent=2)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

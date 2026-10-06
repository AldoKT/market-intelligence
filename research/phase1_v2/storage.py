"""Immutable Parquet batches, source preservation and explicit promotion."""
from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import uuid
import pyarrow.parquet as pq
import pyarrow as pa
from .contracts import FIELDS, KEYS, SCHEMAS, aware_time, digest, now, prepare

def write_json(path, body):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(body, stream, indent=2, default=str, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)

@contextmanager
def exclusive(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, str(os.getpid()).encode())
        yield
    finally:
        os.close(fd)
        path.unlink()

class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_source(self, source_bytes):
        sha = hashlib.sha256(source_bytes).hexdigest()
        path = self.root / "sources" / (sha + ".blob")
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise ValueError("source blob integrity failure; human review required")
            return sha
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(sha + "." + uuid.uuid4().hex + ".tmp")
        with temp.open("xb") as stream:
            stream.write(source_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        return sha

    def ingest(self, table, rows, *, source_bytes, source_file=None, source_endpoint=None,
               retrieved_at=None, provenance="legacy_candidate", request=None):
        if provenance not in ("legacy_candidate", "api", "cache_candidate"):
            raise ValueError("invalid provenance")
        with exclusive(self.root / ".write.lock"):
            sha = self.save_source(source_bytes)
            if provenance != "api":
                for manifest_path in (self.root / "batches" / table).glob("*.json"):
                    previous = json.loads(manifest_path.read_text(encoding="utf-8"))
                    if (previous["source_sha256"], previous["source_file"], previous["provenance"]) == (sha, source_file, provenance):
                        return previous
            batch = uuid.uuid4().hex
            accepted, failures, keys = [], [], {}
            for index, original in enumerate(rows):
                try:
                    row = prepare(table, original)
                    if request and table != "broker_registry":
                        if row.get("symbol") != request["symbol"] or not date.fromisoformat(request["start"]) <= row["date"] <= date.fromisoformat(request["end"]):
                            raise ValueError("response row outside requested symbol/date window")
                    key = tuple(row[k] for k in KEYS[table])
                    if key in keys:
                        if keys[key] == row:
                            continue
                        raise ValueError("conflicting duplicate key within source batch")
                    keys[key] = dict(row)
                    row.update(source_file=source_file, source_endpoint=source_endpoint, source_sha256=sha,
                               imported_at=now(), retrieved_at=aware_time(retrieved_at), retrieved_at_original=retrieved_at,
                               validation_status="validated_api" if provenance == "api" else "legacy_candidate",
                               provenance=provenance, batch_id=batch)
                    accepted.append(row)
                except (ValueError, TypeError, KeyError) as error:
                    failures.append({"row_index": index, "row_repr": repr(original), "reason": str(error)})
            # A partially invalid API response is preserved but not promoted.
            if failures:
                for row in accepted:
                    row["validation_status"] = "quarantined"
            folder = self.root / "batches" / table
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / (batch + ".parquet")
            pq.write_table(pa.Table.from_pylist(accepted, schema=SCHEMAS[table]), path, compression="zstd")
            manifest = {"batch_id": batch, "table": table, "source_sha256": sha,
                        "source_file": source_file, "source_endpoint": source_endpoint,
                        "provenance": provenance, "request": request, "imported_at": str(now()),
                        "retrieved_at": retrieved_at, "accepted_rows": len(accepted), "failures": failures,
                        "returned_dates": sorted({str(r["date"]) for r in accepted if "date" in r}),
                        "received_dates": sorted({str(r["date"]) for r in rows if r.get("date") is not None}),
                        "status": "quarantined" if failures else ("validated_api" if provenance == "api" else "legacy_candidate")}
            write_json(folder / (batch + ".json"), manifest)
            return manifest

    def rows(self, table, include_candidates=False):
        rows = []
        for path in sorted((self.root / "batches" / table).glob("*.parquet")):
            manifest = path.with_suffix(".json")
            if not manifest.exists():  # interrupted writes never become coverage
                continue
            info = json.loads(manifest.read_text(encoding="utf-8"))
            if info["status"] == "quarantined":
                continue
            status = info["status"]
            promotion = self.root / "promotions" / (info["batch_id"] + ".json")
            if promotion.exists():
                status = "validated_legacy"
            if status == "legacy_candidate" and not include_candidates:
                continue
            for row in pq.read_table(path).to_pylist():
                row["validation_status"] = status
                rows.append(row)
        return rows

    def promote_legacy(self, table, batch, *, reviewer, evidence):
        if not reviewer.strip() or not evidence.strip():
            raise ValueError("reviewer and source validation evidence required")
        manifest = json.loads((self.root / "batches" / table / (batch + ".json")).read_text(encoding="utf-8"))
        if manifest["status"] != "legacy_candidate":
            raise ValueError("only valid candidate batches can be promoted")
        write_json(self.root / "promotions" / (batch + ".json"), {"table": table, "batch_id": batch,
            "reviewer": reviewer, "evidence": evidence, "approved_at": str(now())})

    def merged(self, table, include_candidates=False):
        groups, conflicts = {}, []
        for row in self.rows(table, include_candidates):
            key = tuple(row[k] for k in KEYS[table])
            groups.setdefault(key, []).append(row)
        output = []
        for key, versions in groups.items():
            merged = dict(zip(KEYS[table], key))
            merged["revisions"] = [{field: r[field] for field in ("batch_id", "source_sha256", "validation_status", "source_file", "source_endpoint", "imported_at", "retrieved_at", "retrieved_at_original", "market_scope")} for r in versions]
            scopes = {r["market_scope"] for r in versions if r["market_scope"] is not None}
            merged["market_scope"] = next(iter(scopes)) if len(scopes) == 1 else None
            merged["scope_conflict"] = len(scopes) > 1
            blocked = []
            for field in FIELDS[table]:
                if field in KEYS[table]:
                    continue
                values = {}
                for row in versions:
                    if row[field] is not None:
                        values.setdefault(digest(row[field]), {"value": row[field], "sources": []})["sources"].append(row["source_sha256"])
                if len(values) > 1:
                    conflict = {"table": table, "key": list(key), "field": field, "versions": list(values.values())}
                    resolution = self.root / "decisions" / (digest([table, list(key), field]) + ".json")
                    decision = json.loads(resolution.read_text(encoding="utf-8")) if resolution.exists() else {}
                    fingerprint = digest(sorted(values))
                    choice = decision.get("value_hash") if decision.get("versions_hash") == fingerprint else None
                    if choice in values:
                        merged[field] = values[choice]["value"]
                        conflict["decision"] = decision
                    else:
                        blocked.append(field)
                        merged[field] = None
                    conflicts.append(conflict)
                else:
                    merged[field] = next(iter(values.values()))["value"] if values else None
            try:
                prepare(table, merged)
            except (ValueError, TypeError) as error:
                merged["row_validation_error"] = str(error)
                blocked = [f for f in FIELDS[table] if f not in KEYS[table]]
                conflicts.append({"table": table, "key": list(key), "field": "__merged_row__", "reason": str(error)})
                for field in blocked:
                    merged[field] = None
            merged["blocked_fields"] = blocked
            output.append(merged)
        return sorted(output, key=lambda r: tuple(str(r[k]) for k in KEYS[table])), conflicts

    def resolve(self, table, key, field, value, *, reviewer, evidence):
        if not reviewer.strip() or not evidence.strip():
            raise ValueError("reviewer and evidence required")
        _, conflicts = self.merged(table, include_candidates=True)
        matching = [c for c in conflicts if [str(k) for k in c["key"]] == [str(k) for k in key] and c["field"] == field and "versions" in c]
        if len(matching) != 1:
            raise ValueError("conflict not found")
        c = matching[0]
        dtype = FIELDS[table][field]
        if pa.types.is_floating(dtype):
            value = float(value)
        hashes = sorted(digest(v["value"]) for v in c["versions"])
        if digest(value) not in hashes:
            raise ValueError("decision must select an existing source value")
        write_json(self.root / "decisions" / (digest([table, c["key"], field]) + ".json"),
                   {"reviewer": reviewer, "evidence": evidence, "approved_at": str(now()),
                    "value_hash": digest(value), "versions_hash": digest(hashes)})

    def attest_broker_coverage(self, symbol, session_date, *, reviewer, evidence):
        """Human source review certifies a full session, bound to its revisions."""
        if not reviewer.strip() or not evidence.strip():
            raise ValueError("reviewer and completeness evidence required")
        session_date = date.fromisoformat(str(session_date))
        rows, _ = self.merged("broker_activity")
        rows = [r for r in rows if (r["symbol"], r["date"]) == (symbol, session_date)]
        from .offline import REQUIRED
        if not rows or any(r["blocked_fields"] or any(r.get(f) is None for f in REQUIRED["broker_activity"]) for r in rows):
            raise ValueError("validated complete broker fields required")
        import math
        for buy, sell in (("buy_value_idr", "sell_value_idr"), ("buy_lots", "sell_lots"), ("buy_frequency", "sell_frequency")):
            if not math.isclose(sum(r[buy] for r in rows), sum(r[sell] for r in rows), rel_tol=1e-9, abs_tol=0.01):
                raise ValueError("broker buy/sell totals do not reconcile")
        write_json(self.root / "coverage" / (digest([symbol, session_date]) + ".json"),
                   {"symbol": symbol, "date": str(session_date), "reviewer": reviewer, "evidence": evidence,
                    "approved_at": str(now()), "revisions_sha256": digest(rows)})

    def broker_complete_dates(self):
        rows, _ = self.merged("broker_activity")
        groups = {}
        for row in rows:
            groups.setdefault((row["symbol"], row["date"]), []).append(row)
        complete = set()
        for key, sessions in groups.items():
            path = self.root / "coverage" / (digest(list(key)) + ".json")
            if path.exists():
                info = json.loads(path.read_text(encoding="utf-8"))
                if info.get("reviewer") and info.get("evidence") and info.get("revisions_sha256") == digest(sessions):
                    complete.add(key)
        return complete

    def export(self, table, path):
        rows, conflicts = self.merged(table)
        clean = [{k: r.get(k) for k in FIELDS[table]} for r in rows if not r["blocked_fields"]]
        pq.write_table(pa.Table.from_pylist(clean, schema=pa.schema(FIELDS[table])), path, compression="zstd")
        write_json(Path(path).with_suffix(".provenance.json"), {"rows": rows, "conflicts": conflicts})
        return {"rows": len(clean), "conflicts": len(conflicts)}

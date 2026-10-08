"""Export only derived demo JSON. No credentials, network requests, or dependencies."""
import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def export(output):
    output = Path(output)
    def write(relative, payload):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    product = ROOT / "payloads/valid_baseline_v1"
    for source in product.rglob("*.json"):
        write(Path("product") / source.relative_to(product), json.loads(source.read_text(encoding="utf-8")))
    reaction = ROOT / "backend/app/data/reaction_validation.json"
    if reaction.exists():
        write("product/reaction-validation.json", json.loads(reaction.read_text(encoding="utf-8")))
    snapshot = json.loads((product / "manifest.json").read_text(encoding="utf-8"))["as_of"]
    archive = ROOT / "research/data/checkpoints/phase2_expansion28/valid_baseline_history.zip"
    prefix = "valid_baseline_history/broker_views/"
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read(prefix + "manifest.json"))
        histories = {symbol: {} for symbol in manifest["symbols"]}
        for name in z.namelist():
            if not name.startswith(prefix) or not name.endswith(".json"):
                continue
            relative = name[len(prefix):]
            if not relative.startswith(("sessions/", "episodes/")):
                continue
            payload = json.loads(z.read(name))
            write(Path("brokers") / relative, payload)
            if relative.startswith("sessions/"):
                symbol, day = relative.split("/")[1:]
                fields = ("bval", "sval", "blot", "slot", "bfreq", "sfreq", "nval", "nlot", "net_role")
                histories[symbol][day[:-5]] = {"quality": payload["quality"]["status"], "rows": {row["broker_code"]: {f: row[f] for f in fields} for row in payload["brokers"]}}
        for symbol, history in histories.items():
            dates = sorted(history)
            if not dates:
                raise ValueError(f"Missing broker sessions: {symbol}")
            write(f"brokers/index/{symbol}.json", {"symbol": symbol, "as_of": manifest["as_of"], "analysis_start": manifest["analysis_start"], "signal_snapshot": snapshot, "default_date": snapshot if snapshot in dates else None, "dates": dates, "episodes": [e for e in manifest["episodes"] if e["symbol"] == symbol], "source_completeness": "All returned rows retained; source completeness not independently verified."})
            write(f"brokers/history/{symbol}.json", history)
    total = sum(p.stat().st_size for p in output.rglob("*.json"))
    print(f"Static export: {len(histories)} stocks; {total / 1024 / 1024:.1f} MiB; no API requests.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    export(parser.parse_args().output)

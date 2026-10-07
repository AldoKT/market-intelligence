"""Offline reader and price/volume baselines for the Phase 1 JSON pilot."""
import hashlib
import json
import math
from pathlib import Path
from statistics import median

SYMBOLS = ('ANTM', 'INCO', 'BBCA')

def load_dataset(directory, symbols=SYMBOLS):
    directory = Path(directory)
    dataset = {}
    for name in ('daily', 'foreign_flow', 'broker_activity', 'broker_registry'):
        dataset[name] = json.loads((directory / (name + '.json')).read_text(encoding='utf-8'))
    daily = dataset['daily']
    keys = [(r['symbol'], r['date']) for r in daily]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate daily key')
    for row in daily:
        if row['symbol'] not in symbols:
            raise ValueError('Unexpected pilot symbol')
        for field in ('open', 'high', 'low', 'close', 'volume'):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError('Invalid daily field: ' + field)
        if not row['low'] <= row['open'] <= row['high'] or not row['low'] <= row['close'] <= row['high']:
            raise ValueError('Invalid OHLC bounds')
    return dataset

def price_baselines(rows):
    """24 preceding sessions support 20 prior five-session ranges.

    Current range includes today's prices; its historical distribution does not.
    Missing data blocks its window rather than shortening it or becoming zero.
    """
    ordered = sorted(rows, key=lambda r: r['date'])
    if len({r['date'] for r in ordered}) != len(ordered):
        raise ValueError('Duplicate dates')
    ranges = []
    result = []
    for index, row in enumerate(ordered):
        window = ordered[max(0, index - 4):index + 1]
        available = len(window) == 5 and all(v.get(f) is not None for v in window for f in ('high', 'low', 'close'))
        denominator = median(v['close'] for v in window) if available else None
        current = (max(v['high'] for v in window) - min(v['low'] for v in window)) / denominator if denominator and denominator > 0 else None
        history = ranges[index - 20:index] if index >= 24 else []
        historical_complete = len(history) == 20 and all(v is not None for v in history)
        baseline = median(history) if historical_complete else None
        prior = ordered[index - 20:index] if index >= 24 else []
        volumes = [v.get('volume') for v in prior]
        volume_baseline = median(volumes) if len(volumes) == 20 and all(v is not None for v in volumes) else None
        result.append({'symbol': row['symbol'], 'date': row['date'],
                       'preceding_sessions': index, 'baseline_ready': historical_complete,
                       'current_5d_range_pct': current * 100 if current is not None else None,
                       'baseline_5d_range_pct': baseline * 100 if baseline is not None else None,
                       'compression_ratio': current / baseline if current is not None and baseline and baseline > 0 else None,
                       'volume_baseline_20_prior': volume_baseline,
                       'relative_volume': row['volume'] / volume_baseline if row.get('volume') is not None and volume_baseline and volume_baseline > 0 else None,
                       'price_regime_eligible': baseline is not None and baseline > 0})
        ranges.append(current)
    return result

def build(directory, analysis_end='2026-09-30', symbols=SYMBOLS):
    dataset = load_dataset(directory, symbols=symbols)
    result = []
    foreign_dates = {(r['symbol'], r['date']) for r in dataset['foreign_flow']}
    broker_dates = {(r['symbol'], r['date']) for r in dataset['broker_activity']}
    for symbol in symbols:
        rows = [r for r in dataset['daily'] if r['symbol'] == symbol]
        for row in price_baselines(rows):
            if '2026-04-01' <= row['date'] <= analysis_end:
                key = (symbol, row['date'])
                row.update(foreign_flow_available=key in foreign_dates,
                           broker_available=key in broker_dates,
                           broker_completeness_attested=False,
                           context_scope='PILOT_UNIVERSE_ONLY')
                result.append(row)
    return {'methodology': {'required_preceding_sessions': 24, 'baseline_window': 20,
                           'range_window': 5, 'baseline_excludes_evaluated_session': True,
                           'detector_thresholds_changed': False, 'detector_executed': False},
            'source_sha256': {n: hashlib.sha256((Path(directory) / (n + '.json')).read_bytes()).hexdigest()
                              for n in ('daily', 'foreign_flow', 'broker_activity', 'broker_registry')},
            'sessions': result}

"""Read-only access to audited all-broker preview; no external requests."""
from datetime import date
import re
import math
from pathlib import Path
from .repository import PayloadRepository, PayloadNotFoundError


class BrokerDataUnavailableError(Exception):
    """Invalid local research data must not be presented as valid broker activity."""


class BrokerRepository(PayloadRepository):
    def _read_json(self, path):
        try:
            return super()._read_json(path)
        except PayloadNotFoundError:
            raise PayloadNotFoundError('Broker research data is unavailable.') from None
        except (OSError, ValueError):
            raise BrokerDataUnavailableError() from None

    def _validate_activity(self, payload, symbol, day=None):
        try:
            if payload['symbol'] != symbol or (day is not None and payload['date'] != day.isoformat()):
                raise ValueError('Scope mismatch')
            if not isinstance(payload['brokers'], list):
                raise ValueError('Invalid rows')
            codes=set()
            for row in payload['brokers']:
                code=row['broker_code']
                if not isinstance(code,str) or not code or code in codes:
                    raise ValueError('Invalid or duplicate code')
                codes.add(code)
                for field in ('bval','sval','blot','slot','bfreq','sfreq','nval','nlot'):
                    value=row[field]
                    if value is None and row.get('source_quality')=='BROKER_FIELDS_INCOMPLETE':
                        continue
                    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                        raise ValueError('Invalid number')
                    if field not in ('nval','nlot') and value < 0:
                        raise ValueError('Negative gross activity')
                for buy,sell,netfield in [('bval','sval','nval'),('blot','slot','nlot')]:
                    expected=row[buy]-row[sell] if row[buy] is not None and row[sell] is not None else None
                    actual=row[netfield]
                    if expected is None:
                        if actual is not None: raise ValueError('Invented net')
                    elif actual is None or not math.isclose(expected,actual,rel_tol=1e-9,abs_tol=.01):
                        raise ValueError('Inconsistent net')
                net=row['nval']
                role='UNKNOWN' if net is None else 'NET_BUY' if net>0 else 'NET_SELL' if net<0 else 'NET_FLAT'
                if row['net_role'] != role: raise ValueError('Inconsistent role')
        except (KeyError,TypeError,ValueError):
            raise BrokerDataUnavailableError() from None
        return payload

    def symbol(self, symbol):
        symbol=symbol.upper().strip()
        if symbol not in self.manifest()['symbols']:
            raise PayloadNotFoundError('Broker research is unavailable for this symbol.')
        return symbol

    def index(self, symbol, signal_snapshot):
        symbol=self.symbol(symbol);manifest=self.manifest()
        dates=sorted(p.stem for p in (self.payload_dir/'sessions'/symbol).glob('*.json')
                     if re.fullmatch(r'\d{4}-\d{2}-\d{2}',p.stem))
        if not dates:
            raise PayloadNotFoundError('Broker session data is unavailable for this symbol.')
        for value in dates:date.fromisoformat(value)
        return {'symbol':symbol,'as_of':manifest['as_of'],'analysis_start':manifest['analysis_start'],
                'signal_snapshot':signal_snapshot,'default_date':signal_snapshot if signal_snapshot in dates else None,
                'dates':dates,'episodes':[e for e in manifest['episodes'] if e['symbol']==symbol],
                'source_completeness':'All returned rows retained; source completeness not independently verified.'}

    def session(self,symbol,day):
        symbol=self.symbol(symbol)
        return self._validate_activity(self._read_json(self.payload_dir/'sessions'/symbol/(day.isoformat()+'.json')),symbol,day)

    def episode(self,symbol,identifier):
        symbol=self.symbol(symbol)
        if not any(e['symbol']==symbol and e['investigation_id']==identifier for e in self.manifest()['episodes']):
            raise PayloadNotFoundError('Broker episode is unavailable for this symbol.')
        return self._validate_activity(self._read_json(self.payload_dir/'episodes'/(identifier+'.json')),symbol)

    def history(self,symbol,code,through):
        symbol=self.symbol(symbol)
        # Match a returned code; do not treat broker codes as paths or infer missing as zero.
        dates=self.index(symbol,through.isoformat())['dates']
        if through.isoformat() not in dates:
            raise PayloadNotFoundError('Broker history cutoff is unavailable.')
        dates=[d for d in dates if d<=through.isoformat()][-20:]
        series=[];seen=False
        for day in dates:
            payload=self.session(symbol,date.fromisoformat(day))
            row=next((r for r in payload['brokers'] if r['broker_code']==code),None)
            seen=seen or row is not None
            observation='RETURNED' if row else 'BROKER_DATA_MISSING' if not payload['brokers'] else 'NOT_RETURNED'
            fields=('bval','sval','blot','slot','bfreq','sfreq','nval','nlot','net_role')
            series.append({'date':day,'observation':observation,'session_quality':payload['quality']['status'],
                           **{f:row[f] if row else None for f in fields}})
        if not seen:
            earlier=[d for d in self.index(symbol,through.isoformat())['dates'] if d<dates[0]]
            known=any(any(r['broker_code']==code for r in self.session(symbol,date.fromisoformat(d))['brokers']) for d in earlier)
            if not known:
                raise PayloadNotFoundError('Broker code has not been returned by this cutoff.')
        # A known code absent from the last20 remains unknown, not zero.
        return {'symbol':symbol,'broker_code':code,'through':through.isoformat(),'window_sessions':len(dates),
                'returned_in_window':seen,'series':series}

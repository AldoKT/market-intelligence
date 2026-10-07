from datetime import date
from functools import lru_cache
from fastapi import APIRouter, Depends
from ..config import get_settings
from ..dependencies import get_repository
from ..repository import PayloadNotFoundError
from ..broker_repository import BrokerRepository

router=APIRouter(prefix='/api/brokers',tags=['brokers'])

@lru_cache(maxsize=1)
def get_broker_repository():
    return BrokerRepository(get_settings().broker_dir)

def pilot_repository():
    repository=get_repository()
    if not repository.manifest().get('methodology_version','').startswith('phase1-json-pilot'):
        raise PayloadNotFoundError('Broker research requires the JSON pilot profile.')
    return repository

@router.get('/{symbol}')
def index(symbol:str, repo=Depends(get_broker_repository),pilot=Depends(pilot_repository)):
    return repo.index(symbol,pilot.manifest()['as_of'])

@router.get('/{symbol}/sessions/{day}')
def session(symbol:str,day:date,repo=Depends(get_broker_repository),pilot=Depends(pilot_repository)):
    return repo.session(symbol,day)

@router.get('/{symbol}/episodes/{identifier}')
def episode(symbol:str,identifier:str,repo=Depends(get_broker_repository),pilot=Depends(pilot_repository)):
    return repo.episode(symbol,identifier)

@router.get('/{symbol}/history/{code}')
def history(symbol:str,code:str,through:date,repo=Depends(get_broker_repository),pilot=Depends(pilot_repository)):
    return repo.history(symbol,code,through)

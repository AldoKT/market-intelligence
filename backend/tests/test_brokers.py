import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path,monkeypatch):
    pilot=tmp_path/'pilot';broker=tmp_path/'brokers'
    pilot.mkdir();broker.mkdir()
    (pilot/'manifest.json').write_text(json.dumps({'methodology_version':'phase1-json-pilot-2.0','as_of':'2026-09-30'}))
    manifest={'symbols':['ANTM','BBCA'],'as_of':'2026-10-02','analysis_start':'2026-09-30','episodes':[
        {'symbol':'ANTM','investigation_id':'ANTM-20260930-01','start':'2026-09-30','last_observed_date':'2026-10-02','last_state':'CLOSED','observed_sessions':3,'end_status':'OBSERVED_CLOSED'}]}
    (broker/'manifest.json').write_text(json.dumps(manifest))
    path=broker/'sessions/ANTM';path.mkdir(parents=True)
    rows=[{'broker_code':str(i),'bval':100,'sval':100,'nval':0,'blot':1,'slot':1,'nlot':0,'bfreq':1,'sfreq':1,'net_role':'NET_FLAT'} for i in range(7)]
    for day in ('2026-09-30','2026-10-01','2026-10-02'):
        body={'symbol':'ANTM','date':day,'brokers':rows if day!='2026-10-01' else [],
              'quality':{'status':'RECONCILED_RESEARCH_CANDIDATE' if day!='2026-10-01' else 'BROKER_DATA_MISSING'}}
        (path/(day+'.json')).write_text(json.dumps(body))
    (broker/'episodes').mkdir()
    (broker/'episodes/ANTM-20260930-01.json').write_text(json.dumps({'symbol':'ANTM','brokers':rows,'start':'2026-09-30','last_observed_date':'2026-10-02'}))
    monkeypatch.setenv('SIGNAL_PAYLOAD_DIR',str(pilot));monkeypatch.setenv('SIGNAL_BROKER_DIR',str(broker))
    from app.dependencies import get_repository
    from app.routers.brokers import get_broker_repository
    from app.main import create_app
    get_repository.cache_clear();get_broker_repository.cache_clear()
    with TestClient(create_app()) as app:
        yield app,pilot
    get_repository.cache_clear();get_broker_repository.cache_clear()


def test_default_is_signal_snapshot_not_later_research_date(client):
    app,_=client;value=app.get('/api/brokers/ANTM').json()
    assert value['default_date']=='2026-09-30' and value['as_of']=='2026-10-02'
    assert len(value['dates'])==3


def test_full_table_keeps_more_than_five_and_zero_net(client):
    app,_=client;response=app.get('/api/brokers/ANTM/sessions/2026-09-30')
    assert response.status_code==200
    assert len(response.json()['brokers'])==7
    assert all(r['net_role']=='NET_FLAT' for r in response.json()['brokers'])


def test_history_no_future_rows_or_zero_filled_gaps(client):
    app,_=client
    rows=app.get('/api/brokers/ANTM/history/0?through=2026-10-01').json()['series']
    assert [r['date'] for r in rows]==['2026-09-30','2026-10-01']
    assert rows[0]['nval']==0 and rows[1]['nval'] is None
    assert rows[1]['observation']=='BROKER_DATA_MISSING'


def test_unknown_dates_symbols_codes_and_wrong_episode_symbol(client):
    app,_=client
    for url in ('/api/brokers/OTHER','/api/brokers/ANTM/sessions/2027-01-01',
                '/api/brokers/BBCA/episodes/ANTM-20260930-01','/api/brokers/ANTM/history/ZZ?through=2026-09-30'):
        assert app.get(url).status_code==404
    assert app.get('/api/brokers/ANTM/sessions/not-a-date').status_code==422


def test_legacy_profile_does_not_expose_later_broker_research(client):
    app,pilot=client
    (pilot/'manifest.json').write_text(json.dumps({'methodology_version':'1.0-candidate','as_of':'2026-09-30'}))
    from app.dependencies import get_repository
    get_repository.cache_clear()
    assert app.get('/api/brokers/ANTM').status_code==404


def test_episode_and_identifier_cannot_escape_root(client):
    app,_=client
    assert app.get('/api/brokers/ANTM/episodes/ANTM-20260930-01').json()['last_observed_date']=='2026-10-02'
    from app.routers.brokers import get_broker_repository
    from app.repository import PayloadNotFoundError
    with pytest.raises(PayloadNotFoundError):get_broker_repository().episode('ANTM','../../manifest')


def test_corrupt_json_returns_controlled_error_without_disk_path(client):
    app,_=client
    from app.routers.brokers import get_broker_repository
    path=get_broker_repository().payload_dir/'sessions/ANTM/2026-09-30.json'
    path.write_text('{invalid json')
    response=app.get('/api/brokers/ANTM/sessions/2026-09-30')
    assert response.status_code==503
    assert str(path) not in response.text


@pytest.mark.parametrize('change', ['wrong_symbol','wrong_date','duplicate','bad_net','negative','nonfinite'])
def test_inconsistent_session_is_not_served_as_valid_data(client,change):
    app,_=client
    from app.routers.brokers import get_broker_repository
    path=get_broker_repository().payload_dir/'sessions/ANTM/2026-09-30.json'
    value=json.loads(path.read_text())
    if change=='wrong_symbol':value['symbol']='BBCA'
    elif change=='wrong_date':value['date']='2026-10-02'
    elif change=='duplicate':value['brokers'].append(value['brokers'][0])
    elif change=='bad_net':value['brokers'][0]['nval']=999
    elif change=='negative':value['brokers'][0]['bfreq']=-1
    elif change=='nonfinite':value['brokers'][0]['bval']=float('nan')
    path.write_text(json.dumps(value))
    assert app.get('/api/brokers/ANTM/sessions/2026-09-30').status_code==503
    assert app.get('/api/brokers/ANTM/history/0?through=2026-09-30').status_code==503


def test_missing_snapshot_requires_explicit_date_instead_of_future_default(client):
    app,pilot=client
    (pilot/'manifest.json').write_text(json.dumps({'methodology_version':'phase1-json-pilot-2.0','as_of':'2026-09-29'}))
    from app.dependencies import get_repository
    get_repository.cache_clear()
    assert app.get('/api/brokers/ANTM').json()['default_date'] is None

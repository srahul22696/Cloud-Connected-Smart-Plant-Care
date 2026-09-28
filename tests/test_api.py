from datetime import datetime, timezone, timedelta
import json

def sample(device_id='PLANT-001', **changes):
    item={'device_id':device_id,'event_id':'reading-000001','soil_moisture':55,'temperature':24.2,'humidity':60,'light_level':70,'timestamp':datetime.now(timezone.utc).isoformat()}
    item.update(changes); return item

def test_registration_login_and_unauthorized(client):
    assert client.get('/api/devices').status_code==401
    assert client.post('/api/auth/login',json={'email':'none@example.com','password':'invalid'}).status_code==401
    assert client.post('/api/auth/register',json={'email':'GROWER@example.com','password':'other-long-password-123'}).status_code==201
    assert client.post('/api/auth/register',json={'email':'grower@example.com','password':'other-long-password-123'}).status_code==409

def test_reject_short_password_and_malformed_email(client):
    assert client.post('/api/auth/register',json={'email':'x','password':'short'}).status_code==422
    assert client.post('/api/auth/register',json={'email':'bad@@example.com','password':'long-password-123'}).status_code==422

def test_device_api_key_is_one_time_and_user_scoped(client,account,device):
    assert client.post('/api/sensors/data',headers={'X-Device-Key':'wrong'},json=sample()).status_code==401
    other=client.post('/api/auth/register',json={'email':'other@example.com','password':'long-password-456'}).json()['access_token']
    assert client.get('/api/devices/PLANT-001',headers={'Authorization':f'Bearer {other}'}).status_code==404

def test_valid_reading_and_duplicate_are_idempotent(client,device):
    first=client.post('/api/sensors/data',headers=device['headers'],json=sample())
    assert first.status_code==202 and first.json()['accepted']
    duplicate=client.post('/api/sensors/data',headers=device['headers'],json=sample())
    assert duplicate.status_code==202 and duplicate.json()['duplicate']

def test_impossible_sensor_values_rejected(client,device):
    for key,value in [('soil_moisture',101),('temperature',90),('humidity',-1),('light_level',float('nan'))]:
        assert client.post('/api/sensors/data',headers=device['headers'],content=json.dumps(sample(event_id=f'event-{key}',**{key:value}),allow_nan=True)).status_code==422
    future=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    assert client.post('/api/sensors/data',headers=device['headers'],json=sample(event_id='event-future',timestamp=future)).status_code==422
    no_tz=datetime.now().replace(tzinfo=None).isoformat()
    assert client.post('/api/sensors/data',headers=device['headers'],json=sample(event_id='event-no-tz',timestamp=no_tz)).status_code==422

def test_low_moisture_queues_bounded_automatic_water(client,device,account):
    result=client.post('/api/sensors/data',headers=device['headers'],json=sample(soil_moisture=10))
    assert result.status_code==202 and result.json()['watering']=='queued'
    actions=client.get('/api/devices/PLANT-001/actions',headers=device['headers']).json()['actions']
    assert len(actions)==1 and actions[0]['duration_seconds']<=10
    assert client.get('/api/devices/PLANT-001/actions',headers=device['headers']).json()['actions']==[]

def test_cooldown_prevents_repeated_watering(client,device):
    assert client.post('/api/sensors/data',headers=device['headers'],json=sample(soil_moisture=10)).json()['watering']=='queued'
    assert client.post('/api/sensors/data',headers=device['headers'],json=sample(event_id='reading-000002',soil_moisture=8)).json()['watering']=='not_required'

def test_threshold_range_and_auto_toggle(client,account,device):
    assert client.put('/api/devices/PLANT-001/threshold',headers=account,json={'threshold':101}).status_code==422
    assert client.put('/api/devices/PLANT-001/threshold',headers=account,json={'threshold':34}).status_code==200
    assert client.put('/api/devices/PLANT-001/auto-water',headers=account,json={'enabled':False}).json()['auto_water'] is False

def test_manual_water_requires_reading_and_obeys_cooldown(client,account,device):
    assert client.post('/api/devices/PLANT-001/water',headers=account,json={'duration_seconds':3}).status_code==409
    client.post('/api/sensors/data',headers=device['headers'],json=sample())
    assert client.post('/api/devices/PLANT-001/water',headers=account,json={'duration_seconds':99}).status_code==422
    assert client.post('/api/devices/PLANT-001/water',headers=account,json={'duration_seconds':3}).status_code==202
    assert client.post('/api/devices/PLANT-001/water',headers=account,json={'duration_seconds':3}).status_code==429

def test_low_tank_blocks_automatic_watering(client,device):
    result=client.post('/api/sensors/data',headers=device['headers'],json=sample(soil_moisture=10,event_id='tank-reading',water_tank_level=2))
    assert result.status_code==202 and result.json()['watering']=='not_required'
    assert client.get('/api/devices/PLANT-001/actions',headers=device['headers']).json()['actions']==[]

def test_alerts_acknowledge_and_history(client,account,device):
    client.post('/api/sensors/data',headers=device['headers'],json=sample(soil_moisture=10))
    alerts=client.get('/api/alerts',headers=account).json()
    assert any(a['alert_type']=='low_moisture' for a in alerts)
    aid=alerts[0]['id']; assert client.put(f'/api/alerts/{aid}/acknowledge',headers=account).json()['acknowledged']
    assert client.get('/api/devices/PLANT-001/history',headers=account).status_code==200

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import backend.database as database
from backend.app import app
from backend.database import Base, get_db
from backend.config import settings

@pytest.fixture
def client(monkeypatch):
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    test_sessions=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    def override_db():
        db=test_sessions()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db]=override_db
    monkeypatch.setattr(settings,"app_secret","test-secret-with-enough-entropy-123456")
    monkeypatch.setattr(settings,"app_env","test")
    monkeypatch.setattr(settings,"watering_cooldown_seconds",300)
    monkeypatch.setattr(settings,"default_pump_seconds",3)
    monkeypatch.setattr(settings,"max_pump_seconds",10)
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear(); Base.metadata.drop_all(engine); engine.dispose()

@pytest.fixture
def account(client):
    res=client.post('/api/auth/register',json={'email':'grower@example.com','password':'long-password-123'})
    assert res.status_code==201
    return {'Authorization':f"Bearer {res.json()['access_token']}"}

@pytest.fixture
def device(client,account):
    res=client.post('/api/devices',headers=account,json={'id':'PLANT-001','plant_name':'Tomato','plant_type':'tomato'})
    assert res.status_code==201
    return {**res.json(),'headers':{'X-Device-Key':res.json()['device_key']}}

import importlib
import sys
from pathlib import Path

import mongomock
import pytest
from flask_jwt_extended import create_access_token, decode_token

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setenv('JWT_SECRET_KEY', 'local-test-signing-key-with-at-least-32-characters')
    monkeypatch.setenv('MONGODB_URI', 'mongodb://localhost')
    monkeypatch.setenv('DB_NAME', 'alertme_test')
    monkeypatch.setenv('PERSONAL_DB_NAME', 'alertme_personal_test')
    monkeypatch.delenv('ADMIN_EMAIL', raising=False)
    monkeypatch.delenv('ADMIN_PASSWORD', raising=False)
    monkeypatch.delenv('ADMIN_PASSWORD_HASH', raising=False)
    database = mongomock.MongoClient()
    monkeypatch.setattr('pymongo.MongoClient', lambda *a, **kw: database)
    module = importlib.import_module('Alertme.src.backend.app')
    module = importlib.reload(module)
    module.app.config['TESTING'] = True
    return module


def auth(backend, identity):
    with backend.app.app_context():
        return {'Authorization': 'Bearer ' + create_access_token(identity=identity)}


@pytest.mark.parametrize('endpoint,model', [
    ('/api/deadlines', 'deadline_model'),
    ('/api/personal-deadlines', 'personal_deadline_model'),
])
def test_other_user_cannot_change_deadline(backend, endpoint, model):
    collection = getattr(backend, model).collection
    identifier = collection.insert_one({'user_id': 'owner', 'title': 'Private'}).inserted_id
    client = backend.app.test_client()
    headers = auth(backend, 'stranger')
    if endpoint == '/api/deadlines':
        assert client.get(f'{endpoint}/{identifier}', headers=headers).status_code == 404
    assert client.put(f'{endpoint}/{identifier}', json={'title': 'Hijacked'}, headers=headers).status_code == 404
    assert client.delete(f'{endpoint}/{identifier}', headers=headers).status_code == 404
    assert collection.find_one({'_id': identifier})['title'] == 'Private'


@pytest.mark.parametrize('endpoint,model', [
    ('/api/deadlines', 'deadline_model'),
    ('/api/personal-deadlines', 'personal_deadline_model'),
])
def test_owner_can_update_and_delete_but_cannot_transfer_ownership(backend, endpoint, model):
    collection = getattr(backend, model).collection
    identifier = collection.insert_one({'user_id': 'owner', 'title': 'Original'}).inserted_id
    client = backend.app.test_client()
    headers = auth(backend, 'owner')
    assert client.put(f'{endpoint}/{identifier}', json={'title': 'Updated', 'user_id': 'stranger'}, headers=headers).status_code in (200, 204)
    saved = collection.find_one({'_id': identifier})
    assert saved['title'] == 'Updated'
    assert saved['user_id'] == 'owner'
    assert client.delete(f'{endpoint}/{identifier}', headers=headers).status_code in (200, 204)
    assert collection.find_one({'_id': identifier}) is None


def test_access_tokens_expire(backend):
    with backend.app.app_context():
        token = decode_token(create_access_token(identity='user'))
    assert 0 < token['exp'] - token['iat'] <= 3600


def test_unconfigured_admin_cannot_log_in(backend):
    response = backend.app.test_client().post('/auth/api/admin/login', json={})
    assert response.status_code == 401


def test_models_use_configured_database(backend):
    assert backend.deadline_model.collection.database.name == 'alertme_personal_test'
    assert backend.personal_deadline_model.collection.database.name == 'alertme_test'


@pytest.mark.parametrize('endpoint', ['/api/deadlines', '/api/personal-deadlines'])
def test_malformed_deadline_id_is_client_error(backend, endpoint):
    response = backend.app.test_client().delete(f'{endpoint}/invalid', headers=auth(backend, 'owner'))
    assert response.status_code == 400


def test_login_rejects_query_operators(backend):
    response = backend.app.test_client().post('/login', json={
        'identifier': {'$ne': None}, 'password': 'irrelevant',
    })
    assert response.status_code == 400


def test_missing_signing_key_fails_closed(backend, monkeypatch):
    monkeypatch.delenv('JWT_SECRET_KEY')
    monkeypatch.setattr('dotenv.load_dotenv', lambda: None)
    with pytest.raises(RuntimeError, match='JWT_SECRET_KEY'):
        importlib.reload(backend)


def test_configured_admin_hash_can_log_in(backend, monkeypatch):
    from werkzeug.security import generate_password_hash
    monkeypatch.setattr(backend, 'ADMIN_EMAIL', 'admin@example.test')
    monkeypatch.setattr(backend, 'ADMIN_PASSWORD_HASH', generate_password_hash('local-test-admin'))
    client = backend.app.test_client()
    assert client.post('/auth/api/admin/login', json={'email': 'admin@example.test', 'password': 'wrong'}).status_code == 401
    response = client.post('/auth/api/admin/login', json={'email': 'admin@example.test', 'password': 'local-test-admin'})
    assert response.status_code == 200
    assert client.get('/auth/api/admin/verify', headers={'Authorization': 'Bearer ' + response.json['token']}).status_code == 200

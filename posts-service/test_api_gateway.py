import pytest
import jwt
from unittest.mock import patch, MagicMock
from app import app

SECRET_KEY = 'your_secret_key'

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def generate_token(username):
    return jwt.encode({'username': username}, SECRET_KEY, algorithm='HS256')

def test_register_success(client):
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {'message': 'User registered successfully!'}
        mock_post.return_value.status_code = 201

        response = client.post('/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepass'
        })

        assert response.status_code == 201
        assert response.json['message'] == 'User registered successfully!'

def test_login_success(client):
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {'token': 'faketoken'}
        mock_post.return_value.status_code = 200

        response = client.post('/login', json={
            'username': 'testuser',
            'password': 'securepass'
        })

        assert response.status_code == 200
        assert 'token' in response.json

def test_create_post(client):
    token = generate_token('testuser')

    with patch('app.get_grpc_stub') as mock_stub:
        mock_instance = MagicMock()
        mock_instance.CreatePost.return_value = MagicMock(post={
            'id': '1',
            'title': 'Test Post',
            'description': 'A test post.',
            'creator_id': 'testuser',
            'created_at': '2023-01-01T00:00:00',
            'updated_at': '2023-01-01T00:00:00',
            'is_private': False,
            'tags': ['test']
        })
        mock_stub.return_value = mock_instance

        response = client.post('/posts',
                               json={
                                   'title': 'Test Post',
                                   'description': 'A test post.',
                                   'is_private': False,
                                   'tags': ['test']
                               },
                               headers={'Authorization': f'Bearer {token}'}
                               )

        assert response.status_code == 200
        assert 'post' in response.json
        assert response.json['post']['title'] == 'Test Post'

def test_get_post_unauthorized(client):
    response = client.get('/posts/1')
    assert response.status_code == 401

def test_get_post_success(client):
    token = generate_token('testuser')

    with patch('app.get_grpc_stub') as mock_stub:
        mock_instance = MagicMock()
        mock_instance.GetPost.return_value = MagicMock(post={
            'id': '1',
            'title': 'Test Post',
            'description': 'A test post.',
            'creator_id': 'testuser',
            'created_at': '2023-01-01T00:00:00',
            'updated_at': '2023-01-01T00:00:00',
            'is_private': False,
            'tags': ['test']
        })
        mock_stub.return_value = mock_instance

        response = client.get('/posts/1', headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == 200
        assert 'post' in response.json


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

@pytest.fixture
def mock_dependencies():
    with patch('app.get_grpc_stub') as mock_grpc, patch('app.send_event') as mock_kafka:
        yield mock_grpc, mock_kafka

def test_register_success(client, mock_dependencies):
    mock_grpc, mock_send_event = mock_dependencies

    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {'id': '1', 'message': 'User registered successfully!'}
        mock_post.return_value.status_code = 201

        response = client.post('/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepass'
        })

        assert response.status_code == 201
        assert response.json['message'] == 'User registered successfully!'
        mock_send_event.assert_called_once()
        called_args = mock_send_event.call_args[0]
        assert called_args[0] == 'user_registered'
        assert 'username' in called_args[1]

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

def test_create_post(client, mock_dependencies):
    mock_grpc, mock_send_event = mock_dependencies
    token = generate_token('testuser')

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
    mock_grpc.return_value = mock_instance

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

def test_get_post_unauthorized(client):
    response = client.get('/posts/1')
    assert response.status_code == 401

def test_get_post_success(client, mock_dependencies):
    mock_grpc, _ = mock_dependencies
    token = generate_token('testuser')

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
    mock_grpc.return_value = mock_instance

    response = client.get('/posts/1', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200

def test_view_post_success(client, mock_dependencies):
    mock_grpc, mock_send_event = mock_dependencies
    token = generate_token('testuser')

    mock_instance = MagicMock()
    mock_instance.ViewPost.return_value = MagicMock()
    mock_grpc.return_value = mock_instance

    response = client.post('/posts/1/view', headers={'Authorization': f'Bearer {token}'})
    
    assert response.status_code == 204
    mock_send_event.assert_called_once()
    called_args = mock_send_event.call_args[0]
    assert called_args[0] == 'post_viewed'
    assert 'user_id' in called_args[1]
    assert 'post_id' in called_args[1]
    assert 'viewed_at' in called_args[1]

def test_like_post_success(client, mock_dependencies):
    mock_grpc, mock_send_event = mock_dependencies
    token = generate_token('testuser')

    mock_instance = MagicMock()
    mock_instance.LikePost.return_value = MagicMock()
    mock_grpc.return_value = mock_instance

    response = client.post('/posts/1/like', headers={'Authorization': f'Bearer {token}'})
    
    assert response.status_code == 204
    mock_send_event.assert_called_once()
    called_args = mock_send_event.call_args[0]
    assert called_args[0] == 'post_liked'
    assert 'user_id' in called_args[1]
    assert 'post_id' in called_args[1]
    assert 'liked_at' in called_args[1]

def test_comment_post_success(client, mock_dependencies):
    mock_grpc, mock_send_event = mock_dependencies
    token = generate_token('testuser')

    mock_instance = MagicMock()
    mock_instance.CommentPost.return_value = MagicMock()
    mock_grpc.return_value = mock_instance

    response = client.post('/posts/1/comment',
                           json={'content': 'Nice post!'},
                           headers={'Authorization': f'Bearer {token}'})
    
    assert response.status_code == 204
    mock_send_event.assert_called_once()
    called_args = mock_send_event.call_args[0]
    assert called_args[0] == 'post_commented'
    assert 'user_id' in called_args[1]
    assert 'post_id' in called_args[1]
    assert 'comment' in called_args[1]
    assert 'commented_at' in called_args[1]

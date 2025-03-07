import pytest
import json
from ..app import app, db, User
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
    client = app.test_client()

    with app.app_context():
        db.create_all()
        yield client
        db.drop_all()

def test_register_user(client):
    response = client.post("/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword"
    })
    assert response.status_code == 201
    assert response.json["message"] == "User registered successfully!"

def test_login_user(client):
    with app.app_context():
        user = User(username="testuser", email="test@example.com", password_hash=generate_password_hash("testpassword"))
        db.session.add(user)
        db.session.commit()

    response = client.post("/login", json={
        "username": "testuser",
        "password": "testpassword"
    })
    assert response.status_code == 200
    assert "token" in response.json

def test_get_profile(client):
    with app.app_context():
        user = User(username="testuser", email="test@example.com", password_hash=generate_password_hash("testpassword"))
        db.session.add(user)
        db.session.commit()
        token = json.loads(client.post("/login", json={"username": "testuser", "password": "testpassword"}).data)["token"]

    response = client.get("/profile", headers={"Authorization": token})
    assert response.status_code == 200
    assert response.json["username"] == "testuser"
    assert response.json["email"] == "test@example.com"

def test_update_profile(client):
    with app.app_context():
        user = User(username="testuser", email="test@example.com", password_hash=generate_password_hash("testpassword"))
        db.session.add(user)
        db.session.commit()
        token = json.loads(client.post("/login", json={"username": "testuser", "password": "testpassword"}).data)["token"]

    response = client.put("/profile", json={"first_name": "NewName"}, headers={"Authorization": token})
    assert response.status_code == 200
    assert response.json["message"] == "Profile updated successfully!"

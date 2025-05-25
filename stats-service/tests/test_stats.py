import pytest
from unittest.mock import patch, MagicMock
from main import app  # adjust if your Flask app is defined elsewhere


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# Mocked gRPC response for post stats
@patch("main.get_stats_stub")
def test_get_post_stats(mock_stub, client):
    mock_response = MagicMock()
    mock_response.views = 100
    mock_response.likes = 50
    mock_response.comments = 25
    mock_stub.return_value.GetPostStats.return_value = mock_response

    res = client.get("/stats/12345")
    assert res.status_code == 200
    assert res.json == {"views": 100, "likes": 50, "comments": 25}


# Mocked gRPC response for views over time
@patch("main.get_stats_stub")
def test_get_post_views_over_time(mock_stub, client):
    mock_response = MagicMock()
    mock_response.entries = [
        MagicMock(date="2025-05-24", count=10),
        MagicMock(date="2025-05-25", count=12)
    ]
    mock_stub.return_value.GetPostViewsOverTime.return_value = mock_response

    res = client.get("/stats/12345/views")
    assert res.status_code == 200
    assert "entries" in res.json
    assert res.json["entries"][0]["date"] == "2025-05-24"


# Top posts by likes
@patch("main.get_stats_stub")
def test_get_top_posts(mock_stub, client):
    mock_response = MagicMock()
    mock_response.posts = [
        MagicMock(post_id="post1", count=100),
        MagicMock(post_id="post2", count=80)
    ]
    mock_stub.return_value.GetTopPosts.return_value = mock_response

    res = client.get("/stats/top/posts?metric=likes")
    assert res.status_code == 200
    assert res.json["posts"][0]["post_id"] == "post1"


# Invalid metric for users
def test_invalid_top_users_metric(client):
    res = client.get("/stats/top/users?metric=invalid")
    assert res.status_code == 400
    assert "Invalid metric" in res.json["message"]

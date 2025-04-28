from flask import Flask, request, jsonify
import requests
import grpc
from google.protobuf.json_format import MessageToDict
import jwt
from marshmallow import Schema, fields, ValidationError, validate
from datetime import datetime
import post_pb2
import post_pb2_grpc
from kafka import KafkaProducer
import json
import time

app = Flask(__name__)
USER_SERVICE_URL = "http://users-service:5001"
POSTS_SERVICE_HOST = "posts-service:50051"

KAFKA_BOOTSTRAP_SERVERS = 'kafka:9092'
time.sleep(5)
try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
except Exception as e:
    print(e)
    
def send_event(topic, event):
    producer.send(topic, event)
    producer.flush()


class CreatePostSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1))
    description = fields.String(required=True, validate=validate.Length(min=1))
    is_private = fields.Boolean(load_default=False)
    tags = fields.List(fields.String(), load_default=[])

class UpdatePostSchema(Schema):
    title = fields.String()
    description = fields.String()
    is_private = fields.Boolean()
    tags = fields.List(fields.String())

class ViewPostSchema(Schema):
    viewed_at = fields.String(required=False)

class LikePostSchema(Schema):
    liked_at = fields.String(required=False)

class CommentPostSchema(Schema):
    content = fields.String(required=True, validate=validate.Length(min=1))
    commented_at = fields.String(required=False)

def decode_token(auth_header):
    if not auth_header:
        return None
    try:
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = auth_header
        payload = jwt.decode(token, "your_secret_key", algorithms=["HS256"])
        return payload.get("username")
    except Exception:
        return None

def get_grpc_stub():
    channel = grpc.insecure_channel(POSTS_SERVICE_HOST)
    return post_pb2_grpc.PostServiceStub(channel)

@app.route('/register', methods=['POST'])
def register():
    response = requests.post(f"{USER_SERVICE_URL}/register", json=request.json)

    if response.status_code == 201:
        user_data = request.json
        send_event('user_registered', {
            "username": user_data.get("username", ""),
            "registered_at": datetime.utcnow().isoformat()
        })
    
    return jsonify(response.json()), response.status_code


@app.route('/login', methods=['POST'])
def login():
    response = requests.post(f"{USER_SERVICE_URL}/login", json=request.json)
    return jsonify(response.json()), response.status_code

@app.route('/profile', methods=['GET', 'PUT'])
def profile():
    headers = {"Authorization": request.headers.get("Authorization")}
    if request.method == 'GET':
        response = requests.get(f"{USER_SERVICE_URL}/profile", headers=headers)
    else:
        response = requests.put(f"{USER_SERVICE_URL}/profile", json=request.json, headers=headers)
    return jsonify(response.json()), response.status_code

@app.route('/posts', methods=['POST'])
def create_post():
    user_id = decode_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        data = CreatePostSchema().load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 401

    stub = get_grpc_stub()
    grpc_request = post_pb2.CreatePostRequest(
        title=data["title"],
        description=data["description"],
        creator_id=user_id,
        is_private=data["is_private"],
        tags=data["tags"]
    )
    grpc_response = stub.CreatePost(grpc_request)
    return jsonify(MessageToDict(grpc_response))

@app.route('/posts/<post_id>', methods=['GET'])
def get_post(post_id):
    user_id = decode_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    stub = get_grpc_stub()
    grpc_request = post_pb2.GetPostRequest(id=post_id, requester_id=user_id)
    try:
        grpc_response = stub.GetPost(grpc_request)
        return jsonify(MessageToDict(grpc_response))
    except grpc.RpcError as e:
        return jsonify({"message": e.details()}), 401

@app.route('/posts/<post_id>', methods=['PUT'])
def update_post(post_id):
    user_id = decode_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        data = UpdatePostSchema().load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 401

    stub = get_grpc_stub()
    grpc_request = post_pb2.UpdatePostRequest(
        id=post_id,
        title=data.get("title", ""),
        description=data.get("description", ""),
        is_private=data.get("is_private", False),
        tags=data.get("tags", []),
        requester_id=user_id
    )
    try:
        grpc_response = stub.UpdatePost(grpc_request)
        return jsonify(MessageToDict(grpc_response))
    except grpc.RpcError as e:
        return jsonify({"message": e.details()}), 401

@app.route('/posts/<post_id>', methods=['DELETE'])
def delete_post(post_id):
    user_id = decode_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    stub = get_grpc_stub()
    grpc_request = post_pb2.DeletePostRequest(id=post_id, requester_id=user_id)
    try:
        stub.DeletePost(grpc_request)
        return '', 204
    except grpc.RpcError as e:
        return jsonify({"message": e.details()}), 401

@app.route('/posts', methods=['GET'])
def list_posts():
    user_id = decode_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))

    stub = get_grpc_stub()
    grpc_request = post_pb2.ListPostsRequest(requester_id=user_id, page=page, page_size=page_size)
    grpc_response = stub.ListPosts(grpc_request)
    return jsonify(MessageToDict(grpc_response))

@app.route('/posts/<post_id>/view', methods=['POST'])
def view_post(post_id):
    user_id = decode_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    stub = get_grpc_stub()
    now = datetime.utcnow().isoformat()
    grpc_request = post_pb2.ViewPostRequest(
        post_id=post_id,
        viewer_id=user_id,
        viewed_at=now
    )
    try:
        stub.ViewPost(grpc_request)
        send_event('post_viewed', {
            "user_id": user_id,
            "post_id": post_id,
            "viewed_at": now
        })
        return '', 204
    except grpc.RpcError as e:
        return jsonify({"message": e.details()}), 400

@app.route('/posts/<post_id>/like', methods=['POST'])
def like_post(post_id):
    user_id = decode_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    stub = get_grpc_stub()
    now = datetime.utcnow().isoformat()
    grpc_request = post_pb2.LikePostRequest(
        post_id=post_id,
        liker_id=user_id,
        liked_at=now
    )
    try:
        stub.LikePost(grpc_request)
        send_event('post_liked', {
            "user_id": user_id,
            "post_id": post_id,
            "liked_at": now
        })
        return '', 204
    except grpc.RpcError as e:
        return jsonify({"message": e.details()}), 400

    user_id = decode_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    stub = get_grpc_stub()
    grpc_request = post_pb2.LikePostRequest(
        post_id=post_id,
        liker_id=user_id,
        liked_at=datetime.utcnow().isoformat()  # авто-время
    )
    try:
        stub.LikePost(grpc_request)
        return '', 204
    except grpc.RpcError as e:
        return jsonify({"message": e.details()}), 400

@app.route('/posts/<post_id>/comment', methods=['POST'])
def comment_post(post_id):
    user_id = decode_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        data = CommentPostSchema().load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    stub = get_grpc_stub()
    now = datetime.utcnow().isoformat()
    grpc_request = post_pb2.CommentPostRequest(
        post_id=post_id,
        commenter_id=user_id,
        content=data["content"],
        commented_at=now
    )
    try:
        stub.CommentPost(grpc_request)
        send_event('post_commented', {
            "user_id": user_id,
            "post_id": post_id,
            "comment": data["content"],
            "commented_at": now
        })
        return '', 204
    except grpc.RpcError as e:
        return jsonify({"message": e.details()}), 400

@app.route('/posts/<post_id>/comments', methods=['GET'])
def list_post_comments(post_id):
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))

    stub = get_grpc_stub()
    grpc_request = post_pb2.ListPostCommentsRequest(
        post_id=post_id,
        page=page,
        page_size=page_size
    )
    try:
        grpc_response = stub.ListPostComments(grpc_request)
        return jsonify(MessageToDict(grpc_response))
    except grpc.RpcError as e:
        return jsonify({"message": e.details()}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

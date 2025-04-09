from flask import Flask, request, jsonify
import requests
import grpc
from google.protobuf.json_format import MessageToDict
import post_pb2
import post_pb2_grpc
import jwt

app = Flask(__name__)
USER_SERVICE_URL = "http://users-service:5001"
POSTS_SERVICE_HOST = "posts-service:50051"

class CreatePostSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1))
    description = fields.String(required=True, validate=validate.Length(min=1))
    is_private = fields.Boolean(missing=False)
    tags = fields.List(fields.String(), missing=[])

class UpdatePostSchema(Schema):
    title = fields.String()
    description = fields.String()
    is_private = fields.Boolean()
    tags = fields.List(fields.String())

def get_grpc_stub():
    channel = grpc.insecure_channel(POSTS_SERVICE_HOST)
    return post_pb2_grpc.PostServiceStub(channel)

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
    except Exception as e:
        return None

@app.route('/register', methods=['POST'])
def register():
    response = requests.post(f"{USER_SERVICE_URL}/register", json=request.json)
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

    data = request.json
    stub = get_grpc_stub()
    grpc_request = post_pb2.CreatePostRequest(
        title=data["title"],
        description=data["description"],
        creator_id=user_id,
        is_private=data.get("is_private", False),
        tags=data.get("tags", [])
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
        return jsonify({"message": e.details()}), e.code().value[0]

@app.route('/posts/<post_id>', methods=['PUT'])
def update_post(post_id):
    user_id = decode_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json
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
        return jsonify({"message": e.details()}), e.code().value[0]

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
        return jsonify({"message": e.details()}), e.code().value[0]

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

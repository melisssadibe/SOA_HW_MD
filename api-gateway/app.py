from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
USER_SERVICE_URL = "http://user_service:5001"

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

from flask import Flask, request, jsonify
import requests
import os
from PIL import Image
import tempfile

app = Flask(__name__)

API_KEY = '-g2HJjxr7cXknliWvXArQrv3yj8sEO8T'
API_SECRET = '6Qmd7WAGpCb5jMuE1Fadcpp-rHCj6tkz'
FACESET_OUTER_ID = 'employee_faces'
MIN_SIZE = 64
MAX_SIZE = 1920

def resize_image_if_needed(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
        if width < MIN_SIZE or height < MIN_SIZE or width > MAX_SIZE or height > MAX_SIZE:
            scale_factor = 1
            if width < MIN_SIZE:
                scale_factor = max(scale_factor, MIN_SIZE / width)
            if height < MIN_SIZE:
                scale_factor = max(scale_factor, MIN_SIZE / height)
            if width > MAX_SIZE:
                scale_factor = min(scale_factor, MAX_SIZE / width)
            if height > MAX_SIZE:
                scale_factor = min(scale_factor, MAX_SIZE / height)

            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)

            resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)
            resized_img.save(image_path)

def detect_face(image_path):
    url = 'https://api-us.faceplusplus.com/facepp/v3/detect'
    with open(image_path, 'rb') as f:
        files = {'image_file': f}
        data = {
            'api_key': API_KEY,
            'api_secret': API_SECRET,
        }
        response = requests.post(url, data=data, files=files)
        result = response.json()
        if 'faces' in result and len(result['faces']) > 0:
            return result['faces'][0]['face_token']
        else:
            return None

def create_faceset():
    url = 'https://api-us.faceplusplus.com/facepp/v3/faceset/create'
    data = {
        'api_key': API_KEY,
        'api_secret': API_SECRET,
        'display_name': 'Employees FaceSet',
        'outer_id': FACESET_OUTER_ID,
        'face_tokens': '',
    }
    response = requests.post(url, data=data)
    result = response.json()
    # Ignore if FaceSet already exists
    if 'error_message' in result and result['error_message'] != 'FACESET_EXIST':
        print(f"Error creating FaceSet: {result['error_message']}")

def add_face_to_faceset(face_token):
    url = 'https://api-us.faceplusplus.com/facepp/v3/faceset/addface'
    data = {
        'api_key': API_KEY,
        'api_secret': API_SECRET,
        'outer_id': FACESET_OUTER_ID,
        'face_tokens': face_token,
    }
    response = requests.post(url, data=data)
    result = response.json()
    return result.get('face_added', 0) > 0

def search_face(face_token):
    url = 'https://api-us.faceplusplus.com/facepp/v3/search'
    data = {
        'api_key': API_KEY,
        'api_secret': API_SECRET,
        'face_token': face_token,
        'outer_id': FACESET_OUTER_ID,
    }
    response = requests.post(url, data=data)
    result = response.json()
    if 'results' in result and len(result['results']) > 0:
        confidence = result['results'][0]['confidence']
        return confidence > 80  # threshold
    else:
        return False

@app.route('/faces', methods=['POST'])
def handle_face():
    """
    Accepts multipart/form-data:
    - file: image file (required)
    - action: 'register' or 'checkin' (required)
    """
    if 'file' not in request.files or 'action' not in request.form:
        return jsonify({"success": False, "message": "Missing file or action"}), 400

    file = request.files['file']
    action = request.form['action'].lower()
    if action not in ['register', 'checkin']:
        return jsonify({"success": False, "message": "Invalid action"}), 400

    # Save the file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        resize_image_if_needed(tmp_path)
        face_token = detect_face(tmp_path)
        if not face_token:
            return jsonify({"success": False, "message": "No face detected in the image."}), 400

        if action == 'register':
            created = add_face_to_faceset(face_token)
            if created:
                return jsonify({"success": True, "message": "Face registered successfully."})
            else:
                return jsonify({"success": False, "message": "Failed to add face to FaceSet."}), 500

        elif action == 'checkin':
            matched = search_face(face_token)
            if matched:
                return jsonify({"success": True, "message": "Check-in successful. Face recognized."})
            else:
                return jsonify({"success": False, "message": "Face not recognized. Check-in denied."}), 401

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == '__main__':
    create_faceset()
    app.run(host='127.0.0.1', port=5000, debug=False)
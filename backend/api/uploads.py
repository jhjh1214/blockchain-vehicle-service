from flask import Blueprint, request, jsonify, send_from_directory
from api.middleware import token_required
from core import upload_service
from config import Config
from extensions import limiter

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/photo', methods=['POST'])
@limiter.limit('20 per hour')
@token_required
def upload_photo():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    try:
        result = upload_service.save_file(request.files['file'], request.user['user_id'])
        return jsonify({'message': 'File uploaded successfully', **result}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@upload_bp.route('/photos', methods=['POST'])
@limiter.limit('20 per hour')
@token_required
def upload_multiple_photos():
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No files selected'}), 400
    uploaded, errors = upload_service.save_multiple_files(files, request.user['user_id'])
    return jsonify({'message': f'Uploaded {len(uploaded)} files', 'files': uploaded, 'errors': errors}), 200


@upload_bp.route('/files/<filename>', methods=['GET'])
def get_uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

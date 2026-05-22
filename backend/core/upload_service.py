import os
from datetime import datetime
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


def _allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file, user_id: int) -> dict:
    if not file or file.filename == '':
        raise ValueError('No file selected')
    if not _allowed_file(file.filename):
        raise ValueError('Invalid file type. Allowed: png, jpg, jpeg, gif, pdf')

    filename = secure_filename(file.filename)
    timestamp = int(datetime.now().timestamp())
    filename = f"{user_id}_{timestamp}_{filename}"

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file.save(os.path.join(UPLOAD_FOLDER, filename))

    return {'filename': filename, 'url': f'/api/upload/files/{filename}'}


def save_multiple_files(files, user_id: int) -> tuple[list, list]:
    uploaded, errors = [], []
    for file in files:
        try:
            uploaded.append(save_file(file, user_id))
        except ValueError as e:
            errors.append(f"{file.filename}: {e}")
    return uploaded, errors

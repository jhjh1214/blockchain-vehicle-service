import os
from datetime import datetime
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per file

# Magic bytes (file signatures) for allowed types — defence against extension spoofing
_MAGIC_SIGNATURES = [
    (b'\xff\xd8\xff', 'image/jpeg'),        # JPEG
    (b'\x89PNG\r\n\x1a\n', 'image/png'),    # PNG
    (b'GIF87a', 'image/gif'),               # GIF87
    (b'GIF89a', 'image/gif'),               # GIF89
    (b'%PDF-', 'application/pdf'),           # PDF
]


def _allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _check_magic_bytes(file) -> bool:
    """Read the first 8 bytes and confirm they match a known safe file type."""
    header = file.read(8)
    file.seek(0)
    return any(header.startswith(sig) for sig, _ in _MAGIC_SIGNATURES)


def save_file(file, user_id: int) -> dict:
    if not file or file.filename == '':
        raise ValueError('No file selected')
    if not _allowed_file(file.filename):
        raise ValueError('Invalid file type. Allowed: png, jpg, jpeg, gif, pdf')
    if not _check_magic_bytes(file):
        raise ValueError('File content does not match its extension')

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        raise ValueError(f'File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB')

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

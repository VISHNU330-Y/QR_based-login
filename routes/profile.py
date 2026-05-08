import base64
from flask import Blueprint, request, jsonify
from models.database import query_db, execute_db
from utils.jwt_utils import login_required

profile_bp = Blueprint('profile', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@profile_bp.route('/api/profile/photo', methods=['POST'])
@login_required()
def upload_photo():
    """Upload or update profile photo (stored as base64 data URI)."""
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo file provided'}), 400

    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use PNG, JPG, GIF, or WebP'}), 400

    file_data = file.read()
    if len(file_data) > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large. Maximum size is 2 MB'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    mime_map = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif', 'webp': 'webp'}
    mime = mime_map.get(ext, 'png')
    b64 = base64.b64encode(file_data).decode('utf-8')
    data_uri = f'data:image/{mime};base64,{b64}'

    execute_db(
        'UPDATE users SET photo_url = ? WHERE id = ?',
        (data_uri, request.user['user_id'])
    )

    user = query_db(
        'SELECT id, username, name, role, department, roll_no, photo_url, hostel_block FROM users WHERE id = ?',
        (request.user['user_id'],), one=True
    )

    return jsonify({'message': 'Profile photo updated', 'user': user})


@profile_bp.route('/api/profile/photo', methods=['DELETE'])
@login_required()
def remove_photo():
    """Remove profile photo (revert to avatar initials)."""
    execute_db(
        'UPDATE users SET photo_url = NULL WHERE id = ?',
        (request.user['user_id'],)
    )
    return jsonify({'message': 'Profile photo removed'})


@profile_bp.route('/api/profile/update', methods=['PUT'])
@login_required()
def update_profile():
    """Update basic profile fields (name, parent_contact)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    allowed_fields = {'name', 'parent_contact'}
    updates = []
    values = []
    for field in allowed_fields:
        if field in data and data[field] is not None:
            updates.append(f'{field} = ?')
            values.append(data[field].strip())

    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    values.append(request.user['user_id'])
    execute_db(
        f'UPDATE users SET {", ".join(updates)} WHERE id = ?',
        tuple(values)
    )

    user = query_db(
        'SELECT id, username, name, role, department, roll_no, photo_url, hostel_block, year, parent_contact FROM users WHERE id = ?',
        (request.user['user_id'],), one=True
    )

    return jsonify({'message': 'Profile updated', 'user': user})

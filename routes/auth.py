from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from models.database import query_db
from utils.jwt_utils import generate_token, decode_token

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    user = query_db(
        'SELECT * FROM users WHERE username = ?',
        (username,), one=True
    )

    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    if not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = generate_token(user)

    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'name': user['name'],
            'role': user['role'],
            'department': user['department'],
            'roll_no': user['roll_no'],
            'photo_url': user['photo_url'],
            'hostel_block': user['hostel_block']
        }
    })


@auth_bp.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Get current user info from JWT."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401

    token = auth_header.split(' ')[1]
    payload = decode_token(token)

    if not payload:
        return jsonify({'error': 'Invalid or expired token'}), 401

    user = query_db(
        'SELECT id, username, name, role, department, roll_no, photo_url, hostel_block FROM users WHERE id = ?',
        (payload['user_id'],), one=True
    )

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user})

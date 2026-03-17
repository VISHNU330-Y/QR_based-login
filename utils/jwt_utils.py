import jwt
import datetime
from functools import wraps
from flask import request, jsonify
from config import JWT_SECRET


def generate_token(user):
    """Generate a JWT token for a user."""
    payload = {
        'user_id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'department': user.get('department', ''),
        'name': user['name'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def decode_token(token):
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(allowed_roles=None):
    """Decorator to protect routes with JWT authentication."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None

            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

            if not token:
                return jsonify({'error': 'Authentication required'}), 401

            payload = decode_token(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401

            if allowed_roles and payload['role'] not in allowed_roles:
                return jsonify({'error': 'Access denied'}), 403

            request.user = payload
            return f(*args, **kwargs)

        return decorated_function
    return decorator

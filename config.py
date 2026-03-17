import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY', 'qr-gate-pass-secret-key-2026')
JWT_SECRET = os.environ.get('JWT_SECRET', 'jwt-super-secret-key-2026')
QR_SECRET = os.environ.get('QR_SECRET', 'qr-token-hmac-secret-2026')

DATABASE_PATH = os.path.join(BASE_DIR, 'gatepass.db')

QR_EXPIRY_HOURS = 24

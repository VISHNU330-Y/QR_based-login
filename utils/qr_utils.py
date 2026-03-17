import qrcode
import uuid
import hmac
import hashlib
import json
import io
import base64
import datetime
from config import QR_SECRET, QR_EXPIRY_HOURS


def generate_qr_token(pass_id, qr_type, student_id):
    """Generate a unique, signed QR token."""
    unique_id = str(uuid.uuid4())
    raw = f"{pass_id}:{qr_type}:{student_id}:{unique_id}"
    signature = hmac.new(
        QR_SECRET.encode(), raw.encode(), hashlib.sha256
    ).hexdigest()[:16]
    return f"{unique_id}-{signature}"


def generate_qr_data(pass_id, student_id, qr_type, date, time_value, token):
    """Create the JSON data to encode in the QR code."""
    data = {
        'pass_id': pass_id,
        'student_id': student_id,
        'qr_type': qr_type,
        'date': date,
        'time': time_value,
        'token': token
    }
    return json.dumps(data)


def generate_qr_image(data):
    """Generate a QR code image and return as base64 string."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0f0f23", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def generate_qr_pair(pass_id, student_id, date, exit_time, return_time):
    """Generate both exit and entry QR codes for a gate pass."""
    expiry = (datetime.datetime.utcnow() +
              datetime.timedelta(hours=QR_EXPIRY_HOURS)).isoformat()

    # Exit QR
    exit_token = generate_qr_token(pass_id, 'exit', student_id)
    exit_data = generate_qr_data(
        pass_id, student_id, 'exit', date, exit_time, exit_token
    )
    exit_image = generate_qr_image(exit_data)

    # Entry QR
    entry_token = generate_qr_token(pass_id, 'entry', student_id)
    entry_data = generate_qr_data(
        pass_id, student_id, 'entry', date, return_time, entry_token
    )
    entry_image = generate_qr_image(entry_data)

    return {
        'exit': {
            'token': exit_token,
            'data': exit_data,
            'image': exit_image,
            'expiry': expiry
        },
        'entry': {
            'token': entry_token,
            'data': entry_data,
            'image': entry_image,
            'expiry': expiry
        }
    }


def verify_qr_token(qr_data_str):
    """Verify QR code data and return parsed info."""
    try:
        data = json.loads(qr_data_str)
        required = ['pass_id', 'student_id', 'qr_type', 'token']
        for field in required:
            if field not in data:
                return None, "Invalid QR code format"
        return data, None
    except (json.JSONDecodeError, Exception) as e:
        return None, f"Invalid QR code: {str(e)}"

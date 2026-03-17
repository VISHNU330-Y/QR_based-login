from flask import Blueprint, request, jsonify
from models.database import query_db, execute_db
from utils.jwt_utils import login_required
from utils.qr_utils import verify_qr_token
import datetime

security_bp = Blueprint('security', __name__)


@security_bp.route('/api/security/verify', methods=['POST'])
@login_required(allowed_roles=['security'])
def verify_qr():
    """Verify a scanned QR code and return student details."""
    data = request.get_json()
    if not data or not data.get('qr_data'):
        return jsonify({'error': 'No QR data provided'}), 400

    qr_data_str = data['qr_data']

    # Parse and verify QR data
    parsed, error = verify_qr_token(qr_data_str)
    if error:
        return jsonify({'error': error, 'valid': False}), 400

    # Look up QR in database
    qr_record = query_db(
        'SELECT * FROM qr_codes WHERE qr_token = ?',
        (parsed['token'],), one=True
    )

    if not qr_record:
        return jsonify({'error': 'QR code not found. Possible fake QR!', 'valid': False}), 404

    # Check if already used
    if qr_record['is_used']:
        return jsonify({'error': 'QR code already used!', 'valid': False}), 400

    # Check expiry
    expiry = datetime.datetime.fromisoformat(qr_record['qr_expiry'])
    if datetime.datetime.utcnow() > expiry:
        return jsonify({'error': 'QR code has expired!', 'valid': False}), 400

    # Get gate pass details
    gate_pass = query_db(
        'SELECT * FROM gate_passes WHERE id = ?',
        (qr_record['pass_id'],), one=True
    )

    if not gate_pass:
        return jsonify({'error': 'Gate pass not found', 'valid': False}), 404

    # Get student details
    student = query_db(
        'SELECT id, name, roll_no, department, year, hostel_block, photo_url FROM users WHERE id = ?',
        (gate_pass['student_id'],), one=True
    )

    if not student:
        return jsonify({'error': 'Student not found', 'valid': False}), 404

    # Determine pass validity status
    pass_valid = True
    status_message = 'Valid'

    if qr_record['qr_type'] == 'exit' and gate_pass['pass_status'] != 'warden_approved':
        pass_valid = False
        status_message = 'Exit not allowed - pass not in correct state'

    if qr_record['qr_type'] == 'entry' and gate_pass['pass_status'] != 'exit_used':
        pass_valid = False
        status_message = 'Entry not allowed - student has not exited yet'

    return jsonify({
        'valid': pass_valid,
        'status_message': status_message,
        'qr_type': qr_record['qr_type'],
        'student': student,
        'gate_pass': {
            'id': gate_pass['id'],
            'reason': gate_pass['reason'],
            'destination': gate_pass['destination'],
            'date': gate_pass['date'],
            'exit_time': gate_pass['exit_time'],
            'return_time': gate_pass['return_time'],
            'pass_status': gate_pass['pass_status']
        }
    })


@security_bp.route('/api/security/allow-exit/<int:pass_id>', methods=['POST'])
@login_required(allowed_roles=['security'])
def allow_exit(pass_id):
    """Record student exit and mark exit QR as used."""
    data = request.get_json() or {}
    gate_number = data.get('gate_number', 'Gate 1')

    gate_pass = query_db(
        'SELECT * FROM gate_passes WHERE id = ?',
        (pass_id,), one=True
    )

    if not gate_pass:
        return jsonify({'error': 'Gate pass not found'}), 404

    if gate_pass['pass_status'] != 'warden_approved':
        return jsonify({'error': 'Pass is not in the right state for exit'}), 400

    # Mark exit QR as used
    execute_db(
        'UPDATE qr_codes SET is_used = 1 WHERE pass_id = ? AND qr_type = ?',
        (pass_id, 'exit')
    )

    # Update pass status
    execute_db(
        'UPDATE gate_passes SET pass_status = ? WHERE id = ?',
        ('exit_used', pass_id)
    )

    # Log the exit
    execute_db(
        '''INSERT INTO security_logs (pass_id, action_type, gate_number, security_guard_id)
           VALUES (?, 'exit', ?, ?)''',
        (pass_id, gate_number, request.user['user_id'])
    )

    return jsonify({'message': 'Exit recorded successfully'})


@security_bp.route('/api/security/allow-entry/<int:pass_id>', methods=['POST'])
@login_required(allowed_roles=['security'])
def allow_entry(pass_id):
    """Record student entry and mark entry QR as used."""
    data = request.get_json() or {}
    gate_number = data.get('gate_number', 'Gate 1')

    gate_pass = query_db(
        'SELECT * FROM gate_passes WHERE id = ?',
        (pass_id,), one=True
    )

    if not gate_pass:
        return jsonify({'error': 'Gate pass not found'}), 404

    if gate_pass['pass_status'] != 'exit_used':
        return jsonify({'error': 'Student has not exited yet'}), 400

    # Mark entry QR as used
    execute_db(
        'UPDATE qr_codes SET is_used = 1 WHERE pass_id = ? AND qr_type = ?',
        (pass_id, 'entry')
    )

    # Update pass status to completed
    execute_db(
        'UPDATE gate_passes SET pass_status = ? WHERE id = ?',
        ('completed', pass_id)
    )

    # Log the entry
    execute_db(
        '''INSERT INTO security_logs (pass_id, action_type, gate_number, security_guard_id)
           VALUES (?, 'entry', ?, ?)''',
        (pass_id, gate_number, request.user['user_id'])
    )

    return jsonify({'message': 'Entry recorded. Pass completed!'})


@security_bp.route('/api/security/logs', methods=['GET'])
@login_required(allowed_roles=['security'])
def get_logs():
    """Get recent security logs."""
    logs = query_db(
        '''SELECT sl.*, gp.destination, gp.date, gp.exit_time, gp.return_time,
                  u.name as student_name, u.roll_no, u.department
           FROM security_logs sl
           JOIN gate_passes gp ON sl.pass_id = gp.id
           JOIN users u ON gp.student_id = u.id
           ORDER BY sl.timestamp DESC
           LIMIT 50'''
    )
    return jsonify({'logs': logs})

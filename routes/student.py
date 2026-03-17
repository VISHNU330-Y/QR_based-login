from flask import Blueprint, request, jsonify
from models.database import query_db, execute_db
from utils.jwt_utils import login_required

student_bp = Blueprint('student', __name__)


@student_bp.route('/api/student/apply', methods=['POST'])
@login_required(allowed_roles=['student'])
def apply_gate_pass():
    """Student applies for a gate pass."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['reason', 'destination', 'date', 'exit_time', 'return_time']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    student = query_db(
        'SELECT * FROM users WHERE id = ?',
        (request.user['user_id'],), one=True
    )
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    pass_id = execute_db(
        '''INSERT INTO gate_passes
           (student_id, reason, destination, date, exit_time, return_time, parent_contact,
            hod_status, warden_status, pass_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 'pending', 'requested')''',
        (
            request.user['user_id'],
            data['reason'],
            data['destination'],
            data['date'],
            data['exit_time'],
            data['return_time'],
            data.get('parent_contact', student.get('parent_contact', ''))
        )
    )

    return jsonify({
        'message': 'Gate pass request submitted successfully',
        'pass_id': pass_id
    }), 201


@student_bp.route('/api/student/passes', methods=['GET'])
@login_required(allowed_roles=['student'])
def get_passes():
    """Get all gate passes for the logged-in student."""
    passes = query_db(
        '''SELECT gp.*,
           (SELECT qr_image FROM qr_codes WHERE pass_id = gp.id AND qr_type = 'exit') as exit_qr_image,
           (SELECT qr_image FROM qr_codes WHERE pass_id = gp.id AND qr_type = 'entry') as entry_qr_image,
           (SELECT is_used FROM qr_codes WHERE pass_id = gp.id AND qr_type = 'exit') as exit_qr_used,
           (SELECT is_used FROM qr_codes WHERE pass_id = gp.id AND qr_type = 'entry') as entry_qr_used
           FROM gate_passes gp
           WHERE gp.student_id = ?
           ORDER BY gp.created_at DESC''',
        (request.user['user_id'],)
    )
    return jsonify({'passes': passes})


@student_bp.route('/api/student/qr/<int:pass_id>', methods=['GET'])
@login_required(allowed_roles=['student'])
def get_qr_codes(pass_id):
    """Get QR codes for a specific gate pass."""
    gate_pass = query_db(
        'SELECT * FROM gate_passes WHERE id = ? AND student_id = ?',
        (pass_id, request.user['user_id']), one=True
    )
    if not gate_pass:
        return jsonify({'error': 'Gate pass not found'}), 404

    if gate_pass['pass_status'] not in ('warden_approved', 'exit_used'):
        return jsonify({'error': 'QR codes not yet available'}), 400

    qr_codes = query_db(
        'SELECT * FROM qr_codes WHERE pass_id = ?',
        (pass_id,)
    )

    result = {}
    for qr in qr_codes:
        result[qr['qr_type']] = {
            'image': qr['qr_image'],
            'token': qr['qr_token'],
            'expiry': qr['qr_expiry'],
            'is_used': bool(qr['is_used'])
        }

    return jsonify({'qr_codes': result, 'gate_pass': gate_pass})


@student_bp.route('/api/student/cancel/<int:pass_id>', methods=['POST'])
@login_required(allowed_roles=['student'])
def cancel_pass(pass_id):
    """Student cancels their gate pass."""
    gate_pass = query_db(
        'SELECT * FROM gate_passes WHERE id = ? AND student_id = ?',
        (pass_id, request.user['user_id']), one=True
    )
    if not gate_pass:
        return jsonify({'error': 'Gate pass not found'}), 404

    if gate_pass['pass_status'] not in ('requested', 'hod_approved'):
        return jsonify({'error': 'Cannot cancel this pass'}), 400

    execute_db(
        'UPDATE gate_passes SET pass_status = ? WHERE id = ?',
        ('cancelled', pass_id)
    )

    return jsonify({'message': 'Gate pass cancelled'})

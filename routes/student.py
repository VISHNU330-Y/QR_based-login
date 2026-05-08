from datetime import date as date_cls
from flask import Blueprint, request, jsonify
from models.database import query_db, execute_db
from utils.jwt_utils import login_required
from routes.notifications import notify_role

student_bp = Blueprint('student', __name__)


@student_bp.route('/api/student/apply', methods=['POST'])
@login_required(allowed_roles=['student'])
def apply_gate_pass():
    """Student applies for a gate pass."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['reason', 'destination', 'date', 'exit_time', 'return_time', 'student_phone', 'parent_contact']
    for field in required:
        if not data.get(field):
            label = field.replace('_', ' ').title()
            return jsonify({'error': f'{label} is required'}), 400

    try:
        outing_date = date_cls.fromisoformat(data['date'])
        if outing_date < date_cls.today():
            return jsonify({'error': 'Outing date cannot be in the past'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    if data.get('return_date'):
        try:
            ret_date = date_cls.fromisoformat(data['return_date'])
            if ret_date < outing_date:
                return jsonify({'error': 'Return date cannot be before outing date'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid return date format'}), 400

    student = query_db(
        'SELECT * FROM users WHERE id = ?',
        (request.user['user_id'],), one=True
    )
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    pass_id = execute_db(
        '''INSERT INTO gate_passes
           (student_id, reason, destination, date, exit_time, return_time,
            return_date, student_phone, parent_contact,
            hod_status, warden_status, pass_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'pending', 'requested')''',
        (
            request.user['user_id'],
            data['reason'],
            data['destination'],
            data['date'],
            data['exit_time'],
            data['return_time'],
            data.get('return_date', data['date']),
            data['student_phone'],
            data.get('parent_contact', student.get('parent_contact', ''))
        )
    )

    notify_role(
        'hod',
        '📥 New Gate Pass Request',
        f"{student['name']} ({student['roll_no']}) requested an outing to {data['destination']} on {data['date']}.",
        'info',
        pass_id,
        department=student.get('department')
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

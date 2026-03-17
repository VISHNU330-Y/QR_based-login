from flask import Blueprint, request, jsonify
from models.database import query_db, execute_db
from utils.jwt_utils import login_required

hod_bp = Blueprint('hod', __name__)


@hod_bp.route('/api/hod/requests', methods=['GET'])
@login_required(allowed_roles=['hod'])
def get_requests():
    """Get gate pass requests for HOD's department."""
    department = request.user.get('department', '')
    status_filter = request.args.get('status', 'all')

    query = '''
        SELECT gp.*, u.name as student_name, u.roll_no, u.department,
               u.year, u.hostel_block, u.photo_url
        FROM gate_passes gp
        JOIN users u ON gp.student_id = u.id
        WHERE u.department = ?
    '''
    args = [department]

    if status_filter == 'pending':
        query += ' AND gp.hod_status = ?'
        args.append('pending')
    elif status_filter == 'approved':
        query += ' AND gp.hod_status = ?'
        args.append('approved')
    elif status_filter == 'rejected':
        query += ' AND gp.hod_status = ?'
        args.append('rejected')

    query += ' ORDER BY gp.created_at DESC'

    requests_list = query_db(query, tuple(args))
    return jsonify({'requests': requests_list})


@hod_bp.route('/api/hod/approve/<int:pass_id>', methods=['POST'])
@login_required(allowed_roles=['hod'])
def approve_request(pass_id):
    """HOD approves a gate pass request."""
    data = request.get_json() or {}
    remarks = data.get('remarks', '')

    gate_pass = query_db(
        '''SELECT gp.*, u.department FROM gate_passes gp
           JOIN users u ON gp.student_id = u.id
           WHERE gp.id = ? AND u.department = ?''',
        (pass_id, request.user.get('department', '')), one=True
    )

    if not gate_pass:
        return jsonify({'error': 'Request not found in your department'}), 404

    if gate_pass['hod_status'] != 'pending':
        return jsonify({'error': 'Request already processed'}), 400

    execute_db(
        '''UPDATE gate_passes
           SET hod_status = 'approved', pass_status = 'hod_approved',
               hod_id = ?, hod_remarks = ?
           WHERE id = ?''',
        (request.user['user_id'], remarks, pass_id)
    )

    return jsonify({'message': 'Request approved successfully'})


@hod_bp.route('/api/hod/reject/<int:pass_id>', methods=['POST'])
@login_required(allowed_roles=['hod'])
def reject_request(pass_id):
    """HOD rejects a gate pass request."""
    data = request.get_json() or {}
    remarks = data.get('remarks', 'Rejected by HOD')

    gate_pass = query_db(
        '''SELECT gp.*, u.department FROM gate_passes gp
           JOIN users u ON gp.student_id = u.id
           WHERE gp.id = ? AND u.department = ?''',
        (pass_id, request.user.get('department', '')), one=True
    )

    if not gate_pass:
        return jsonify({'error': 'Request not found in your department'}), 404

    if gate_pass['hod_status'] != 'pending':
        return jsonify({'error': 'Request already processed'}), 400

    execute_db(
        '''UPDATE gate_passes
           SET hod_status = 'rejected', pass_status = 'rejected_hod',
               hod_id = ?, hod_remarks = ?
           WHERE id = ?''',
        (request.user['user_id'], remarks, pass_id)
    )

    return jsonify({'message': 'Request rejected'})


@hod_bp.route('/api/hod/stats', methods=['GET'])
@login_required(allowed_roles=['hod'])
def get_stats():
    """Get HOD dashboard statistics."""
    department = request.user.get('department', '')

    pending = query_db(
        '''SELECT COUNT(*) as count FROM gate_passes gp
           JOIN users u ON gp.student_id = u.id
           WHERE u.department = ? AND gp.hod_status = 'pending' ''',
        (department,), one=True
    )

    approved_today = query_db(
        '''SELECT COUNT(*) as count FROM gate_passes gp
           JOIN users u ON gp.student_id = u.id
           WHERE u.department = ? AND gp.hod_status = 'approved'
           AND DATE(gp.created_at) = DATE('now') ''',
        (department,), one=True
    )

    total = query_db(
        '''SELECT COUNT(*) as count FROM gate_passes gp
           JOIN users u ON gp.student_id = u.id
           WHERE u.department = ? ''',
        (department,), one=True
    )

    return jsonify({
        'pending': pending['count'] if pending else 0,
        'approved_today': approved_today['count'] if approved_today else 0,
        'total': total['count'] if total else 0
    })

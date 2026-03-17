from flask import Blueprint, request, jsonify
from models.database import query_db, execute_db
from utils.jwt_utils import login_required
from utils.qr_utils import generate_qr_pair

warden_bp = Blueprint('warden', __name__)


@warden_bp.route('/api/warden/requests', methods=['GET'])
@login_required(allowed_roles=['warden'])
def get_requests():
    """Get HOD-approved requests for warden review."""
    status_filter = request.args.get('status', 'all')

    query = '''
        SELECT gp.*, u.name as student_name, u.roll_no, u.department,
               u.year, u.hostel_block, u.photo_url
        FROM gate_passes gp
        JOIN users u ON gp.student_id = u.id
        WHERE gp.hod_status = 'approved'
    '''
    args = []

    if status_filter == 'pending':
        query += ' AND gp.warden_status = ?'
        args.append('pending')
    elif status_filter == 'approved':
        query += ' AND gp.warden_status = ?'
        args.append('approved')
    elif status_filter == 'rejected':
        query += ' AND gp.warden_status = ?'
        args.append('rejected')

    query += ' ORDER BY gp.created_at DESC'

    requests_list = query_db(query, tuple(args))
    return jsonify({'requests': requests_list})


@warden_bp.route('/api/warden/approve/<int:pass_id>', methods=['POST'])
@login_required(allowed_roles=['warden'])
def approve_request(pass_id):
    """Warden approves request and triggers QR generation."""
    data = request.get_json() or {}
    remarks = data.get('remarks', '')

    gate_pass = query_db(
        '''SELECT * FROM gate_passes WHERE id = ? AND hod_status = 'approved' ''',
        (pass_id,), one=True
    )

    if not gate_pass:
        return jsonify({'error': 'Request not found or not HOD-approved'}), 404

    if gate_pass['warden_status'] != 'pending':
        return jsonify({'error': 'Request already processed'}), 400

    # Update gate pass status
    execute_db(
        '''UPDATE gate_passes
           SET warden_status = 'approved', pass_status = 'warden_approved',
               warden_id = ?, warden_remarks = ?
           WHERE id = ?''',
        (request.user['user_id'], remarks, pass_id)
    )

    # Generate QR code pair
    qr_pair = generate_qr_pair(
        pass_id,
        gate_pass['student_id'],
        gate_pass['date'],
        gate_pass['exit_time'],
        gate_pass['return_time']
    )

    # Store Exit QR
    execute_db(
        '''INSERT INTO qr_codes (pass_id, qr_type, qr_token, qr_data, qr_image, qr_expiry)
           VALUES (?, 'exit', ?, ?, ?, ?)''',
        (pass_id, qr_pair['exit']['token'], qr_pair['exit']['data'],
         qr_pair['exit']['image'], qr_pair['exit']['expiry'])
    )

    # Store Entry QR
    execute_db(
        '''INSERT INTO qr_codes (pass_id, qr_type, qr_token, qr_data, qr_image, qr_expiry)
           VALUES (?, 'entry', ?, ?, ?, ?)''',
        (pass_id, qr_pair['entry']['token'], qr_pair['entry']['data'],
         qr_pair['entry']['image'], qr_pair['entry']['expiry'])
    )

    return jsonify({'message': 'Request approved. QR codes generated!'})


@warden_bp.route('/api/warden/reject/<int:pass_id>', methods=['POST'])
@login_required(allowed_roles=['warden'])
def reject_request(pass_id):
    """Warden rejects a request."""
    data = request.get_json() or {}
    remarks = data.get('remarks', 'Rejected by Warden')

    gate_pass = query_db(
        '''SELECT * FROM gate_passes WHERE id = ? AND hod_status = 'approved' ''',
        (pass_id,), one=True
    )

    if not gate_pass:
        return jsonify({'error': 'Request not found'}), 404

    if gate_pass['warden_status'] != 'pending':
        return jsonify({'error': 'Request already processed'}), 400

    execute_db(
        '''UPDATE gate_passes
           SET warden_status = 'rejected', pass_status = 'rejected_warden',
               warden_id = ?, warden_remarks = ?
           WHERE id = ?''',
        (request.user['user_id'], remarks, pass_id)
    )

    return jsonify({'message': 'Request rejected'})


@warden_bp.route('/api/warden/stats', methods=['GET'])
@login_required(allowed_roles=['warden'])
def get_stats():
    """Get warden dashboard statistics."""
    pending = query_db(
        '''SELECT COUNT(*) as count FROM gate_passes
           WHERE hod_status = 'approved' AND warden_status = 'pending' ''',
        one=True
    )

    approved_today = query_db(
        '''SELECT COUNT(*) as count FROM gate_passes
           WHERE warden_status = 'approved'
           AND DATE(created_at) = DATE('now') ''',
        one=True
    )

    active = query_db(
        '''SELECT COUNT(*) as count FROM gate_passes
           WHERE pass_status IN ('warden_approved', 'exit_used') ''',
        one=True
    )

    return jsonify({
        'pending': pending['count'] if pending else 0,
        'approved_today': approved_today['count'] if approved_today else 0,
        'active_passes': active['count'] if active else 0
    })

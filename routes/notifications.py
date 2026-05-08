from flask import Blueprint, request, jsonify
from models.database import query_db, execute_db
from utils.jwt_utils import login_required

notif_bp = Blueprint('notifications', __name__)


def create_notification(user_id, title, message, notif_type='info', pass_id=None):
    """Create a notification for a specific user."""
    execute_db(
        '''INSERT INTO notifications (user_id, title, message, type, pass_id)
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, title, message, notif_type, pass_id)
    )


def notify_role(role, title, message, notif_type='info', pass_id=None, department=None):
    """Send a notification to all users of a specific role (optionally filtered by department)."""
    if department:
        users = query_db(
            'SELECT id FROM users WHERE role = ? AND department = ?',
            (role, department)
        )
    else:
        users = query_db('SELECT id FROM users WHERE role = ?', (role,))
    for u in users:
        create_notification(u['id'], title, message, notif_type, pass_id)


@notif_bp.route('/api/notifications', methods=['GET'])
@login_required(allowed_roles=['student', 'hod', 'warden', 'security'])
def get_notifications():
    """Get notifications for the logged-in user."""
    limit = request.args.get('limit', 30, type=int)
    notifications = query_db(
        '''SELECT * FROM notifications
           WHERE user_id = ?
           ORDER BY created_at DESC
           LIMIT ?''',
        (request.user['user_id'], limit)
    )
    unread = query_db(
        'SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0',
        (request.user['user_id'],), one=True
    )
    return jsonify({
        'notifications': notifications,
        'unread_count': unread['cnt'] if unread else 0
    })


@notif_bp.route('/api/notifications/read/<int:notif_id>', methods=['POST'])
@login_required(allowed_roles=['student', 'hod', 'warden', 'security'])
def mark_read(notif_id):
    """Mark a single notification as read."""
    execute_db(
        'UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?',
        (notif_id, request.user['user_id'])
    )
    return jsonify({'message': 'Marked as read'})


@notif_bp.route('/api/notifications/read-all', methods=['POST'])
@login_required(allowed_roles=['student', 'hod', 'warden', 'security'])
def mark_all_read():
    """Mark all notifications as read for the logged-in user."""
    execute_db(
        'UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0',
        (request.user['user_id'],)
    )
    return jsonify({'message': 'All notifications marked as read'})

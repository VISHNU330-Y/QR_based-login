from flask import Blueprint, request, jsonify
from models.database import query_db
from utils.jwt_utils import login_required
from utils.ai_engine import (
    calculate_risk_score,
    get_overdue_students,
    get_analytics_data,
    get_student_smart_tips
)

ai_bp = Blueprint('ai', __name__)


# ── Risk Score for a single gate pass ─────────────────────────
@ai_bp.route('/api/ai/risk/<int:pass_id>', methods=['GET'])
@login_required(allowed_roles=['hod', 'warden'])
def get_risk_score(pass_id):
    """Return AI risk score for a gate pass request."""
    gp = query_db('SELECT * FROM gate_passes WHERE id = ?', (pass_id,), one=True)
    if not gp:
        return jsonify({'error': 'Gate pass not found'}), 404
    result = calculate_risk_score(gp, gp['student_id'])
    return jsonify({'pass_id': pass_id, 'ai': result})


# ── Bulk risk scores for a list of pass IDs ───────────────────
@ai_bp.route('/api/ai/risk/bulk', methods=['POST'])
@login_required(allowed_roles=['hod', 'warden'])
def get_bulk_risk():
    """Return risk scores for multiple gate passes at once."""
    data = request.get_json() or {}
    pass_ids = data.get('pass_ids', [])
    results = {}
    for pid in pass_ids[:30]:  # cap at 30
        gp = query_db('SELECT * FROM gate_passes WHERE id = ?', (pid,), one=True)
        if gp:
            results[pid] = calculate_risk_score(gp, gp['student_id'])
    return jsonify({'risk_scores': results})


# ── Overdue students alert ─────────────────────────────────────
@ai_bp.route('/api/ai/overdue', methods=['GET'])
@login_required(allowed_roles=['warden', 'security', 'hod'])
def get_overdue():
    """Return students who are overdue (exited but not returned)."""
    overdue = get_overdue_students()
    return jsonify({
        'overdue': overdue,
        'count':   len(overdue),
        'critical': sum(1 for o in overdue if o['severity'] == 'critical'),
    })


# ── Analytics dashboard data ───────────────────────────────────
@ai_bp.route('/api/ai/analytics', methods=['GET'])
@login_required(allowed_roles=['hod', 'warden', 'security'])
def get_analytics():
    """Return full analytics dataset for charts."""
    data = get_analytics_data()
    return jsonify(data)


# ── Student smart tips ─────────────────────────────────────────
@ai_bp.route('/api/ai/tips', methods=['GET'])
@login_required(allowed_roles=['student'])
def get_tips():
    """Return AI-generated personalized tips for the student."""
    tips = get_student_smart_tips(request.user['user_id'])
    return jsonify({'tips': tips})


# ── Analyze a reason text before submission ────────────────────
@ai_bp.route('/api/ai/analyze-reason', methods=['POST'])
@login_required(allowed_roles=['student'])
def analyze_reason():
    """
    Pre-submission analysis of a reason text.
    Returns predicted risk level and tips to improve approval chances.
    """
    data = request.get_json() or {}
    reason      = data.get('reason', '')
    destination = data.get('destination', '')
    exit_time   = data.get('exit_time', '09:00')
    return_time = data.get('return_time', '18:00')

    mock_pass = {
        'id': 0,
        'reason': reason,
        'destination': destination,
        'exit_time': exit_time,
        'return_time': return_time,
        'date': data.get('date', ''),
    }
    result = calculate_risk_score(mock_pass, request.user['user_id'])

    # Build actionable suggestions
    suggestions = []
    if result.get('safety_alert'):
        suggestions.append('🚨 This request has been flagged for safety review.')
        suggestions.append('⚠️ A staff member will be notified about this request.')
        if result['safety_alert'].get('type') == 'self_harm':
            suggestions.append('💙 If you are struggling, please reach out to the campus counselor or call a helpline.')
    elif result['level'] == 'high':
        suggestions.append('📝 Add more specific details to your reason.')
        suggestions.append('📞 Mention parent/guardian contact.')
        if result['nlp']['high_risk_keywords']:
            suggestions.append('⚠️ Avoid vague or leisure-related terms in your reason.')
        if result['nlp']['reason_category'] == 'insufficient':
            suggestions.append('📝 Your reason is too vague. Provide clear details about where, why, and when.')
    elif result['level'] == 'medium':
        suggestions.append('ℹ️ Providing more context will help speed up approval.')
        if result['nlp']['reason_category'] == 'leisure':
            suggestions.append('💡 Leisure outings get extra scrutiny — add details about urgency if applicable.')

    if result['level'] == 'critical':
        prediction = 'Blocked — requires staff intervention'
    elif result['score'] < 40:
        prediction = 'Likely'
    elif result['score'] < 60:
        prediction = 'Moderate'
    else:
        prediction = 'Unlikely without strong justification'

    return jsonify({
        'ai': result,
        'suggestions': suggestions,
        'approval_prediction': prediction,
    })

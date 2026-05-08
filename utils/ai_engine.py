"""
╔══════════════════════════════════════════════════════════════╗
║           GatePass Pro — AI Intelligence Engine             ║
║   Risk Scoring · Pattern Detection · Anomaly Alerts         ║
╚══════════════════════════════════════════════════════════════╝

This module provides AI-powered analysis for gate pass requests
using multi-factor scoring, NLP-lite keyword analysis, and
behavioral pattern detection — no external API required.
"""

import re
from datetime import datetime, timedelta
from models.database import query_db


# ══════════════════════════════════════════════════════════════
#  KEYWORD DICTIONARIES  (NLP-lite classification)
# ══════════════════════════════════════════════════════════════

LOW_RISK_KEYWORDS = [
    'hospital', 'medical', 'doctor', 'clinic', 'health', 'medicine',
    'pharmacy', 'treatment', 'checkup', 'dental', 'eye', 'lab', 'test',
    'family', 'home', 'parent', 'emergency', 'accident', 'funeral',
    'grandmother', 'grandfather', 'relative', 'urgent',
    'bank', 'passport', 'id', 'document', 'official', 'government',
    'court', 'police', 'embassy', 'visa', 'certificate',
    'college', 'interview', 'exam', 'university', 'campus', 'library',
]

HIGH_RISK_KEYWORDS = [
    'party', 'club', 'bar', 'pub', 'concert', 'movie', 'cinema', 'mall',
    'shopping', 'fun', 'hang out', 'hangout', 'chill', 'friend',
    'night', 'late', 'midnight', 'weekend', 'holiday',
    'protest', 'rally', 'strike', 'demonstration',
]

SUSPICIOUS_PATTERNS = [
    r'\b(?:alcohol|liquor|beer|wine|drink)\b',
    r'\b(?:smoke|smoking|cigarette)\b',
    r'\b(?:casino|gambling|bet)\b',
    r'\b(?:fight|violence|weapon)\b',
]

DESTINATION_RISK = {
    # Low risk destinations
    'hospital': -20, 'clinic': -20, 'medical': -20, 'pharmacy': -10,
    'college': -10, 'university': -10, 'library': -10,
    'home': -15, 'bank': -10, 'government': -10, 'court': -10,
    # High risk destinations
    'mall': 10, 'movie': 15, 'theatre': 15, 'cinema': 15,
    'restaurant': 5,  'market': 5,
}


# ══════════════════════════════════════════════════════════════
#  CORE RISK SCORING  (0–100, higher = riskier)
# ══════════════════════════════════════════════════════════════

def calculate_risk_score(gate_pass: dict, student_id: int) -> dict:
    """
    Multi-factor AI risk scorer.
    Returns:
        {
          score: int (0-100),
          level: str ('low'|'medium'|'high'),
          factors: list[{name, impact, reason}],
          recommendation: str,
          nlp: { reason_category, suspicious_keywords }
        }
    """
    score = 30  # neutral baseline
    factors = []

    reason      = (gate_pass.get('reason') or '').lower()
    destination = (gate_pass.get('destination') or '').lower()
    exit_time   = gate_pass.get('exit_time', '08:00')
    return_time = gate_pass.get('return_time', '18:00')
    pass_date   = gate_pass.get('date', datetime.now().strftime('%Y-%m-%d'))

    # ── Factor 1: Exit time risk ──────────────────────────────
    try:
        exit_h = int(exit_time.split(':')[0])
        if exit_h >= 22 or exit_h < 5:
            score += 30
            factors.append({'name': 'Night Exit', 'impact': 'high',
                             'reason': f'Exit at {exit_time} (late night/early morning)'})
        elif exit_h >= 20:
            score += 15
            factors.append({'name': 'Evening Exit', 'impact': 'medium',
                             'reason': f'Exit at {exit_time} (evening)'})
        elif 6 <= exit_h <= 18:
            score -= 10
            factors.append({'name': 'Daytime Exit', 'impact': 'low',
                             'reason': f'Normal daytime exit at {exit_time}'})
    except Exception:
        pass

    # ── Factor 2: Duration risk ────────────────────────────────
    try:
        eh, em = map(int, exit_time.split(':'))
        rh, rm = map(int, return_time.split(':'))
        duration_mins = (rh * 60 + rm) - (eh * 60 + em)
        if duration_mins < 0:
            duration_mins += 1440  # overnight
        duration_hrs = duration_mins / 60

        if duration_hrs > 10:
            score += 20
            factors.append({'name': 'Very Long Duration', 'impact': 'high',
                             'reason': f'{duration_hrs:.1f}h outing (over 10 hours)'})
        elif duration_hrs > 6:
            score += 10
            factors.append({'name': 'Long Duration', 'impact': 'medium',
                             'reason': f'{duration_hrs:.1f}h outing'})
        elif duration_hrs <= 3:
            score -= 5
            factors.append({'name': 'Short Duration', 'impact': 'low',
                             'reason': f'Brief outing of {duration_hrs:.1f}h'})
    except Exception:
        pass

    # ── Factor 3: Day of week ──────────────────────────────────
    try:
        dt = datetime.strptime(pass_date, '%Y-%m-%d')
        if dt.weekday() >= 5:  # Saturday or Sunday
            score += 10
            factors.append({'name': 'Weekend Outing', 'impact': 'medium',
                             'reason': 'Request on a weekend'})
    except Exception:
        pass

    # ── Factor 4: NLP Reason Analysis ─────────────────────────
    nlp_category = 'general'
    suspicious_found = []

    low_hits  = [w for w in LOW_RISK_KEYWORDS  if w in reason]
    high_hits = [w for w in HIGH_RISK_KEYWORDS if w in reason]

    for pattern in SUSPICIOUS_PATTERNS:
        m = re.search(pattern, reason, re.IGNORECASE)
        if m:
            suspicious_found.append(m.group())

    if suspicious_found:
        score += 35
        factors.append({'name': 'Suspicious Content', 'impact': 'high',
                         'reason': f'Reason contains flagged terms: {", ".join(suspicious_found)}'})
        nlp_category = 'suspicious'
    elif high_hits:
        score += 15
        factors.append({'name': 'Leisure Activity', 'impact': 'medium',
                         'reason': f'Reason suggests leisure: {", ".join(high_hits[:3])}'})
        nlp_category = 'leisure'
    elif low_hits:
        score -= 15
        factors.append({'name': 'Valid Reason', 'impact': 'low',
                         'reason': f'Genuine reason detected: {", ".join(low_hits[:3])}'})
        nlp_category = 'valid'

    # ── Factor 5: Destination analysis ────────────────────────
    dest_delta = 0
    for dest_key, delta in DESTINATION_RISK.items():
        if dest_key in destination:
            dest_delta += delta
    if dest_delta != 0:
        score += dest_delta
        impact = 'low' if dest_delta < 0 else 'medium'
        factors.append({'name': 'Destination', 'impact': impact,
                         'reason': f'Destination "{gate_pass.get("destination")}" scored {dest_delta:+d}'})

    # ── Factor 6: Outing frequency (past 30 days) ─────────────
    try:
        recent = query_db(
            '''SELECT COUNT(*) as cnt FROM gate_passes
               WHERE student_id = ? AND created_at >= datetime('now', '-30 days')
               AND pass_status != 'cancelled' ''',
            (student_id,), one=True
        )
        freq = recent['cnt'] if recent else 0
        if freq >= 10:
            score += 20
            factors.append({'name': 'High Frequency', 'impact': 'high',
                             'reason': f'{freq} outings in past 30 days'})
        elif freq >= 5:
            score += 8
            factors.append({'name': 'Moderate Frequency', 'impact': 'medium',
                             'reason': f'{freq} outings in past 30 days'})
        elif freq <= 1:
            score -= 5
            factors.append({'name': 'First/Rare Outing', 'impact': 'low',
                             'reason': f'Only {freq} outings in past 30 days'})
    except Exception:
        pass

    # ── Factor 7: Past rejection rate ─────────────────────────
    try:
        rejection = query_db(
            '''SELECT
                 COUNT(*) as total,
                 SUM(CASE WHEN pass_status LIKE 'rejected%' THEN 1 ELSE 0 END) as rejected
               FROM gate_passes WHERE student_id = ?''',
            (student_id,), one=True
        )
        if rejection and rejection['total'] > 3:
            rate = (rejection['rejected'] or 0) / rejection['total']
            if rate > 0.4:
                score += 15
                factors.append({'name': 'High Rejection History', 'impact': 'high',
                                 'reason': f'{rate*100:.0f}% of past requests rejected'})
    except Exception:
        pass

    # ── Factor 8: Pending passes for same day ─────────────────
    try:
        same_day = query_db(
            '''SELECT COUNT(*) as cnt FROM gate_passes
               WHERE student_id = ? AND date = ? AND id != ?
               AND pass_status NOT IN ('cancelled','rejected_hod','rejected_warden','expired') ''',
            (student_id, pass_date, gate_pass.get('id', 0)), one=True
        )
        if same_day and same_day['cnt'] > 0:
            score += 10
            factors.append({'name': 'Duplicate Day', 'impact': 'medium',
                             'reason': f'Another pass already exists for {pass_date}'})
    except Exception:
        pass

    # ── Clamp + Classify ──────────────────────────────────────
    score = max(0, min(100, score))

    if score <= 33:
        level = 'low'
        recommendation = '✅ Low risk — safe to approve quickly.'
    elif score <= 66:
        level = 'medium'
        recommendation = '⚠️ Medium risk — review details before approving.'
    else:
        level = 'high'
        recommendation = '🔴 High risk — verify with student or parent before approving.'

    return {
        'score': score,
        'level': level,
        'factors': factors,
        'recommendation': recommendation,
        'nlp': {
            'reason_category': nlp_category,
            'suspicious_keywords': suspicious_found,
            'low_risk_keywords':  low_hits,
            'high_risk_keywords': high_hits,
        }
    }


# ══════════════════════════════════════════════════════════════
#  OVERDUE DETECTION
# ══════════════════════════════════════════════════════════════

def get_overdue_students():
    """
    Detect students who exited but haven't returned by their expected return time.
    Returns list of overdue gate passes with severity.
    """
    passes = query_db(
        '''SELECT gp.id, gp.date, gp.exit_time, gp.return_time,
                  gp.destination, gp.pass_status,
                  u.name as student_name, u.roll_no, u.department,
                  u.hostel_block, u.parent_contact,
                  sl.timestamp as exit_timestamp
           FROM gate_passes gp
           JOIN users u ON gp.student_id = u.id
           LEFT JOIN security_logs sl ON sl.pass_id = gp.id AND sl.action_type = 'exit'
           WHERE gp.pass_status = 'exit_used'
           ORDER BY gp.date DESC, gp.return_time''',
        ()
    )

    overdue = []
    now = datetime.now()

    for p in passes:
        try:
            return_dt = datetime.strptime(
                f"{p['date']} {p['return_time']}", '%Y-%m-%d %H:%M'
            )
            if now > return_dt:
                overdue_mins = int((now - return_dt).total_seconds() / 60)
                if overdue_mins >= 5:
                    if overdue_mins > 120:
                        severity = 'critical'
                    elif overdue_mins > 30:
                        severity = 'high'
                    else:
                        severity = 'medium'

                    overdue.append({
                        **p,
                        'overdue_minutes': overdue_mins,
                        'severity': severity,
                        'return_dt': return_dt.strftime('%H:%M'),
                    })
        except Exception:
            continue

    return overdue


# ══════════════════════════════════════════════════════════════
#  ANALYTICS DATA
# ══════════════════════════════════════════════════════════════

def get_analytics_data():
    """Generate analytics data for the admin dashboard."""

    # Passes per day — last 14 days
    daily = query_db(
        '''SELECT DATE(created_at) as day, COUNT(*) as count
           FROM gate_passes
           WHERE created_at >= datetime('now', '-14 days')
           GROUP BY DATE(created_at)
           ORDER BY day''',
        ()
    )

    # Status distribution
    status_dist = query_db(
        '''SELECT pass_status, COUNT(*) as count
           FROM gate_passes GROUP BY pass_status''',
        ()
    )

    # Requests by department
    dept_dist = query_db(
        '''SELECT u.department, COUNT(*) as count
           FROM gate_passes gp JOIN users u ON gp.student_id = u.id
           GROUP BY u.department ORDER BY count DESC''',
        ()
    )

    # Hour of exit distribution
    hour_dist = query_db(
        '''SELECT CAST(SUBSTR(exit_time, 1, 2) AS INTEGER) as hour, COUNT(*) as count
           FROM gate_passes GROUP BY hour ORDER BY hour''',
        ()
    )

    # Approval rates
    approval = query_db(
        '''SELECT
             COUNT(*) as total,
             SUM(CASE WHEN pass_status IN ('warden_approved','exit_used','entry_used','completed') THEN 1 ELSE 0 END) as approved,
             SUM(CASE WHEN pass_status LIKE 'rejected%' THEN 1 ELSE 0 END) as rejected,
             SUM(CASE WHEN pass_status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
             SUM(CASE WHEN pass_status = 'completed' THEN 1 ELSE 0 END) as completed
           FROM gate_passes''',
        (), one=True
    )

    # Top destinations
    top_dest = query_db(
        '''SELECT destination, COUNT(*) as count
           FROM gate_passes GROUP BY LOWER(TRIM(destination))
           ORDER BY count DESC LIMIT 8''',
        ()
    )

    # Active students (most outings in 30 days)
    active_students = query_db(
        '''SELECT u.name, u.roll_no, u.department, COUNT(*) as outing_count
           FROM gate_passes gp JOIN users u ON gp.student_id = u.id
           WHERE gp.created_at >= datetime('now', '-30 days')
           AND gp.pass_status != 'cancelled'
           GROUP BY gp.student_id
           ORDER BY outing_count DESC LIMIT 5''',
        ()
    )

    # Average processing time (hod approved - created)
    avg_time = query_db(
        '''SELECT AVG((JULIANDAY(created_at) - JULIANDAY(created_at)) * 24 * 60) as avg_mins
           FROM gate_passes WHERE hod_status = 'approved' ''',
        (), one=True
    )

    # Overdue count
    overdue_list = get_overdue_students()

    return {
        'daily_trend':       daily,
        'status_distribution': status_dist,
        'department_distribution': dept_dist,
        'hour_distribution': hour_dist,
        'approval_stats':    approval or {},
        'top_destinations':  top_dest,
        'active_students':   active_students,
        'overdue_count':     len(overdue_list),
        'total_students':    query_db('SELECT COUNT(*) as c FROM users WHERE role = "student"', (), one=True).get('c', 0),
        'total_passes':      (approval or {}).get('total', 0),
    }


# ══════════════════════════════════════════════════════════════
#  STUDENT SMART TIPS  (shown on student dashboard)
# ══════════════════════════════════════════════════════════════

def get_student_smart_tips(student_id: int) -> list:
    """Return personalized smart tips for a student."""
    tips = []

    # Check for overdue pattern
    overdue_hist = query_db(
        '''SELECT COUNT(*) as cnt FROM gate_passes gp
           LEFT JOIN security_logs sl ON sl.pass_id = gp.id AND sl.action_type = 'entry'
           WHERE gp.student_id = ? AND gp.pass_status = 'exit_used' ''',
        (student_id,), one=True
    )
    if overdue_hist and overdue_hist['cnt'] > 0:
        tips.append({
            'type': 'warning',
            'icon': '⚠️',
            'message': 'You have a pending return. Scan Entry QR immediately after reaching campus.',
        })

    # Count pending passes
    pending = query_db(
        '''SELECT COUNT(*) as cnt FROM gate_passes
           WHERE student_id = ? AND pass_status IN ('requested','hod_approved')''',
        (student_id,), one=True
    )
    if pending and pending['cnt'] > 0:
        tips.append({
            'type': 'info',
            'icon': '⏳',
            'message': f'You have {pending["cnt"]} pending request(s) under review.',
        })

    # Frequency tip
    freq = query_db(
        '''SELECT COUNT(*) as cnt FROM gate_passes
           WHERE student_id = ? AND created_at >= datetime('now', '-7 days')
           AND pass_status != 'cancelled' ''',
        (student_id,), one=True
    )
    if freq and freq['cnt'] >= 4:
        tips.append({
            'type': 'warning',
            'icon': '🔔',
            'message': f'{freq["cnt"]} outings this week — frequent requests may be flagged as high-risk.',
        })

    if not tips:
        tips.append({
            'type': 'success',
            'icon': '✅',
            'message': 'Your record looks good! Keep ensuring timely returns.',
        })

    return tips

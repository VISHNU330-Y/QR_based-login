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
import math
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
    r'\b(?:alcohol|liquor|beer|wine|drink|daru|daaru)\b',
    r'\b(?:smoke|smoking|cigarette|vape|vaping|weed|ganja)\b',
    r'\b(?:casino|gambling|bet|betting|satta)\b',
    r'\b(?:fight|violence|weapon|knife|gun|blade)\b',
    r'\b(?:drug|drugs|pills|overdose|inject)\b',
    r'\b(?:rave|hookah|shisha)\b',
]

# ── CRITICAL SAFETY PATTERNS (immediate escalation) ───────────
CRITICAL_SAFETY_PATTERNS = [
    r'\b(?:suicide|suicidal|kill\s*(?:my)?\s*self|end\s*(?:my)?\s*life)\b',
    r'\b(?:self[\s\-]*harm|cut\s*(?:my)?\s*self|hurt\s*(?:my)?\s*self|wrist)\b',
    r'\b(?:want\s*to\s*die|wanna\s*die|better\s*off\s*dead|no\s*reason\s*to\s*live)\b',
    r'\b(?:jump\s*(?:off|from)|hang\s*(?:my)?\s*self|poison|drown\s*(?:my)?\s*self)\b',
    r'\b(?:kill\s*(?:him|her|them|someone|people)|murder|stab|shoot)\b',
    r'\b(?:bomb|explosive|attack|terror|assault)\b',
    r'\b(?:rape|molest|abuse|harass|trafficking)\b',
    r'\b(?:kidnap|abduct|ransom|hostage)\b',
    r'\b(?:run\s*away|escape|never\s*(?:come|coming)\s*back|disappear)\b',
    r'\b(?:depression|depressed|hopeless|worthless|nobody\s*cares)\b',
    r'\b(?:cutting|bleeding|scars|razor)\b',
    r'\b(?:final\s*goodbye|last\s*day|farewell|end\s*it)\b',
]

# ── PROFANITY / NONSENSE PATTERNS ─────────────────────────────
PROFANITY_PATTERNS = [
    r'\b(?:fuck|shit|ass|bitch|bastard|damn|crap|dick|pussy)\b',
    r'\b(?:wtf|stfu|lmao|lmfao)\b',
    r'\b(?:chutiya|madarchod|bhenchod|bsdk|mc|bc|gandu|saala)\b',
]

DESTINATION_RISK = {
    'hospital': -20, 'clinic': -20, 'medical': -20, 'pharmacy': -10,
    'college': -10, 'university': -10, 'library': -10,
    'home': -15, 'bank': -10, 'government': -10, 'court': -10,
    'mall': 10, 'movie': 15, 'theatre': 15, 'cinema': 15,
    'restaurant': 5,  'market': 5,
}


# ══════════════════════════════════════════════════════════════
#  CORE RISK SCORING  (0–100, higher = riskier)
# ══════════════════════════════════════════════════════════════

def _check_reason_quality(reason: str) -> dict:
    """
    Evaluate how detailed and genuine a reason text appears.
    Returns quality assessment with score penalty and flags.
    """
    words = reason.split()
    word_count = len(words)
    unique_words = len(set(words))
    has_numbers = bool(re.search(r'\d', reason))
    alpha_ratio = sum(1 for c in reason if c.isalpha()) / max(len(reason), 1)
    repeated_chars = bool(re.search(r'(.)\1{4,}', reason))
    all_same_word = (unique_words == 1 and word_count > 2)
    gibberish = bool(re.search(r'[^a-z\s]{5,}', reason)) or repeated_chars or all_same_word

    result = {'penalty': 0, 'flags': [], 'quality': 'good'}

    if word_count == 0:
        result['penalty'] = 25
        result['flags'].append('Empty reason provided')
        result['quality'] = 'empty'
    elif word_count <= 2:
        result['penalty'] = 15
        result['flags'].append('Very vague reason — only 1-2 words')
        result['quality'] = 'vague'
    elif word_count <= 4 and not has_numbers:
        result['penalty'] = 8
        result['flags'].append('Short reason with little detail')
        result['quality'] = 'brief'

    if gibberish:
        result['penalty'] += 20
        result['flags'].append('Reason appears to be gibberish or spam')
        result['quality'] = 'gibberish'

    if alpha_ratio < 0.4 and word_count > 0:
        result['penalty'] += 10
        result['flags'].append('Reason contains excessive non-text characters')

    return result


def _detect_safety_crisis(text: str) -> dict:
    """
    Detect critical safety concerns like self-harm, violence, or threats.
    Returns crisis assessment with matched patterns.
    """
    crisis = {'is_critical': False, 'matched': [], 'category': None, 'profanity': []}

    for pattern in CRITICAL_SAFETY_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            crisis['is_critical'] = True
            crisis['matched'].append(m.group())

    if crisis['matched']:
        harm_words = {'suicide', 'suicidal', 'kill self', 'end life', 'die',
                      'self-harm', 'cut self', 'hurt self', 'wrist',
                      'depression', 'depressed', 'hopeless', 'worthless',
                      'cutting', 'bleeding', 'razor', 'final goodbye',
                      'jump', 'hang', 'poison', 'drown'}
        violence_words = {'kill', 'murder', 'stab', 'shoot', 'bomb',
                          'explosive', 'attack', 'terror', 'assault',
                          'kidnap', 'abduct', 'hostage'}

        matched_lower = ' '.join(crisis['matched']).lower()
        if any(w in matched_lower for w in harm_words):
            crisis['category'] = 'self_harm'
        elif any(w in matched_lower for w in violence_words):
            crisis['category'] = 'violence_threat'
        else:
            crisis['category'] = 'safety_concern'

    for pattern in PROFANITY_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            crisis['profanity'].append(m.group())

    return crisis


def calculate_risk_score(gate_pass: dict, student_id: int) -> dict:
    """
    Multi-factor AI risk scorer with safety-aware analysis.
    Returns:
        {
          score: int (0-100),
          level: str ('low'|'medium'|'high'|'critical'),
          factors: list[{name, impact, reason}],
          recommendation: str,
          nlp: { reason_category, suspicious_keywords },
          safety_alert: dict | None
        }
    """
    score = 35  # neutral baseline
    factors = []

    reason      = (gate_pass.get('reason') or '').lower().strip()
    destination = (gate_pass.get('destination') or '').lower().strip()
    exit_time   = gate_pass.get('exit_time', '08:00')
    return_time = gate_pass.get('return_time', '18:00')
    pass_date   = gate_pass.get('date', datetime.now().strftime('%Y-%m-%d'))
    combined_text = f"{reason} {destination}"

    safety_alert = None

    # ══ CRITICAL SAFETY CHECK (highest priority) ══════════════
    crisis = _detect_safety_crisis(combined_text)
    if crisis['is_critical']:
        score = 100
        safety_alert = {
            'type': crisis['category'],
            'matched_terms': crisis['matched'],
            'action_required': True,
        }
        if crisis['category'] == 'self_harm':
            factors.append({'name': '🚨 WELFARE ALERT', 'impact': 'critical',
                'reason': 'Reason contains self-harm / suicidal language — '
                          'IMMEDIATELY contact counselor and guardians'})
            safety_alert['instructions'] = (
                'DO NOT approve or reject. Escalate to student counselor '
                'and contact parent/guardian immediately. This student may need help.'
            )
        elif crisis['category'] == 'violence_threat':
            factors.append({'name': '🚨 THREAT ALERT', 'impact': 'critical',
                'reason': 'Reason contains violent / threatening language — '
                          'escalate to security and administration immediately'})
            safety_alert['instructions'] = (
                'DO NOT approve. Report to campus security and administration. '
                'This may indicate an active threat.'
            )
        else:
            factors.append({'name': '🚨 SAFETY CONCERN', 'impact': 'critical',
                'reason': 'Reason contains alarming content — review and escalate'})
            safety_alert['instructions'] = (
                'This request contains concerning language. '
                'Contact the student directly and involve relevant authorities.'
            )

    # ── Profanity check (even if not critical) ────────────────
    if crisis['profanity']:
        score += 20
        factors.append({'name': 'Inappropriate Language', 'impact': 'high',
            'reason': f'Reason contains profanity/offensive terms'})

    # ── Reason quality check ──────────────────────────────────
    quality = _check_reason_quality(reason)
    if quality['penalty'] > 0:
        score += quality['penalty']
        for flag in quality['flags']:
            factors.append({'name': 'Reason Quality', 'impact': 'medium' if quality['penalty'] < 15 else 'high',
                'reason': flag})

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
    if crisis['is_critical']:
        nlp_category = 'critical_safety'
    suspicious_found = []

    low_hits  = [w for w in LOW_RISK_KEYWORDS  if re.search(r'\b' + re.escape(w) + r'\b', reason)]
    high_hits = [w for w in HIGH_RISK_KEYWORDS if re.search(r'\b' + re.escape(w) + r'\b', reason)]

    for pattern in SUSPICIOUS_PATTERNS:
        m = re.search(pattern, reason, re.IGNORECASE)
        if m:
            suspicious_found.append(m.group())

    if suspicious_found:
        score += 35
        factors.append({'name': 'Suspicious Content', 'impact': 'high',
                         'reason': f'Reason contains flagged terms: {", ".join(suspicious_found)}'})
        if nlp_category != 'critical_safety':
            nlp_category = 'suspicious'
    elif high_hits:
        score += 15
        factors.append({'name': 'Leisure Activity', 'impact': 'medium',
                         'reason': f'Reason suggests leisure: {", ".join(high_hits[:3])}'})
        if nlp_category != 'critical_safety':
            nlp_category = 'leisure'
    elif low_hits:
        score -= 15
        factors.append({'name': 'Valid Reason', 'impact': 'low',
                         'reason': f'Genuine reason detected: {", ".join(low_hits[:3])}'})
        if nlp_category != 'critical_safety':
            nlp_category = 'valid'
    elif quality['quality'] in ('vague', 'empty', 'gibberish') and not crisis['is_critical']:
        nlp_category = 'insufficient'

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

    if safety_alert:
        level = 'critical'
        score = 100
        recommendation = ('🚨 CRITICAL — This request has been flagged for '
                          'immediate attention. Do NOT process normally. '
                          'Follow the safety instructions above.')
    elif score <= 30:
        level = 'low'
        recommendation = '✅ Low risk — safe to approve quickly.'
    elif score <= 55:
        level = 'medium'
        recommendation = '⚠️ Medium risk — review details before approving.'
    elif score <= 75:
        level = 'high'
        recommendation = '🔴 High risk — verify with student or parent before approving.'
    else:
        level = 'high'
        recommendation = '🔴 Very high risk — strongly consider rejecting or require parent confirmation.'

    result = {
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
    if safety_alert:
        result['safety_alert'] = safety_alert
    return result


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

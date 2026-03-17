/* ============================
   Shared Utilities — API calls, Auth, Toast
   ============================ */

const API_BASE = '';

// ── Auth helpers ──
function getToken() {
    return localStorage.getItem('gatepass_token');
}

function getUser() {
    const raw = localStorage.getItem('gatepass_user');
    return raw ? JSON.parse(raw) : null;
}

function saveAuth(token, user) {
    localStorage.setItem('gatepass_token', token);
    localStorage.setItem('gatepass_user', JSON.stringify(user));
}

function clearAuth() {
    localStorage.removeItem('gatepass_token');
    localStorage.removeItem('gatepass_user');
}

function logout() {
    clearAuth();
    window.location.href = '/';
}

function requireAuth(requiredRole) {
    const token = getToken();
    const user = getUser();
    if (!token || !user) {
        window.location.href = '/';
        return null;
    }
    if (requiredRole && user.role !== requiredRole) {
        window.location.href = '/';
        return null;
    }
    return user;
}

// ── API fetch wrapper ──
async function apiFetch(endpoint, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...(options.headers || {})
    };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
        });

        const data = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                clearAuth();
                window.location.href = '/';
                return null;
            }
            throw new Error(data.error || 'Something went wrong');
        }

        return data;
    } catch (error) {
        if (error.message !== 'Failed to fetch') {
            showToast(error.message, 'error');
        } else {
            showToast('Network error. Please try again.', 'error');
        }
        throw error;
    }
}

// ── Toast notifications ──
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    toast.textContent = `${icons[type] || ''} ${message}`;
    container.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}

// ── Navbar renderer ──
function renderNavbar(user, roleLabel) {
    const initials = user.name ? user.name.split(' ').map(n => n[0]).join('').toUpperCase() : '?';
    return `
        <nav class="navbar">
            <div class="navbar-brand">
                <span class="logo-icon">🔐</span>
                <span>Gate Pass System</span>
            </div>
            <div class="navbar-user">
                <div class="user-info">
                    <div class="name">${user.name}</div>
                    <div class="role">${roleLabel}${user.department ? ' • ' + user.department : ''}</div>
                </div>
                <div class="user-avatar">${initials}</div>
                <button class="btn-logout" onclick="logout()">Logout</button>
            </div>
        </nav>
    `;
}

// ── Status badge ──
function getStatusBadge(status) {
    const map = {
        'requested': { class: 'badge-pending', label: '⏳ Pending HOD', icon: '' },
        'hod_approved': { class: 'badge-active', label: '⏳ Pending Warden', icon: '' },
        'warden_approved': { class: 'badge-approved', label: '✅ Approved', icon: '' },
        'exit_used': { class: 'badge-active', label: '🚪 Exited', icon: '' },
        'entry_used': { class: 'badge-active', label: '🏠 Returned', icon: '' },
        'completed': { class: 'badge-completed', label: '✅ Completed', icon: '' },
        'rejected_hod': { class: 'badge-rejected', label: '❌ Rejected (HOD)', icon: '' },
        'rejected_warden': { class: 'badge-rejected', label: '❌ Rejected (Warden)', icon: '' },
        'expired': { class: 'badge-expired', label: '⏰ Expired', icon: '' },
        'cancelled': { class: 'badge-rejected', label: '🚫 Cancelled', icon: '' },
        'pending': { class: 'badge-pending', label: '⏳ Pending', icon: '' },
        'approved': { class: 'badge-approved', label: '✅ Approved', icon: '' },
        'rejected': { class: 'badge-rejected', label: '❌ Rejected', icon: '' },
    };
    const s = map[status] || { class: 'badge-pending', label: status };
    return `<span class="badge ${s.class}">${s.label}</span>`;
}

// ── Pipeline tracker ──
function renderPipeline(status) {
    const steps = [
        { key: 'requested', label: 'Requested' },
        { key: 'hod_approved', label: 'HOD' },
        { key: 'warden_approved', label: 'Warden' },
        { key: 'exit_used', label: 'Exit' },
        { key: 'completed', label: 'Completed' }
    ];

    const rejected = ['rejected_hod', 'rejected_warden', 'cancelled'].includes(status);
    const statusOrder = ['requested', 'hod_approved', 'warden_approved', 'exit_used', 'completed'];
    const currentIdx = statusOrder.indexOf(status);

    let html = '<div class="pipeline">';
    steps.forEach((step, i) => {
        let cls = '';
        if (rejected && i === currentIdx) cls = 'rejected';
        else if (i < currentIdx || (i === currentIdx && status === 'completed')) cls = 'done';
        else if (i === currentIdx) cls = 'active';

        html += `<span class="pipeline-step ${cls}">${step.label}</span>`;
        if (i < steps.length - 1) {
            html += '<span class="pipeline-arrow">→</span>';
        }
    });
    html += '</div>';
    return html;
}

// ── Format dates ──
function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch { return dateStr; }
}

function formatTime(timeStr) {
    if (!timeStr) return '-';
    return timeStr;
}

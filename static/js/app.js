/* ============================================================
   GatePass Pro — Shared Utilities
   Auth · API · Toast · Navbar · Helpers
   ============================================================ */

const API_BASE = '';

// ── Auth helpers ──────────────────────────────────────────────
function getToken() { return localStorage.getItem('gatepass_token'); }
function getUser()  {
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
  showToast('Logged out successfully', 'info');
  setTimeout(() => { window.location.href = '/'; }, 600);
}
function requireAuth(requiredRole) {
  const token = getToken();
  const user  = getUser();
  if (!token || !user) { window.location.href = '/'; return null; }
  if (requiredRole && user.role !== requiredRole) { window.location.href = '/'; return null; }
  return user;
}

// ── API fetch wrapper ─────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    const data = await response.json();
    if (!response.ok) {
      if (response.status === 401) { clearAuth(); window.location.href = '/'; return null; }
      throw new Error(data.error || 'Something went wrong');
    }
    return data;
  } catch (error) {
    const msg = error.message === 'Failed to fetch'
      ? 'Network error. Please try again.' : error.message;
    showToast(msg, 'error');
    throw error;
  }
}

// ── Toast Notifications ───────────────────────────────────────
function showToast(message, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;

  // click to dismiss
  toast.style.cursor = 'pointer';
  toast.addEventListener('click', () => toast.remove());

  container.appendChild(toast);
  setTimeout(() => { toast.style.animation = 'none'; toast.remove(); }, 3100);
}

// ── Navbar renderer ───────────────────────────────────────────
const ROLE_META = {
  student:  { label: 'Student',       icon: '👨‍🎓', grad: 'linear-gradient(135deg,#00d4ff,#8b5cf6)' },
  hod:      { label: 'HOD',           icon: '👨‍🏫', grad: 'linear-gradient(135deg,#8b5cf6,#ec4899)' },
  warden:   { label: 'Hostel Warden', icon: '🏠', grad: 'linear-gradient(135deg,#10b981,#0f766e)' },
  security: { label: 'Security Gate', icon: '🛡️', grad: 'linear-gradient(135deg,#f59e0b,#d97706)' },
};

function renderNavbar(user, roleLabelOverride) {
  const initials = user.name
    ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0,2)
    : '??';
  const meta = ROLE_META[user.role] || { label: user.role, icon: '👤', grad: 'var(--grad-brand)' };
  const roleLabel = roleLabelOverride || `${meta.icon} ${meta.label}`;
  const dept = user.department ? ` · ${user.department}` : '';

  return `
    <nav class="navbar">
      <div class="navbar-brand">
        <div class="logo-icon">🔐</div>
        <div>
          <span class="brand-name">GatePass Pro</span>
          <span class="brand-sub">Campus Security System</span>
        </div>
      </div>

      <div class="navbar-user">
        <div class="user-pill" onclick="openProfile()" id="userPill" title="Click to view profile" style="cursor:pointer;">
          <div class="user-avatar" style="background:${meta.grad};">${initials}</div>
          <div class="user-info">
            <div class="name">${user.name}</div>
            <div class="role">${roleLabel}${dept}</div>
          </div>
          <svg style="margin-left:6px;flex-shrink:0;opacity:0.5;" width="10" height="6" viewBox="0 0 10 6" fill="none">
            <path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
        <button class="btn-logout" onclick="logout()">⏻ Logout</button>
      </div>
    </nav>

    <!-- ─── Profile Modal ─── -->
    <div class="modal-overlay" id="profileModal" onclick="handleProfileOverlayClick(event)">
      <div class="modal" style="max-width:500px;" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h2 style="display:flex;align-items:center;gap:8px;">
            <span style="width:28px;height:28px;background:var(--grad-brand);border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:0.85rem;">👤</span>
            My Profile
          </h2>
          <button class="modal-close" onclick="closeProfile()">✕</button>
        </div>
        <div id="profileContent"><div class="spinner"></div></div>
      </div>
    </div>`;
}

// ── Profile open / close ───────────────────────────────────────
async function openProfile() {
  const modal = document.getElementById('profileModal');
  if (!modal) return;
  modal.classList.add('active');

  const content = document.getElementById('profileContent');
  content.innerHTML = '<div class="spinner"></div>';

  try {
    const data = await apiFetch('/api/auth/me');
    const u    = data.user;
    const meta = ROLE_META[u.role] || { label: u.role, icon: '👤', grad: 'var(--grad-brand)' };
    const initials = u.name
      ? u.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0,2) : '??';

    const roleColors = {
      student:  { bg:'rgba(0,212,255,0.1)',  color:'#00d4ff', border:'rgba(0,212,255,0.25)'  },
      hod:      { bg:'rgba(139,92,246,0.1)', color:'#8b5cf6', border:'rgba(139,92,246,0.25)' },
      warden:   { bg:'rgba(16,185,129,0.1)', color:'#10b981', border:'rgba(16,185,129,0.25)' },
      security: { bg:'rgba(245,158,11,0.1)', color:'#f59e0b', border:'rgba(245,158,11,0.25)' },
    };
    const rc = roleColors[u.role] || roleColors.student;

    // Build field list — skip blank fields
    const allFields = [
      { icon:'🆔', label:'Username',       value: u.username },
      { icon:'📋', label:'Roll Number',    value: u.roll_no },
      { icon:'🏫', label:'Department',     value: u.department },
      { icon:'📚', label:'Year of Study',  value: u.year ? `Year ${u.year}` : null },
      { icon:'🏠', label:'Hostel Block',   value: u.hostel_block },
      { icon:'📞', label:'Parent Contact', value: u.parent_contact },
    ].filter(f => f.value);

    content.innerHTML = `
      <!-- ── Avatar Hero ── -->
      <div style="text-align:center;padding:8px 0 24px;border-bottom:1px solid var(--border);margin-bottom:20px;">
        <div style="position:relative;display:inline-block;margin-bottom:14px;">
          <div style="width:96px;height:96px;border-radius:50%;background:${meta.grad};
               display:flex;align-items:center;justify-content:center;
               font-size:2.4rem;font-weight:800;color:#fff;
               box-shadow:0 0 0 4px rgba(0,212,255,0.15), 0 8px 24px rgba(0,0,0,0.4);
               border:3px solid rgba(255,255,255,0.08);">
            ${initials}
          </div>
          <div style="position:absolute;bottom:2px;right:2px;width:18px;height:18px;
               background:#10b981;border-radius:50%;border:2px solid var(--bg-surface);"
               title="Active"></div>
        </div>
        <h3 style="font-size:1.4rem;font-weight:800;margin-bottom:8px;">${u.name}</h3>
        <span style="display:inline-flex;align-items:center;gap:6px;padding:5px 16px;border-radius:20px;
              font-size:0.75rem;font-weight:700;letter-spacing:0.6px;text-transform:uppercase;
              background:${rc.bg};color:${rc.color};border:1px solid ${rc.border};">
          ${meta.icon} ${meta.label}
        </span>
      </div>

      <!-- ── Info Fields ── -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px;">
        ${allFields.length ? allFields.map(f => `
          <div style="padding:12px 14px;background:rgba(255,255,255,0.025);
               border:1px solid rgba(255,255,255,0.06);border-radius:var(--r-sm);
               transition:border-color 0.2s;">
            <div style="font-size:0.66rem;text-transform:uppercase;letter-spacing:0.8px;
                 color:var(--text-3);margin-bottom:5px;display:flex;align-items:center;gap:5px;">
              <span>${f.icon}</span> ${f.label}
            </div>
            <div style="font-size:0.88rem;font-weight:600;color:var(--text-1);word-break:break-all;">${f.value}</div>
          </div>`).join('') : ''}
      </div>

      <!-- ── Pass Stats (student only) ── -->
      ${u.role === 'student' ? `
      <div id="profileStats" style="border-top:1px solid var(--border);padding-top:18px;margin-bottom:20px;">
        <div class="spinner" style="width:18px;height:18px;border-width:2px;margin:10px auto;"></div>
      </div>` : ''}

      <!-- ── Member Since ── -->
      <div style="text-align:center;font-size:0.72rem;color:var(--text-3);margin-bottom:20px;">
        🗓 Account ID: <span style="font-family:var(--font-mono);">#${u.id}</span>
        &nbsp;·&nbsp; Role: <span style="color:${rc.color};">${u.role}</span>
      </div>

      <!-- ── Actions ── -->
      <div style="display:flex;gap:10px;">
        <button class="btn btn-ghost w-full" onclick="closeProfile()">✕ Close</button>
        <button class="btn btn-danger w-full" onclick="logout()">⏻ Sign Out</button>
      </div>`;

    // Async load pass stats for students
    if (u.role === 'student') loadProfileStats();

  } catch (err) {
    content.innerHTML = `
      <div style="text-align:center;padding:40px;color:var(--text-3);">
        <div style="font-size:2.5rem;margin-bottom:10px;">⚠️</div>
        <p>Failed to load profile data</p>
        <button class="btn btn-ghost btn-sm mt-md" onclick="closeProfile()">Close</button>
      </div>`;
  }
}

async function loadProfileStats() {
  try {
    const data   = await apiFetch('/api/student/passes');
    const passes = data.passes || [];
    const stats  = [
      { label:'Total',     val: passes.length,                                                                color:'#00d4ff' },
      { label:'Approved',  val: passes.filter(p=>['warden_approved','exit_used','completed'].includes(p.pass_status)).length, color:'#10b981' },
      { label:'Pending',   val: passes.filter(p=>['requested','hod_approved'].includes(p.pass_status)).length, color:'#f59e0b' },
      { label:'Completed', val: passes.filter(p=>p.pass_status==='completed').length,                         color:'#8b5cf6' },
    ];
    const el = document.getElementById('profileStats');
    if (!el) return;
    el.innerHTML = `
      <div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;color:var(--text-3);margin-bottom:10px;">
        📊 Gate Pass Summary
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
        ${stats.map(s => `
          <div style="padding:12px 6px;text-align:center;background:rgba(255,255,255,0.025);
               border:1px solid rgba(255,255,255,0.06);border-radius:var(--r-sm);">
            <div style="font-family:'Outfit',sans-serif;font-size:1.6rem;font-weight:900;
                 color:${s.color};line-height:1;">${s.val}</div>
            <div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:0.4px;
                 color:var(--text-3);margin-top:4px;">${s.label}</div>
          </div>`).join('')}
      </div>`;
  } catch (e) {}
}

function closeProfile() {
  const m = document.getElementById('profileModal');
  if (m) m.classList.remove('active');
}

function handleProfileOverlayClick(e) {
  if (e.target.id === 'profileModal') closeProfile();
}

// Escape key closes profile modal
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeProfile(); });

// ── Status badge ──────────────────────────────────────────────
function getStatusBadge(status) {
  const map = {
    requested:        { cls: 'badge-pending',  label: '⏳ Pending HOD' },
    hod_approved:     { cls: 'badge-active',   label: '⏳ Awaiting Warden' },
    warden_approved:  { cls: 'badge-approved', label: '✅ Fully Approved' },
    exit_used:        { cls: 'badge-active',   label: '🚪 Exited Campus' },
    entry_used:       { cls: 'badge-active',   label: '🏠 Re-entered' },
    completed:        { cls: 'badge-completed',label: '✔ Completed' },
    rejected_hod:     { cls: 'badge-rejected', label: '❌ Rejected by HOD' },
    rejected_warden:  { cls: 'badge-rejected', label: '❌ Rejected by Warden' },
    expired:          { cls: 'badge-expired',  label: '⏰ Expired' },
    cancelled:        { cls: 'badge-rejected', label: '🚫 Cancelled' },
    pending:          { cls: 'badge-pending',  label: '⏳ Pending' },
    approved:         { cls: 'badge-approved', label: '✅ Approved' },
    rejected:         { cls: 'badge-rejected', label: '❌ Rejected' },
  };
  const s = map[status] || { cls: 'badge-pending', label: status };
  return `<span class="badge ${s.cls}">${s.label}</span>`;
}

// ── Approval Pipeline Tracker ─────────────────────────────────
function renderPipeline(status) {
  const steps = [
    { key: 'requested',       label: 'Applied'  },
    { key: 'hod_approved',    label: 'HOD OK'   },
    { key: 'warden_approved', label: 'Warden OK'},
    { key: 'exit_used',       label: 'Exited'   },
    { key: 'completed',       label: 'Done'     },
  ];
  const rejected     = ['rejected_hod','rejected_warden','cancelled'].includes(status);
  const statusOrder  = steps.map(s => s.key);
  const currentIdx   = statusOrder.indexOf(status);

  let html = '<div class="pipeline">';
  steps.forEach((step, i) => {
    let cls = '';
    if (rejected && i === currentIdx) cls = 'rejected';
    else if (i < currentIdx || (i === currentIdx && status === 'completed')) cls = 'done';
    else if (i === currentIdx) cls = 'active';

    html += `<span class="pipeline-step ${cls}">${step.label}</span>`;
    if (i < steps.length - 1) html += '<span class="pipeline-arrow">›</span>';
  });
  html += '</div>';
  return html;
}

// ── Date / Time formatters ────────────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch { return dateStr; }
}

function formatTime(timeStr) {
  if (!timeStr) return '—';
  try {
    const [h, m] = timeStr.split(':');
    const hr = parseInt(h), ampm = hr >= 12 ? 'PM' : 'AM';
    return `${hr % 12 || 12}:${m} ${ampm}`;
  } catch { return timeStr; }
}

function formatDateTime(ts) {
  if (!ts) return '—';
  try {
    const d = new Date(ts);
    return d.toLocaleString('en-IN', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' });
  } catch { return ts; }
}

// ── Relative time ─────────────────────────────────────────────
function timeAgo(dateStr) {
  if (!dateStr) return '';
  try {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1)  return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24)  return `${hrs}h ago`;
    return `${Math.floor(hrs/24)}d ago`;
  } catch { return ''; }
}

// ── Animate counter ───────────────────────────────────────────
function animateCounter(el, to, duration = 800) {
  const from = parseInt(el.textContent) || 0;
  if (from === to) return;
  const start = performance.now();
  function step(now) {
    const t = Math.min((now - start) / duration, 1);
    const ease = t < 0.5 ? 2*t*t : -1+(4-2*t)*t;
    el.textContent = Math.round(from + (to - from) * ease);
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

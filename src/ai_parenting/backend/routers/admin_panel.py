"""Admin 管理面板路由。

提供基于 HTML 的系统管理后台，通过 admin API 端点获取数据。
管理员通过邮箱+密码登录后访问仪表板。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from ai_parenting.backend.auth import get_current_admin_id

router = APIRouter(tags=["admin-panel"])


_ADMIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Parenting — 管理后台</title>
<style>
:root {
  --primary: #6366f1;
  --primary-light: #818cf8;
  --primary-dark: #4f46e5;
  --bg: #f8fafc;
  --card-bg: #ffffff;
  --text: #1e293b;
  --text-secondary: #64748b;
  --border: #e2e8f0;
  --success: #22c55e;
  --danger: #ef4444;
  --warning: #f59e0b;
  --radius: 12px;
  --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}
.login-container {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; padding: 20px;
}
.login-card {
  background: var(--card-bg); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 40px; width: 100%; max-width: 420px;
}
.login-card h1 { font-size: 24px; text-align: center; margin-bottom: 8px; }
.login-card p { color: var(--text-secondary); text-align: center; margin-bottom: 32px; font-size: 14px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 6px; }
.form-group input {
  width: 100%; padding: 10px 14px; border: 1px solid var(--border);
  border-radius: 8px; font-size: 14px; outline: none; transition: border 0.2s;
}
.form-group input:focus { border-color: var(--primary); }
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  padding: 10px 20px; border: none; border-radius: 8px; font-size: 14px;
  font-weight: 500; cursor: pointer; transition: all 0.2s;
}
.btn-primary { background: var(--primary); color: #fff; width: 100%; }
.btn-primary:hover { background: var(--primary-dark); }
.btn-danger { background: var(--danger); color: #fff; }
.btn-danger:hover { background: #dc2626; }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.btn-outline {
  background: transparent; border: 1px solid var(--border); color: var(--text);
}
.btn-outline:hover { background: #f1f5f9; }
.error-msg { color: var(--danger); font-size: 13px; margin-top: 8px; text-align: center; }

/* Dashboard Layout */
.dashboard { display: none; }
.header {
  background: var(--card-bg); border-bottom: 1px solid var(--border);
  padding: 16px 32px; display: flex; justify-content: space-between; align-items: center;
}
.header h1 { font-size: 20px; display: flex; align-items: center; gap: 10px; }
.header .badge {
  font-size: 11px; background: var(--primary-light); color: #fff;
  padding: 2px 8px; border-radius: 10px; font-weight: 400;
}
.main { padding: 24px 32px; max-width: 1400px; margin: 0 auto; }
.stats-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px; margin-bottom: 32px;
}
.stat-card {
  background: var(--card-bg); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 20px;
}
.stat-card .label { font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; }
.stat-card .value { font-size: 28px; font-weight: 700; }
.tabs {
  display: flex; gap: 4px; border-bottom: 2px solid var(--border);
  margin-bottom: 20px;
}
.tab {
  padding: 10px 20px; font-size: 14px; font-weight: 500; cursor: pointer;
  border: none; background: none; color: var(--text-secondary);
  border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.2s;
}
.tab.active { color: var(--primary); border-bottom-color: var(--primary); }
.tab:hover { color: var(--text); }
.section { display: none; }
.section.active { display: block; }
.search-bar {
  display: flex; gap: 12px; margin-bottom: 16px; align-items: center;
}
.search-bar input {
  flex: 1; padding: 8px 14px; border: 1px solid var(--border);
  border-radius: 8px; font-size: 14px; outline: none;
}
.search-bar input:focus { border-color: var(--primary); }
table {
  width: 100%; border-collapse: collapse; background: var(--card-bg);
  border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow);
}
th, td { padding: 12px 16px; text-align: left; font-size: 13px; }
th {
  background: #f8fafc; font-weight: 600; color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
}
td { border-bottom: 1px solid var(--border); }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #fafbfc; }
.badge-tag {
  display: inline-block; padding: 2px 8px; border-radius: 6px;
  font-size: 11px; font-weight: 500;
}
.badge-admin { background: #fef3c7; color: #92400e; }
.badge-user { background: #dbeafe; color: #1e40af; }
.badge-active { background: #dcfce7; color: #166534; }
.badge-completed { background: #e0e7ff; color: #3730a3; }
.pagination {
  display: flex; justify-content: center; gap: 8px; margin-top: 16px;
}
.empty { text-align: center; padding: 40px; color: var(--text-secondary); }
.toast {
  position: fixed; bottom: 20px; right: 20px; background: #1e293b;
  color: #fff; padding: 12px 20px; border-radius: 8px; font-size: 13px;
  z-index: 1000; opacity: 0; transition: opacity 0.3s; pointer-events: none;
}
.toast.show { opacity: 1; }
</style>
</head>
<body>

<!-- Login Screen -->
<div class="login-container" id="loginScreen">
  <div class="login-card">
    <h1>&#x1f511; 管理后台</h1>
    <p>AI Parenting 系统管理</p>
    <div class="form-group">
      <label>邮箱</label>
      <input type="email" id="loginEmail" placeholder="admin@aiparenting.dev" value="admin@aiparenting.dev">
    </div>
    <div class="form-group">
      <label>密码</label>
      <input type="password" id="loginPassword" placeholder="输入密码" value="">
    </div>
    <button class="btn btn-primary" onclick="doLogin()" id="loginBtn">登录</button>
    <div class="error-msg" id="loginError"></div>
  </div>
</div>

<!-- Dashboard -->
<div class="dashboard" id="dashboard">
  <div class="header">
    <h1>AI Parenting <span class="badge">管理后台</span></h1>
    <div style="display:flex;align-items:center;gap:12px">
      <span id="adminName" style="font-size:13px;color:var(--text-secondary)"></span>
      <button class="btn btn-outline btn-sm" onclick="doLogout()">退出</button>
    </div>
  </div>
  <div class="main">
    <!-- Stats -->
    <div class="stats-grid" id="statsGrid"></div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab active" data-tab="users" onclick="switchTab('users')">用户管理</button>
      <button class="tab" data-tab="children" onclick="switchTab('children')">儿童档案</button>
      <button class="tab" data-tab="plans" onclick="switchTab('plans')">训练计划</button>
    </div>

    <!-- Users Section -->
    <div class="section active" id="section-users">
      <div class="search-bar">
        <input type="text" id="userSearch" placeholder="搜索邮箱或昵称..." onkeyup="if(event.key==='Enter')searchUsers()">
        <button class="btn btn-primary btn-sm" onclick="searchUsers()">搜索</button>
      </div>
      <div id="usersTable"></div>
    </div>

    <!-- Children Section -->
    <div class="section" id="section-children">
      <div class="search-bar">
        <input type="text" id="childSearch" placeholder="搜索儿童昵称..." onkeyup="if(event.key==='Enter')searchChildren()">
        <button class="btn btn-primary btn-sm" onclick="searchChildren()">搜索</button>
      </div>
      <div id="childrenTable"></div>
    </div>

    <!-- Plans Section -->
    <div class="section" id="section-plans">
      <div class="search-bar">
        <select id="planStatus" style="padding:8px 12px;border:1px solid var(--border);border-radius:8px;font-size:14px">
          <option value="">全部状态</option>
          <option value="active">进行中</option>
          <option value="completed">已完成</option>
          <option value="abandoned">已放弃</option>
        </select>
        <button class="btn btn-primary btn-sm" onclick="loadPlans()">筛选</button>
      </div>
      <div id="plansTable"></div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const API = '/api/v1';
let token = localStorage.getItem('admin_token') || '';
let currentAdmin = null;

// -- XSS Prevention --
function escapeHtml(str) {
  if (!str) return '-';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

// -- Auth --
async function doLogin() {
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  const errEl = document.getElementById('loginError');
  errEl.textContent = '';

  try {
    const res = await fetch(API + '/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email, password})
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || '登录失败');
    }
    const data = await res.json();
    token = data.access_token;
    localStorage.setItem('admin_token', token);
    await loadDashboard();
  } catch (e) {
    errEl.textContent = e.message;
  }
}

function doLogout() {
  token = '';
  localStorage.removeItem('admin_token');
  document.getElementById('loginScreen').style.display = 'flex';
  document.getElementById('dashboard').style.display = 'none';
}

// -- API Helper --
async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, {
    ...opts,
    headers: {
      'Authorization': 'Bearer ' + token,
      'Content-Type': 'application/json',
      ...(opts.headers || {})
    }
  });
  if (res.status === 403) { toast('无管理员权限'); doLogout(); throw new Error('Forbidden'); }
  if (res.status === 401) { toast('登录已过期'); doLogout(); throw new Error('Unauthorized'); }
  if (!res.ok) { const d = await res.json().catch(()=>({})); throw new Error(d.detail || 'Request failed'); }
  return res.json();
}

// -- Dashboard --
async function loadDashboard() {
  try {
    const stats = await apiFetch('/admin/stats');
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';

    const grid = document.getElementById('statsGrid');
    grid.innerHTML = [
      {label: '注册用户', value: stats.total_users},
      {label: '儿童档案', value: stats.total_children},
      {label: '训练计划', value: stats.total_plans},
      {label: '观察记录', value: stats.total_records},
      {label: '系统消息', value: stats.total_messages},
      {label: 'AI 会话', value: stats.total_ai_sessions}
    ].map(s => `<div class="stat-card"><div class="label">${s.label}</div><div class="value">${s.value}</div></div>`).join('');

    document.getElementById('adminName').textContent = '管理员';
    loadUsers();
  } catch (e) {
    // Not admin or token invalid
    document.getElementById('loginScreen').style.display = 'flex';
    document.getElementById('dashboard').style.display = 'none';
    if (e.message !== 'Forbidden' && e.message !== 'Unauthorized') {
      document.getElementById('loginError').textContent = '无法加载管理面板：' + e.message;
    }
  }
}

// -- Tabs --
function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.section').forEach(s => s.classList.toggle('active', s.id === 'section-' + name));
  if (name === 'users') loadUsers();
  if (name === 'children') loadChildren();
  if (name === 'plans') loadPlans();
}

// -- Users --
let usersPage = 0;
async function loadUsers(offset = 0) {
  usersPage = offset;
  const search = document.getElementById('userSearch').value;
  const params = new URLSearchParams({limit: 20, offset});
  if (search) params.set('search', search);

  const data = await apiFetch('/admin/users?' + params);
  const el = document.getElementById('usersTable');
  if (!data.users.length) { el.innerHTML = '<div class="empty">暂无数据</div>'; return; }

  el.innerHTML = `<table>
    <thead><tr><th>邮箱</th><th>昵称</th><th>角色</th><th>权限</th><th>儿童数</th><th>注册时间</th><th>操作</th></tr></thead>
    <tbody>${data.users.map(u => `<tr>
      <td>${escapeHtml(u.email)}</td>
      <td>${escapeHtml(u.display_name)}</td>
      <td>${escapeHtml(u.caregiver_role)}</td>
      <td><span class="badge-tag ${u.is_admin ? 'badge-admin' : 'badge-user'}">${u.is_admin ? '管理员' : '用户'}</span></td>
      <td>${parseInt(u.children_count) || 0}</td>
      <td>${formatDate(u.created_at)}</td>
      <td>
        ${!u.is_admin ? `<button class="btn btn-outline btn-sm" onclick="toggleAdmin('${escapeHtml(u.id)}',true)">设为管理员</button>` : `<button class="btn btn-outline btn-sm" onclick="toggleAdmin('${escapeHtml(u.id)}',false)">取消管理员</button>`}
      </td>
    </tr>`).join('')}</tbody>
  </table>
  ${paginationHtml(data.total, offset, 20, 'loadUsers')}`;
}
function searchUsers() { loadUsers(0); }

async function toggleAdmin(userId, isAdmin) {
  try {
    await apiFetch('/admin/users/' + userId, {
      method: 'PATCH',
      body: JSON.stringify({is_admin: isAdmin})
    });
    toast(isAdmin ? '已设为管理员' : '已取消管理员');
    loadUsers(usersPage);
  } catch (e) { toast(e.message); }
}

// -- Children --
let childrenPage = 0;
async function loadChildren(offset = 0) {
  childrenPage = offset;
  const search = document.getElementById('childSearch').value;
  const params = new URLSearchParams({limit: 20, offset});
  if (search) params.set('search', search);

  const data = await apiFetch('/admin/children?' + params);
  const el = document.getElementById('childrenTable');
  if (!data.children.length) { el.innerHTML = '<div class="empty">暂无数据</div>'; return; }

  el.innerHTML = `<table>
    <thead><tr><th>昵称</th><th>所属用户</th><th>出生年月</th><th>月龄</th><th>阶段</th><th>风险等级</th><th>创建时间</th></tr></thead>
    <tbody>${data.children.map(c => `<tr>
      <td>${escapeHtml(c.nickname)}</td>
      <td>${escapeHtml(c.user_email)}</td>
      <td>${escapeHtml(c.birth_year_month)}</td>
      <td>${parseInt(c.age_months) || 0}个月</td>
      <td>${escapeHtml(c.stage)}</td>
      <td><span class="badge-tag ${c.risk_level === 'normal' ? 'badge-active' : 'badge-admin'}">${escapeHtml(c.risk_level)}</span></td>
      <td>${formatDate(c.created_at)}</td>
    </tr>`).join('')}</tbody>
  </table>
  ${paginationHtml(data.total, offset, 20, 'loadChildren')}`;
}
function searchChildren() { loadChildren(0); }

// -- Plans --
let plansPage = 0;
async function loadPlans(offset = 0) {
  plansPage = offset;
  const status = document.getElementById('planStatus').value;
  const params = new URLSearchParams({limit: 20, offset});
  if (status) params.set('status', status);

  const data = await apiFetch('/admin/plans?' + params);
  const el = document.getElementById('plansTable');
  if (!data.plans.length) { el.innerHTML = '<div class="empty">暂无数据</div>'; return; }

  el.innerHTML = `<table>
    <thead><tr><th>标题</th><th>儿童</th><th>状态</th><th>主题</th><th>当前天</th><th>完成率</th><th>创建时间</th></tr></thead>
    <tbody>${data.plans.map(p => `<tr>
      <td>${escapeHtml(p.title)}</td>
      <td>${escapeHtml(p.child_nickname)}</td>
      <td><span class="badge-tag ${p.status === 'active' ? 'badge-active' : 'badge-completed'}">${escapeHtml(p.status)}</span></td>
      <td>${escapeHtml(p.focus_theme)}</td>
      <td>${parseInt(p.current_day) || 0}/7</td>
      <td>${(parseFloat(p.completion_rate) * 100 || 0).toFixed(0)}%</td>
      <td>${formatDate(p.created_at)}</td>
    </tr>`).join('')}</tbody>
  </table>
  ${paginationHtml(data.total, offset, 20, 'loadPlans')}`;
}

// -- Helpers --
function formatDate(s) {
  if (!s) return '-';
  const d = new Date(s);
  if (isNaN(d)) return s.substring(0, 10);
  return d.toLocaleDateString('zh-CN', {year:'numeric',month:'2-digit',day:'2-digit'});
}

function paginationHtml(total, offset, limit, fn) {
  if (total <= limit) return '';
  const pages = Math.ceil(total / limit);
  const current = Math.floor(offset / limit);
  let html = '<div class="pagination">';
  for (let i = 0; i < pages && i < 10; i++) {
    html += `<button class="btn btn-sm ${i === current ? 'btn-primary' : 'btn-outline'}" onclick="${fn}(${i * limit})">${i + 1}</button>`;
  }
  html += '</div>';
  return html;
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2500);
}

// -- Init --
if (token) { loadDashboard(); }
</script>
</body>
</html>"""


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel() -> HTMLResponse:
    """管理后台入口页面。"""
    return HTMLResponse(content=_ADMIN_HTML)

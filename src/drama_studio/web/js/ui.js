import { thumbUrl } from './api.js';

export function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

const STATUS_LABEL = {
  PASS_VERIFIED: '已验证',
  PASS_STATIC: '静态验证',
  PARTIAL: '部分',
  NOT_RUN: '未运行',
  BLOCKED: '受阻',
  FAILED: '失败',
  UNKNOWN: '未知',
  RUNNING: '运行中',
  PENDING: '等待',
  SUCCEEDED: '成功',
  CANCELLED: '已取消',
  completed: '已成片',
  producing: '生产中',
  ready: '待合成',
  draft: '草稿',
  verified: '已验证',
};

const STATUS_CLASS = {
  PASS_VERIFIED: 'b-verified',
  PASS_STATIC: 'b-pass_static',
  PARTIAL: 'b-partial',
  PASS_LIMITED: 'b-partial',
  NOT_RUN: 'b-not_run',
  BLOCKED: 'b-blocked',
  FAILED: 'b-failed',
  UNKNOWN: 'b-unknown',
  RUNNING: 'b-running',
  PENDING: 'b-pending',
  SUCCEEDED: 'b-succeeded',
  CANCELLED: 'b-cancelled',
  completed: 'b-completed',
  producing: 'b-producing',
  ready: 'b-ready',
  draft: 'b-draft',
};

export function statusLabel(status) {
  return STATUS_LABEL[status] || status || '未知';
}

export function statusBadge(status, extra = '') {
  const cls = STATUS_CLASS[status] || 'b-unknown';
  return `<span class="badge ${cls}">${esc(statusLabel(status))}${extra ? ` · ${esc(extra)}` : ''}</span>`;
}

export function rawStatusBadge(status) {
  const cls = STATUS_CLASS[status] || 'b-unknown';
  return `<span class="badge ${cls}">${esc(status)}</span>`;
}

export function progressBar(progress, { showCount = true } = {}) {
  const percent = Number(progress?.percent ?? 0);
  const ok = percent >= 100;
  return `<div class="progress" title="${esc(progress?.verified ?? 0)}/${esc(progress?.required ?? 0)} 必需步骤已验证">
    <div class="progress-track"><div class="progress-fill ${ok ? 'ok' : ''}" style="width:${percent}%"></div></div>
    <span class="progress-label">${percent}%${showCount ? ` · ${progress?.verified ?? 0}/${progress?.required ?? 0}` : ''}</span>
  </div>`;
}

export function fmtTime(iso, { withYear = false } = {}) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return esc(iso);
  const sameYear = date.getFullYear() === new Date().getFullYear();
  const opts = {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
    hour12: false,
    ...(withYear || !sameYear ? { year: 'numeric' } : {}),
  };
  return new Intl.DateTimeFormat('zh-CN', opts).format(date);
}

export function fmtBytes(bytes) {
  if (bytes == null) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = Number(bytes);
  let i = 0;
  while (value >= 1024 && i < units.length - 1) { value /= 1024; i++; }
  return `${value >= 100 || i === 0 ? Math.round(value) : value.toFixed(1)} ${units[i]}`;
}

export function fmtDuration(seconds) {
  if (seconds == null) return '—';
  const s = Number(seconds);
  if (!Number.isFinite(s)) return '—';
  if (s < 60) return `${s.toFixed(s < 10 ? 2 : 1)} s`;
  const m = Math.floor(s / 60);
  const rest = Math.round(s % 60);
  return `${m} min ${rest} s`;
}

export function fmtSeconds(seconds) {
  if (seconds == null) return '—';
  const s = Number(seconds);
  if (!Number.isFinite(s)) return '—';
  return `${s.toFixed(2)} s`;
}

export function loading(text = '读取真实数据…') {
  return `<div class="loading"><span class="spinner"></span><span>${esc(text)}</span></div>`;
}

export function emptyState(title, detail, action = '') {
  return `<div class="empty">
    <div class="empty-title">${esc(title)}</div>
    <div class="empty-detail">${esc(detail || '')}</div>
    ${action}
  </div>`;
}

export function errorBox(err) {
  const message = err?.message || String(err);
  const code = err?.code ? `[${err.code}] ` : '';
  return `<div class="error-box">${esc(code + message)}</div>`;
}

export function note(text) {
  return `<div class="note">${esc(text)}</div>`;
}

export function thumbTag(path, alt = '', cls = 'thumb') {
  if (!path) return '';
  return `<img class="${cls}" src="${thumbUrl(path)}" alt="${esc(alt)}" loading="lazy"
    onerror="this.style.visibility='hidden'">`;
}

export function icon(name) {
  const paths = {
    dashboard: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    projects: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    episodes: '<path d="M4 5h16M4 12h16M4 19h10"/>',
    workflow: '<circle cx="6" cy="6" r="2.2"/><circle cx="18" cy="6" r="2.2"/><circle cx="12" cy="18" r="2.2"/><path d="M8.2 6h7.6M7 8l4 7.8M17 8l-4 7.8"/>',
    assets: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.6"/><path d="m4 17 5-4 4 3 3-2 4 3"/>',
    styles: '<path d="M12 3a9 9 0 1 0 0 18h1.5a2 2 0 0 0 0-4H12a2 2 0 0 1 0-4h4a5 5 0 0 0 0-10z"/><circle cx="7.5" cy="9" r="1"/><circle cx="11" cy="6.5" r="1"/><circle cx="15" cy="7.5" r="1"/>',
    tasks: '<path d="m4 7 2 2 3-3M4 15l2 2 3-3"/><path d="M12 7h8M12 15h8"/>',
    settings: '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h9M17 18h3"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="15" cy="18" r="2"/>',
    play: '<path d="M7 4.5v15l12-7.5z"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>',
    film: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="m4 17 5-4 4 3 3-2 4 3"/>',
    audio: '<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
    file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    alert: '<path d="M12 3 2.5 20h19z"/><path d="M12 9v5M12 17h.01"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    external: '<path d="M14 4h6v6M20 4l-8 8"/><path d="M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5"/>',
    waveform: '<path d="M3 12h2l2-6 3 12 3-16 3 14 2-6h3"/>',
  };
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.file}</svg>`;
}

export function toast(message, type = 'info', timeout = 3800) {
  const root = document.getElementById('toast-root');
  if (!root) return;
  const node = document.createElement('div');
  node.className = `toast ${type}`;
  node.textContent = message;
  root.appendChild(node);
  setTimeout(() => node.remove(), Math.max(1200, timeout));
}

export function closeModal() {
  const root = document.getElementById('modal-root');
  if (root) root.innerHTML = '';
}

export function modal(title, bodyHtml, { wide = false, onMount, footer = '', guardClose = null } = {}) {
  closeModal();
  const root = document.getElementById('modal-root');
  root.innerHTML = `<div class="modal-backdrop">
    <div class="modal-card ${wide ? 'wide' : ''}" role="dialog" aria-modal="true">
      <div class="modal-head">
        <div class="modal-title">${esc(title)}</div>
        <button class="close-x" data-close aria-label="关闭">×</button>
      </div>
      <div class="modal-body">${bodyHtml}</div>
      ${footer ? `<div class="modal-foot">${footer}</div>` : ''}
    </div>
  </div>`;
  const backdrop = root.firstElementChild;
  const escHandler = (event) => {
    if (event.key === 'Escape') requestClose();
  };
  const requestClose = async () => {
    if (guardClose && !(await guardClose(root))) return;
    closeModal();
    document.removeEventListener('keydown', escHandler);
  };
  backdrop.addEventListener('click', (event) => {
    if (event.target === backdrop) requestClose();
  });
  root.querySelectorAll('[data-close]').forEach((el) => el.addEventListener('click', requestClose));
  document.addEventListener('keydown', escHandler);
  if (onMount) onMount(root);
  return { close: closeModal };
}

export function confirmDialog({ title, body, confirmLabel = '确认', danger = false, requireText = null }) {
  return new Promise((resolve) => {
    const extra = requireText
      ? `<div class="field mt12"><label>输入 <b>${esc(requireText)}</b> 以确认</label>
           <input class="input" id="confirm-input" autocomplete="off"></div>`
      : '';
    modal(title, `<div class="dim">${esc(body || '')}</div>${extra}`, {
      footer: `<button class="btn btn-ghost" data-act="cancel">取消</button>
               <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" data-act="ok">${esc(confirmLabel)}</button>`,
      onMount(root) {
        const input = root.querySelector('#confirm-input');
        const ok = root.querySelector('[data-act="ok"]');
        if (input) {
          input.focus();
          ok.disabled = true;
          input.addEventListener('input', () => { ok.disabled = input.value.trim() !== requireText; });
        }
        root.querySelector('[data-act="cancel"]').addEventListener('click', () => { closeModal(); resolve(false); });
        ok.addEventListener('click', () => {
          if (requireText && input.value.trim() !== requireText) return;
          closeModal();
          resolve(true);
        });
      },
    });
  });
}

export function openDrawer(title, bodyHtml, { onMount } = {}) {
  const root = document.getElementById('modal-root');
  root.innerHTML = `<div class="drawer-backdrop" data-close></div>
    <aside class="drawer" role="dialog" aria-modal="true">
      <div class="drawer-head"><div class="modal-title">${esc(title)}</div>
        <button class="close-x" data-close aria-label="关闭">×</button></div>
      <div class="drawer-body">${bodyHtml}</div>
    </aside>`;
  root.querySelectorAll('[data-close]').forEach((el) => el.addEventListener('click', closeModal));
  document.addEventListener('keydown', function handler(event) {
    if (event.key === 'Escape') { closeModal(); document.removeEventListener('keydown', handler); }
  });
  if (onMount) onMount(root);
}

export function kv(rows) {
  return `<dl class="kv">${rows.map(([k, v, mono]) => `<dt>${esc(k)}</dt><dd class="${mono ? 'mono' : ''}">${v ?? '—'}</dd>`).join('')}</dl>`;
}

export function pageHead(title, subtitle, actionsHtml = '') {
  return `<div class="page-head">
    <div><h1 class="page-title">${esc(title)}</h1>${subtitle ? `<div class="page-sub">${subtitle}</div>` : ''}</div>
    <div class="actions">${actionsHtml}</div>
  </div>`;
}

export function setHash(hash) {
  if (location.hash === hash) return;
  location.hash = hash;
}

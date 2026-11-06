import { get } from './api.js';
import { icon, esc, errorBox, loading } from './ui.js';

import dashboard from './pages/dashboard.js';
import projects from './pages/projects.js';
import episodes from './pages/episodes.js';
import episode from './pages/episode.js';
import workflow from './pages/workflow.js';
import assets from './pages/assets.js';
import styles from './pages/styles.js';
import tasks from './pages/tasks.js';
import settings from './pages/settings.js';

const NAV = [
  { group: '生产', id: 'dashboard', label: '工作台', icon: 'dashboard', hash: '#/dashboard' },
  { group: '生产', id: 'episodes', label: '期数管理', icon: 'episodes', hash: '#/episodes' },
  { group: '生产', id: 'workflow', label: '生产工作流', icon: 'workflow', hash: '#/workflow' },
  { group: '生产', id: 'tasks', label: '任务中心', icon: 'tasks', hash: '#/tasks' },
  { group: '内容', id: 'projects', label: '内容项目', icon: 'projects', hash: '#/projects' },
  { group: '内容', id: 'assets', label: '素材库', icon: 'assets', hash: '#/assets' },
  { group: '内容', id: 'styles', label: '风格管理', icon: 'styles', hash: '#/styles' },
  { group: '系统', id: 'settings', label: '系统设置', icon: 'settings', hash: '#/settings' },
];

const PAGES = {
  dashboard: { component: dashboard, title: '工作台' },
  projects: { component: projects, title: '内容项目' },
  episodes: { component: episodes, title: '期数管理' },
  episode: { component: episode, title: '期数工作区' },
  workflow: { component: workflow, title: '生产工作流' },
  assets: { component: assets, title: '素材库' },
  styles: { component: styles, title: '风格管理' },
  tasks: { component: tasks, title: '任务中心' },
  settings: { component: settings, title: '系统设置' },
};

const state = { current: 'dashboard', params: {}, title: '工作台' };

function renderNav(activeId) {
  const nav = document.getElementById('nav');
  let lastGroup = null;
  const items = [];
  for (const item of NAV) {
    if (item.group !== lastGroup) {
      items.push(`<div class="nav-group">${esc(item.group)}</div>`);
      lastGroup = item.group;
    }
    items.push(`<a class="nav-item ${item.id === activeId ? 'active' : ''}" href="${item.hash}">
      <span class="nav-icon">${icon(item.icon)}</span><span>${esc(item.label)}</span>
    </a>`);
  }
  nav.innerHTML = items.join('');
}

function parseRoute() {
  const raw = location.hash.replace(/^#\/?/, '') || 'dashboard';
  const [pathPart, queryPart] = raw.split('?');
  const segments = pathPart.split('/').filter(Boolean);
  const params = Object.fromEntries(new URLSearchParams(queryPart || ''));
  if (segments[0] === 'episodes' && segments[1]) {
    return { id: 'episode', params: { ...params, episodeId: decodeURIComponent(segments[1]) } };
  }
  const id = segments[0] || 'dashboard';
  return PAGES[id] ? { id, params } : { id: 'dashboard', params: {} };
}

async function route() {
  const { id, params } = parseRoute();
  state.current = id;
  state.params = params;
  state.title = PAGES[id].title;
  renderNav(id === 'episode' ? 'episodes' : id);
  const view = document.getElementById('view');
  view.innerHTML = loading();
  window.scrollTo({ top: 0, behavior: 'instant' });
  try {
    await PAGES[id].component.render(view, params, { refresh: route });
  } catch (err) {
    view.innerHTML = `<div class="page-head"><div><h1 class="page-title">${esc(state.title)}</h1></div></div>${errorBox(err)}`;
    console.error(err);
  }
  await updateCrumbs();
}

async function updateCrumbs() {
  const crumbs = document.getElementById('crumbs');
  const page = PAGES[state.current];
  let detail = '';
  if (state.current === 'episode' && state.params.episodeId) {
    try {
      const data = await get(`/api/episodes/${encodeURIComponent(state.params.episodeId)}`);
      detail = data.title || data.id;
    } catch {
      detail = state.params.episodeId;
    }
  }
  crumbs.innerHTML = detail
    ? `<span>${esc(page.title)}</span><span class="sep">/</span><span class="cur">${esc(detail)}</span>`
    : `<span class="cur">${esc(page.title)}</span>`;
}

function pill(service) {
  const map = {
    PASS_VERIFIED: 'dot-ok', PASS_LIMITED: 'dot-warn', FAIL: 'dot-bad',
    NOT_RUN: 'dot-unknown', UNKNOWN: 'dot-unknown',
  };
  const dot = map[service.status] || 'dot-unknown';
  const short = { comfyui: 'ComfyUI', llm: 'LLM', tts: 'VoxCPM2' }[service.id] || service.name;
  return `<span class="env-pill" title="${esc(service.detail || '')}">
    <span class="dot ${dot}"></span>${esc(short)}</span>`;
}

async function refreshEnv() {
  try {
    const env = await get('/api/env');
    const pills = document.getElementById('env-pills');
    const ffmpeg = (env.tools || []).find((t) => t.id === 'tool.ffmpeg');
    pills.innerHTML = [
      ...(env.services || []).map(pill),
      `<span class="env-pill" title="${esc(ffmpeg?.detail || '')}">
        <span class="dot ${ffmpeg?.status === 'PASS_VERIFIED' ? 'dot-ok' : 'dot-bad'}"></span>FFmpeg</span>`,
    ].join('');
    const mini = document.getElementById('env-mini');
    const verified = (env.services || []).filter((s) => s.status === 'PASS_VERIFIED').length;
    const total = (env.services || []).length;
    const dot = verified === total ? 'dot-ok' : verified > 0 ? 'dot-warn' : 'dot-unknown';
    mini.innerHTML = `<span class="dot ${dot}"></span><span>服务 ${verified}/${total} 在线</span>`;
  } catch {
    document.getElementById('env-pills').innerHTML = '<span class="env-pill"><span class="dot dot-bad"></span>环境探测失败</span>';
  }
}

function boot() {
  renderNav('dashboard');
  window.addEventListener('hashchange', route);
  document.getElementById('refresh-btn').addEventListener('click', () => route());
  route();
  refreshEnv();
  setInterval(refreshEnv, 20000);
}

boot();

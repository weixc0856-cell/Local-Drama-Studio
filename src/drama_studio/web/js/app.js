import { get } from './api.js';
import { icon, esc, errorBox, loading } from './ui.js';

import film_projects from './pages/film_projects.js';
import storyboard from './pages/storyboard.js';
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
  { group: '创作', id: 'film-projects', label: '项目中心', icon: 'film', hash: '#/' },
  { group: '创作', id: 'storyboard', label: '剧本与分镜', icon: 'episodes', hash: '#/storyboard' },
  { group: '创作', id: 'visual', label: '视觉资产', icon: 'image', hash: '#/visual', pending: 'F4' },
  { group: '创作', id: 'voice', label: '声音工作室', icon: 'audio', hash: '#/voice', pending: 'F4' },
  { group: '创作', id: 'edit', label: '剪辑工作台', icon: 'workflow', hash: '#/edit', pending: 'F3' },
  { group: '创作', id: 'ops', label: '生产与质量', icon: 'tasks', hash: '#/ops', pending: 'F5' },
  { group: '旧版', id: 'dashboard', label: '工作台', icon: 'dashboard', hash: '#/dashboard' },
  { group: '旧版', id: 'episodes', label: '期数管理', icon: 'episodes', hash: '#/episodes' },
  { group: '旧版', id: 'workflow', label: '生产工作流', icon: 'workflow', hash: '#/workflow' },
  { group: '旧版', id: 'tasks', label: '任务中心', icon: 'tasks', hash: '#/tasks' },
  { group: '旧版', id: 'projects', label: '内容项目', icon: 'projects', hash: '#/projects' },
  { group: '旧版', id: 'assets', label: '素材库', icon: 'assets', hash: '#/assets' },
  { group: '旧版', id: 'styles', label: '风格管理', icon: 'styles', hash: '#/styles' },
  { group: '旧版', id: 'settings', label: '系统设置', icon: 'settings', hash: '#/settings' },
];

const PAGES = {
  'film-projects': { component: film_projects, title: '项目中心' },
  storyboard: { component: storyboard, title: '剧本与分镜' },
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

const state = { current: 'film-projects', params: {}, title: '项目中心' };

function renderNav(activeId) {
  const nav = document.getElementById('nav');
  let lastGroup = null;
  const items = [];
  for (const item of NAV) {
    if (item.group !== lastGroup) {
      items.push(`<div class="nav-group">${esc(item.group)}</div>`);
      lastGroup = item.group;
    }
    if (item.pending) {
      items.push(`<span class="nav-item disabled" title="计划在 ${esc(item.pending)} 实现">
        <span class="nav-icon">${icon(item.icon)}</span><span>${esc(item.label)}</span>
        <span class="nav-tag">${esc(item.pending)}</span>
      </span>`);
      continue;
    }
    items.push(`<a class="nav-item ${item.id === activeId ? 'active' : ''}" href="${item.hash}">
      <span class="nav-icon">${icon(item.icon)}</span><span>${esc(item.label)}</span>
    </a>`);
  }
  nav.innerHTML = items.join('');
}

function parseRoute() {
  const raw = location.hash.replace(/^#\/?/, '') || 'film-projects';
  const [pathPart, queryPart] = raw.split('?');
  const segments = pathPart.split('/').filter(Boolean);
  const params = Object.fromEntries(new URLSearchParams(queryPart || ''));
  if (segments[0] === 'episodes' && segments[1]) {
    return { id: 'episode', params: { ...params, episodeId: decodeURIComponent(segments[1]) } };
  }
  const id = segments[0] || 'film-projects';
  return PAGES[id] ? { id, params } : { id: 'film-projects', params: {} };
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
  } else if (state.current === 'storyboard' && state.params.project) {
    detail = state.params.project;
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

async function refreshStatus() {
  const gpuEl = document.getElementById('status-gpu');
  const queueEl = document.getElementById('status-queue');
  if (!gpuEl || !queueEl) return;
  try {
    const data = await get('/api/tasks');
    const all = data.tasks || [];
    const running = all.filter((task) => task.status === 'RUNNING');
    const waiting = all.filter((task) => task.status === 'PENDING');
    gpuEl.textContent = running.length ? `GPU：${running[0].kind || '任务'} 运行中` : 'GPU：空闲';
    queueEl.textContent = `队列 ${waiting.length}`;
  } catch {
    gpuEl.textContent = 'GPU：未知';
    queueEl.textContent = '队列 —';
  }
}

function boot() {
  renderNav('film-projects');
  window.addEventListener('hashchange', route);
  document.getElementById('refresh-btn').addEventListener('click', () => route());
  route();
  refreshEnv();
  refreshStatus();
  setInterval(refreshEnv, 20000);
  setInterval(refreshStatus, 5000);
}

boot();

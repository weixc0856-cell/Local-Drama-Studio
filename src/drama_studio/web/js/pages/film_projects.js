import { get, thumbUrl } from '../api.js';
import { esc, pageHead, loading, errorBox, emptyState, fmtDuration, setHash } from '../ui.js';

const STAGES = [
  ['script', '剧本'],
  ['storyboard', '分镜'],
  ['keyframes', '关键帧'],
  ['video', '镜头'],
  ['voice', '配音'],
  ['edit', '剪辑'],
  ['final', '成片'],
];

function stageChips(stages) {
  return STAGES.map(([key, label]) => {
    const value = stages[key];
    const done = value === true || (typeof value === 'string' && value !== '0/0' && !value.startsWith('0/'));
    const detail = typeof value === 'string' ? value : '';
    return `<span class="film-stage ${done ? 'done' : ''}">${esc(label)}${detail ? ` ${esc(detail)}` : ''}</span>`;
  }).join('');
}

function coverStyle(project) {
  return project.cover ? `background-image:url('${thumbUrl(project.cover, 640)}')` : '';
}

function card(project) {
  const meta = [
    esc(project.aspect_ratio || '9:16'),
    project.target_duration_seconds ? fmtDuration(project.target_duration_seconds) : '时长未定',
    project.style_id ? esc(project.style_id) : '未绑定风格',
  ].join(' · ');
  return `<article class="film-card" data-project="${esc(project.project_id)}">
    <div class="film-cover" style="${coverStyle(project)}">${project.cover ? '' : '暂无关键帧'}</div>
    <div class="film-body">
      <div class="film-title">${esc(project.title || project.project_id)}</div>
      <div class="film-meta">${meta}</div>
      <div class="film-stages">${stageChips(project.stages || {})}</div>
    </div>
  </article>`;
}

export default {
  title: '项目中心',
  async render(view, params, ctx) {
    view.innerHTML = loading('扫描 projects/ 下的作品…');
    let data;
    try {
      data = await get('/api/film/projects');
    } catch (err) {
      view.innerHTML = errorBox(err);
      return;
    }
    const projects = data.projects || [];
    const head = pageHead(
      '项目中心',
      '作品、进度与真实生产状态；数据来自 projects/&lt;id&gt;/ 下的文件',
      '<button class="btn" id="refresh-projects">刷新</button>',
    );
    if (!projects.length) {
      view.innerHTML = head + emptyState('暂无作品', 'projects/ 下还没有 project.json。可以先用 drama film 命令创建项目数据。');
    } else {
      view.innerHTML = head + `<div class="film-grid">${projects.map(card).join('')}</div>`;
      view.querySelectorAll('[data-project]').forEach((el) => {
        el.addEventListener('click', () => setHash(`#/storyboard?project=${encodeURIComponent(el.dataset.project)}`));
      });
    }
    view.querySelector('#refresh-projects')?.addEventListener('click', ctx.refresh);
  },
};

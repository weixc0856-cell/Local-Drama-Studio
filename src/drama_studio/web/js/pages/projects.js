import { get } from '../api.js';
import {
  esc, fmtTime, loading, errorBox, emptyState, pageHead, statusBadge, progressBar,
} from '../ui.js';
import { openProjectModal, openEpisodeModal } from '../forms.js';

function projectCard(project) {
  return `<div class="panel" style="display:flex;flex-direction:column">
    <div class="panel-body" style="display:flex;flex-direction:column;gap:8px;flex:1">
      <div class="row" style="justify-content:space-between;align-items:flex-start">
        <div>
          <div class="card-title" style="font-size:14px">${esc(project.name)}</div>
          <div class="tiny muted mt8">${esc(project.positioning || '未填写内容定位')}</div>
        </div>
        ${project.origin === 'imported' ? '<span class="tag">导入</span>' : ''}
      </div>
      <div class="dim small">${esc(project.description || '暂无简介')}</div>
      <div class="row wrap" style="gap:6px">
        <span class="tag">${esc(project.aspect_ratio || '9:16')}</span>
        <span class="tag">${esc(project.style?.name || '未绑定默认风格')}</span>
        <span class="tag">声音 ${esc(project.default_voice || '未设置')}</span>
        ${(project.target_platforms || []).map((p) => `<span class="tag">${esc(p)}</span>`).join('')}
      </div>
      <div class="card-meta">
        <span>${project.episodes_total || 0} 期</span><span>·</span>
        <span>已成片 ${project.episodes_completed || 0}</span><span>·</span>
        <span>更新 ${esc(fmtTime(project.updated_at))}</span>
      </div>
      <div class="row mt8" style="gap:8px">
        <a class="btn btn-sm" href="#/episodes?project=${encodeURIComponent(project.id)}">查看期数</a>
        <button class="btn btn-sm btn-ghost" data-new-episode="${esc(project.id)}">新建期数</button>
        <button class="btn btn-sm btn-ghost" data-edit-project="${esc(project.id)}">编辑</button>
      </div>
    </div>
  </div>`;
}

export default {
  async render(view) {
    let data;
    try {
      data = await get('/api/projects');
    } catch (err) {
      view.innerHTML = errorBox(err);
      return;
    }
    const projects = data.projects || [];
    view.innerHTML = `
      ${pageHead('内容项目', '一个项目是一个内容系列。项目与期数记录保存在 projects/workspace.db；产物状态仍从真实目录派生。',
        '<button class="btn btn-primary" id="new-project">新建项目</button>')}
      ${projects.length ? `<div class="grid grid-2">${projects.map(projectCard).join('')}</div>`
        : emptyState('还没有内容项目', '创建第一个系列，例如「东方意境」或「古典人物」。')}
    `;

    view.querySelector('#new-project')?.addEventListener('click', () => {
      openProjectModal({ onDone: () => this.render(view) });
    });
    view.querySelectorAll('[data-edit-project]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const project = projects.find((p) => p.id === btn.dataset.editProject);
        openProjectModal({ project, onDone: () => this.render(view) });
      });
    });
    view.querySelectorAll('[data-new-episode]').forEach((btn) => {
      btn.addEventListener('click', () => {
        openEpisodeModal({
          projects,
          projectId: btn.dataset.newEpisode,
          onDone: (episode) => {
            location.hash = `#/episodes/${encodeURIComponent(episode.id)}`;
          },
        });
      });
    });
  },
};

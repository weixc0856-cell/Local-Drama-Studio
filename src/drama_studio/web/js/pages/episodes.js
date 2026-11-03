import { get } from '../api.js';
import {
  esc, fmtTime, fmtSeconds, errorBox, emptyState, pageHead, statusBadge, progressBar,
} from '../ui.js';
import { openEpisodeModal } from '../forms.js';

const FILTERS = [
  ['', '全部'], ['draft', '草稿'], ['ready', '待合成'],
  ['producing', '生产中'], ['failed', '失败'], ['completed', '已成片'],
];

export default {
  async render(view, params, ctx) {
    let projects;
    let episodes;
    try {
      [projects, episodes] = await Promise.all([
        get('/api/projects'),
        get(`/api/episodes${params.project ? `?project_id=${encodeURIComponent(params.project)}` : ''}`),
      ]);
    } catch (err) {
      view.innerHTML = errorBox(err);
      return;
    }
    const all = episodes.episodes || [];
    const status = params.status || '';
    const filtered = status ? all.filter((e) => e.status === status) : all;
    const projectId = params.project || '';

    const rows = filtered.map((ep) => `<tr class="clickable" data-episode="${esc(ep.id)}">
      <td class="mono-cell">EP${String(ep.number).padStart(2, '0')}</td>
      <td>
        <div class="title-cell">${esc(ep.title)}</div>
        <div class="tiny muted">${esc(ep.project?.name || '')}</div>
      </td>
      <td><span class="tag">${esc(ep.track)}</span></td>
      <td class="muted small">${esc(ep.style || '—')}</td>
      <td>${statusBadge(ep.status)}</td>
      <td>${progressBar(ep.progress)}</td>
      <td class="small">${ep.final
        ? `<span class="badge b-verified">${esc(fmtSeconds(ep.final.probe?.duration))}</span>`
        : '<span class="muted">—</span>'}</td>
      <td class="muted small nowrap">${fmtTime(ep.updated_at)}</td>
    </tr>`).join('');

    view.innerHTML = `
      ${pageHead('期数管理', '完成度按“必需步骤中已验证的数量”计算；部分完成不计为完成。',
        `<button class="btn btn-primary" id="new-episode" ${projects.projects.length ? '' : 'disabled'}>新建期数</button>`)}
      <div class="panel mb16">
        <div class="panel-body row wrap" style="justify-content:space-between">
          <div class="chips">
            ${FILTERS.map(([value, label]) => {
              const q = new URLSearchParams();
              if (projectId) q.set('project', projectId);
              if (value) q.set('status', value);
              const href = `#/episodes${q.toString() ? `?${q}` : ''}`;
              return `<a class="chip ${status === value ? 'active' : ''}" href="${href}">${label}</a>`;
            }).join('')}
          </div>
          <div class="row">
            <span class="muted small">项目</span>
            <select class="input" id="project-filter" style="width:220px">
              <option value="">全部项目</option>
              ${projects.projects.map((p) => `<option value="${esc(p.id)}" ${p.id === projectId ? 'selected' : ''}>${esc(p.name)}</option>`).join('')}
            </select>
          </div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-body tight">
          ${filtered.length ? `<div class="table-wrap"><table class="table">
            <thead><tr><th>编号</th><th>标题 / 项目</th><th>类型</th><th>风格</th><th>状态</th>
              <th>完成度</th><th>成片</th><th>更新</th></tr></thead>
            <tbody>${rows}</tbody></table></div>`
            : emptyState('没有符合条件的期数', '调整筛选，或新建一期。')}
        </div>
      </div>`;

    view.querySelectorAll('[data-episode]').forEach((row) => {
      row.addEventListener('click', () => { location.hash = `#/episodes/${encodeURIComponent(row.dataset.episode)}`; });
    });
    view.querySelector('#project-filter')?.addEventListener('change', (event) => {
      const q = new URLSearchParams();
      if (event.target.value) q.set('project', event.target.value);
      if (status) q.set('status', status);
      location.hash = `#/episodes${q.toString() ? `?${q}` : ''}`;
    });
    view.querySelector('#new-episode')?.addEventListener('click', () => {
      openEpisodeModal({
        projects: projects.projects,
        projectId: projectId || undefined,
        onDone: (episode) => { location.hash = `#/episodes/${encodeURIComponent(episode.id)}`; },
      });
    });
  },
};

import { get, thumbUrl } from '../api.js';
import {
  esc, statusBadge, progressBar, fmtTime, fmtBytes, loading, errorBox, emptyState,
  pageHead, rawStatusBadge, icon,
} from '../ui.js';

function stat(value, label, foot = '', cls = '') {
  return `<div class="stat ${cls}"><div class="stat-value">${esc(value)}</div>
    <div class="stat-label">${esc(label)}</div>${foot ? `<div class="stat-foot">${foot}</div>` : ''}</div>`;
}

function pipelineClass(status) {
  if (status === 'PASS_VERIFIED') return 'ok';
  if (status === 'PARTIAL') return 'warn';
  if (status === 'FAILED') return 'bad';
  if (status === 'BLOCKED') return 'blocked';
  return '';
}

function episodeCard(ep) {
  const thumb = ep.thumb
    ? `<div class="card-thumb vertical" style="background-image:url('${thumbUrl(ep.thumb, 640)}')"></div>`
    : `<div class="card-thumb vertical"><div class="thumb-empty">${esc(ep.track === 'literary' ? '文学准备中' : '暂无缩略图')}</div></div>`;
  return `<a class="card" href="#/episodes/${encodeURIComponent(ep.id)}">
    ${thumb}
    <div class="card-body">
      <div class="row" style="justify-content:space-between">
        <span class="card-title">${esc(ep.title)}</span>
        ${statusBadge(ep.status)}
      </div>
      <div class="card-meta">
        <span>${esc(ep.project?.name || '')}</span><span>·</span>
        <span>${esc(ep.style || '未绑定风格')}</span><span>·</span>
        <span>${fmtTime(ep.updated_at)}</span>
      </div>
      ${progressBar(ep.progress)}
    </div>
  </a>`;
}

function taskRow(task) {
  return `<tr class="clickable" data-task="${esc(task.id)}">
    <td class="mono-cell">${esc(task.kind)}</td>
    <td>${statusBadge(task.status)}</td>
    <td class="muted small">${fmtTime(task.created_at)}</td>
    <td class="muted small">${task.started_at && task.finished_at
      ? esc(`${Math.max(0, Math.round((new Date(task.finished_at) - new Date(task.started_at)) / 1000))} s`)
      : '—'}</td>
    <td class="mono-cell" style="max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
      ${esc(task.error || (task.result && task.result.final) || '')}</td>
  </tr>`;
}

function envPanel(env) {
  const services = (env.services || []).map((s) => `
    <div class="row" style="justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(36,42,51,.6)">
      <div class="row"><span class="dot ${s.status === 'PASS_VERIFIED' ? 'dot-ok' : s.status === 'NOT_RUN' ? 'dot-unknown' : 'dot-warn'}"></span>
        <span>${esc(s.name)}</span></div>
      <div class="row"><span class="tiny muted mono">${esc(s.url || '')}</span>${rawStatusBadge(s.status)}</div>
    </div>
    <div class="tiny muted" style="padding:2px 0 4px">${esc(s.detail || '')}</div>`).join('');
  const gpu = env.gpu || {};
  const gpuText = gpu.name
    ? `${esc(gpu.name)} · ${esc(gpu.vram_free_gib ?? '?')} / ${esc(gpu.vram_total_gib ?? '?')} GiB 可用`
    : esc(gpu.detail || '无法读取');
  const disks = (env.disk || []).map((d) => `
    <div class="row" style="justify-content:space-between">
      <span class="muted">${esc(d.name)}</span>
      <span class="mono tiny ${d.status === 'PASS_VERIFIED' ? '' : 'muted'}">${esc(d.free_gib)} GiB 可用</span>
    </div>`).join('');
  return `<div class="panel">
    <div class="panel-head"><span class="panel-title">资源与环境</span>
      <span class="panel-sub">探测于 ${esc(fmtTime(env.checked_at))}</span></div>
    <div class="panel-body">
      ${services}
      <div class="mt12 row" style="justify-content:space-between">
        <span class="muted">GPU / XPU</span>
        <span class="small ${gpu.name ? '' : 'muted'}">${gpuText}</span>
      </div>
      <div class="tiny muted mt8">${esc(gpu.source ? `来源：${gpu.source}` : 'ComfyUI 未运行，无法读取 XPU 显存；不以配置推测')}</div>
      <div class="mt12 col" style="gap:4px">${disks}</div>
    </div>
  </div>`;
}

export default {
  async render(view) {
    let data;
    try {
      data = await get('/api/overview');
    } catch (err) {
      view.innerHTML = errorBox(err);
      return;
    }
    const { stats, recent_episodes: recent, recent_tasks: tasks, env } = data;

    let pipelineHtml = emptyState('没有可展示的期数', '先在「内容项目」中创建项目与期数。');
    if (recent.length) {
      try {
        const wf = await get(`/api/episodes/${encodeURIComponent(recent[0].id)}/workflow`);
        pipelineHtml = `<div class="pipeline">${wf.nodes.map((n) => `
          <div class="pipe-node ${pipelineClass(n.status)}">
            <div class="row" style="justify-content:space-between">
              <span class="pipe-name">${esc(n.label)}</span>
              <span class="dot ${n.status === 'PASS_VERIFIED' ? 'dot-ok' : n.status === 'PARTIAL' ? 'dot-warn' : n.status === 'FAILED' ? 'dot-bad' : 'dot-unknown'}"></span>
            </div>
            <div class="pipe-detail">${esc(n.detail || '')}</div>
          </div>`).join('')}</div>
        <div class="tiny muted mt8">流程节点来自「${esc(recent[0].title)}」的真实文件状态；未运行的节点不会显示为完成。</div>`;
      } catch (err) {
        pipelineHtml = errorBox(err);
      }
    }

    view.innerHTML = `
      ${pageHead('工作台', '所有数字来自真实目录、构建 manifest 与任务记录。没有执行过的步骤显示为未运行。')}
      <div class="stat-grid">
        ${stat(stats.projects, '内容项目')}
        ${stat(stats.episodes, '期数')}
        ${stat(stats.completed, '已成片（技术）', '内容验收另计', 'is-accent')}
        ${stat(stats.producing, '生产中')}
        ${stat(stats.failed_tasks, '失败任务', '', stats.failed_tasks ? 'is-bad' : '')}
        ${stat(stats.pending_tasks, '待处理任务')}
        ${stat(stats.videos, '视频素材 / 成片')}
        ${stat(stats.renders, '构建记录')}
      </div>

      <div class="split">
        <div class="col">
          <div class="panel">
            <div class="panel-head"><span class="panel-title">最近制作</span>
              <a href="#/episodes" class="small">全部期数</a></div>
            <div class="panel-body">
              ${recent.length ? `<div class="cards">${recent.map(episodeCard).join('')}</div>`
                : emptyState('还没有期数', '创建一个项目，再添加第一期。')}
            </div>
          </div>

          <div class="panel">
            <div class="panel-head"><span class="panel-title">全局生产流程</span>
              <span class="panel-sub">选题 → 原文 → 分析 → 文案 → 分镜 → 图片 → 视频 → 配音 → 字幕 → 合成 → 成片</span></div>
            <div class="panel-body">${pipelineHtml}</div>
          </div>

          <div class="panel">
            <div class="panel-head"><span class="panel-title">最近任务</span>
              <a href="#/tasks" class="small">任务中心</a></div>
            <div class="panel-body tight">
              ${tasks.length ? `<div class="table-wrap"><table class="table">
                <thead><tr><th>类型</th><th>状态</th><th>创建</th><th>耗时</th><th>结果 / 错误</th></tr></thead>
                <tbody>${tasks.map(taskRow).join('')}</tbody></table></div>`
                : emptyState('还没有任务记录', '在工作流或任务中心执行一个已注册的任务。')}
            </div>
          </div>
        </div>
        <div class="col">
          ${envPanel(env)}
          <div class="panel">
            <div class="panel-head"><span class="panel-title">本期状态说明</span></div>
            <div class="panel-body col" style="gap:8px">
              <div class="note">「已成片」只表示最终视频存在且哈希与 manifest 一致，不代表内容验收通过。</div>
              <div class="note">人工验收没有任何记录时，期数页会显示 NOT_RUN。</div>
              <div class="note">环境探测失败显示 UNKNOWN，不假设服务在线。</div>
            </div>
          </div>
        </div>
      </div>`;

    view.querySelectorAll('[data-task]').forEach((row) => {
      row.addEventListener('click', () => { location.hash = `#/tasks?id=${encodeURIComponent(row.dataset.task)}`; });
    });
  },
};

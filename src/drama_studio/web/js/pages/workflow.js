import { get } from '../api.js';
import {
  esc, statusBadge, loading, errorBox, emptyState, pageHead, fmtTime, confirmDialog, toast,
} from '../ui.js';
import { runTask } from '../forms.js';

const STAGES = [
  { label: '文本', ids: ['source', 'package'] },
  { label: '分析', ids: ['analysis'] },
  { label: '策划', ids: ['script', 'storyboard'] },
  { label: '质检 / 美学', ids: ['static', 'aesthetic'] },
  { label: '生成', ids: ['images', 'videos', 'motion'] },
  { label: '声音', ids: ['voice', 'subtitles'] },
  { label: '合成', ids: ['compose'] },
  { label: '输出', ids: ['output'] },
];

function nodeClass(status) {
  if (status === 'PASS_VERIFIED') return 'ok';
  if (status === 'PARTIAL') return 'warn';
  if (status === 'FAILED') return 'bad';
  if (status === 'BLOCKED') return 'blocked';
  return '';
}

function ioList(items, emptyText) {
  if (!items || !items.length) return `<ul><li class="muted">${esc(emptyText)}</li></ul>`;
  return `<ul>${items.slice(0, 8).map((item) => `<li class="${item.exists ? '' : 'missing'}"
    title="${esc(item.path)}"><span class="io-flag">${item.exists ? '✓' : '✕'}</span> ${esc(item.path)}</li>`).join('')}</ul>`;
}

function nodeCard(node) {
  const task = node.last_task;
  let action = '';
  if (node.task_kind === 'build.rebuild') {
    action = `<button class="btn btn-primary btn-sm" data-build="${esc(node.id)}">执行合成</button>`;
  } else if (node.task_kind === 'comfy.batch') {
    action = `<input class="input" data-jobs="${esc(node.id)}" placeholder="experiments/r3a/jobs_flux.json"
        style="width:300px;font-family:var(--mono);font-size:11px">
      <button class="btn btn-sm" data-batch="${esc(node.id)}">执行批处理</button>`;
  } else if (node.task_kind) {
    action = `<button class="btn btn-sm" disabled>${esc(node.task_kind)}</button>`;
  }
  return `<div class="wf-node ${nodeClass(node.status)}">
    <div class="wf-head">
      <span class="wf-title">${esc(node.label)}</span>
      ${statusBadge(node.status)}
      ${node.required ? '' : '<span class="tag">可选</span>'}
      ${task ? `<a class="tag" href="#/tasks?id=${encodeURIComponent(task.id)}">最近任务 ${esc(task.status)} · ${esc(fmtTime(task.created_at))}</a>` : ''}
    </div>
    <div class="wf-detail">${esc(node.detail || '')}</div>
    <div class="wf-io">
      <div><div class="wf-io-title">输入</div>${ioList(node.inputs, '无文件输入')}</div>
      <div><div class="wf-io-title">输出</div>${ioList(node.outputs, '无已登记输出')}</div>
    </div>
    ${action || node.task_reason ? `<div class="wf-actions">
      ${action}
      ${node.task_blocked_reason ? `<span class="tiny muted">${esc(node.task_blocked_reason)}</span>` : ''}
      ${!action && node.task_reason ? `<span class="tiny muted">入口：${esc(node.task_reason)}</span>` : ''}
    </div>` : ''}
  </div>`;
}

export default {
  async render(view, params, ctx) {
    let episodes;
    try { episodes = (await get('/api/episodes')).episodes || []; }
    catch (err) { view.innerHTML = errorBox(err); return; }
    if (!episodes.length) {
      view.innerHTML = pageHead('生产工作流', '') + emptyState('还没有期数', '先创建项目和期数。');
      return;
    }
    const selected = params.episode && episodes.some((e) => e.id === params.episode)
      ? params.episode : episodes[0].id;
    let data;
    try { data = await get(`/api/workflow?episode_id=${encodeURIComponent(selected)}`); }
    catch (err) { view.innerHTML = errorBox(err); return; }
    const episode = episodes.find((e) => e.id === selected);
    const byId = Object.fromEntries((data.nodes || []).map((n) => [n.id, n]));

    view.innerHTML = `
      ${pageHead('生产工作流', '依赖关系来自真实构建步骤；节点只有在文件证据成立时才显示“已验证”。执行入口只包含已注册任务。',
        `<select class="input" id="episode-select" style="width:280px">
          ${episodes.map((e) => `<option value="${esc(e.id)}" ${e.id === selected ? 'selected' : ''}>
            EP${String(e.number).padStart(2, '0')} · ${esc(e.title)}</option>`).join('')}
        </select>`)}
      <div class="panel mb16">
        <div class="panel-body row wrap" style="justify-content:space-between">
          <div class="row wrap">
            ${statusBadge(data.status)}
            <span class="dim">${esc(episode.title)}</span>
            <span class="tag">${esc(episode.project?.name || '')}</span>
            <span class="tag">${esc(episode.track)}</span>
          </div>
          <div class="row">
            <a class="btn btn-sm btn-ghost" href="#/episodes/${encodeURIComponent(selected)}">打开期数工作区</a>
            <a class="btn btn-sm btn-ghost" href="#/tasks?episode=${encodeURIComponent(selected)}">本期任务</a>
          </div>
        </div>
      </div>
      <div class="wf">
        ${STAGES.map((stage) => `
          <div class="wf-stage">
            <div class="wf-stage-label">${esc(stage.label)}</div>
            <div class="wf-nodes">${stage.ids.map((id) => byId[id]).filter(Boolean).map(nodeCard).join('')}</div>
          </div>`).join('')}
      </div>
      <div class="panel mt16">
        <div class="panel-head"><span class="panel-title">依赖边</span>
          <span class="panel-sub">真实代码顺序，不是装饰图</span></div>
        <div class="panel-body row wrap" style="gap:6px">
          ${(data.edges || []).map((e) => `<span class="tag mono">${esc(e.from)} → ${esc(e.to)}</span>`).join('')}
        </div>
      </div>`;

    view.querySelector('#episode-select').addEventListener('change', (event) => {
      location.hash = `#/workflow?episode=${encodeURIComponent(event.target.value)}`;
    });

    view.querySelectorAll('[data-build]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const ok = await confirmDialog({
          title: '执行合成重建',
          body: '调用 scripts/r3_build.py，写入新的时间戳目录；不覆盖历史成片。约 2 分钟。',
          confirmLabel: '开始',
        });
        if (!ok) return;
        const task = await runTask('build.rebuild', { episode_id: selected });
        if (task?.id) location.hash = `#/tasks?id=${encodeURIComponent(task.id)}`;
      });
    });

    view.querySelectorAll('[data-batch]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const input = view.querySelector(`[data-jobs="${btn.dataset.batch}"]`);
        const jobs = input.value.trim();
        if (!jobs) { toast('请填写 experiments/ 下的 jobs JSON 路径', 'warn'); return; }
        const ok = await confirmDialog({
          title: '执行 ComfyUI 批处理',
          body: `将调用 scripts/r1_batch.py --jobs ${jobs}。需要 ComfyUI 已在 8188 运行；`
            + '同一时间只允许一个 GPU 任务，Wan 单段可能约 36 分钟。',
          confirmLabel: '开始批处理',
          danger: true,
        });
        if (!ok) return;
        const task = await runTask('comfy.batch', { jobs, confirm: true });
        if (task?.id) location.hash = `#/tasks?id=${encodeURIComponent(task.id)}`;
      });
    });
  },
};

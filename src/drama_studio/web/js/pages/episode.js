import { get, patch, mediaUrl, thumbUrl } from '../api.js';
import {
  esc, statusBadge, rawStatusBadge, progressBar, fmtTime, fmtBytes, fmtSeconds, fmtDuration,
  loading, errorBox, emptyState, pageHead, note, confirmDialog, toast,
  statusLabel,
} from '../ui.js';
import { runTask } from '../forms.js';
import { openPreview } from '../preview.js';

const TABS = [
  ['overview', '概览'],
  ['content', '内容'],
  ['storyboard', '分镜'],
  ['visual', '视觉'],
  ['audio', '音频'],
  ['assets', '素材'],
  ['output', '成片'],
];

const CLAIM_TYPE_LABEL = {
  original_text: '原文', historical_fact: '史实', interpretation: '解释', creative: '创作',
};
const REVIEW_LABEL = { unreviewed: '未审核', approved: '已批准', rejected: '已拒绝' };

function section(title, body, sub = '') {
  return `<div class="panel mb16">
    <div class="panel-head"><span class="panel-title">${esc(title)}</span>
      ${sub ? `<span class="panel-sub">${sub}</span>` : ''}</div>
    <div class="panel-body">${body}</div>
  </div>`;
}

function stepRow(step, index) {
  return `<div class="step">
    <div class="step-idx">${String(index).padStart(2, '0')}</div>
    <div><div class="step-label">${esc(step.label)}${step.required ? '' : ' <span class="tiny muted">可选</span>'}</div></div>
    <div class="badge-cell">${statusBadge(step.status)}</div>
    <div>
      <div class="step-detail">${esc(step.detail || '')}</div>
      ${(step.evidence || []).length ? `<div class="step-evidence">${step.evidence
        .slice(0, 4).map((path) => `<span title="${esc(path)}">${esc(path)}</span>`).join('')}</div>` : ''}
    </div>
  </div>`;
}

function taskTable(tasks) {
  if (!tasks.length) return emptyState('暂无任务', '在工作流或任务中心执行一个已注册的任务。');
  return `<div class="col" style="gap:0">${tasks.slice(0, 6).map((t) => `
    <a href="#/tasks?id=${encodeURIComponent(t.id)}" class="row"
       style="justify-content:space-between;gap:8px;padding:7px 0;border-bottom:1px solid rgba(36,42,51,.6);text-decoration:none;color:inherit">
      <span class="mono tiny" title="${esc(t.error || '')}">${esc(t.kind)}</span>
      <span class="row" style="gap:8px">${statusBadge(t.status)}
        <span class="tiny muted nowrap">${fmtTime(t.created_at)}</span></span>
    </a>`).join('')}</div>
    <div class="mt8"><a class="small" href="#/tasks?episode=${encodeURIComponent(tasks[0].episode_id || '')}">查看全部任务 →</a></div>`;
}

function buildTable(builds) {
  if (!builds.length) return emptyState('没有构建记录', '该期还没有 build_manifest.json。');
  return `<div class="table-wrap"><table class="table">
    <thead><tr><th>构建目录</th><th>时间</th><th>manifest</th><th>成片哈希</th><th>质量</th><th>字体</th></tr></thead>
    <tbody>${builds.map((b) => `<tr>
      <td class="mono-cell">${esc(b.dir)}</td>
      <td class="muted small">${fmtTime(b.created_at)}</td>
      <td>${b.manifest_version === 'current' ? '<span class="badge b-verified">current</span>'
        : '<span class="badge b-unknown">legacy</span>'}</td>
      <td>${b.final?.sha_ok ? '<span class="badge b-verified">一致</span>'
        : `<span class="badge b-failed">${b.final?.exists ? '不一致' : '缺失'}</span>`}</td>
      <td>${b.quality ? `<span class="badge ${b.quality === 'PASS' ? 'b-verified' : 'b-failed'}">${esc(b.quality)}</span>` : '<span class="badge b-unknown">NOT_RUN</span>'}</td>
      <td class="mono-cell" title="${esc(b.font?.postscript_name || '')}">${esc(b.font?.postscript_name || '—')}</td>
    </tr>`).join('')}</tbody></table></div>`;
}

async function renderOverview(host, detail, ctx) {
  host.innerHTML = `
    <div class="split">
      <div>
        ${section('生产步骤', `<div class="steps">${detail.steps.map((s, i) => stepRow(s, i + 1)).join('')}</div>`,
          '只统计真实文件证据')}
        ${section('构建记录', buildTable(detail.builds || []))}
      </div>
      <div>
        ${section('人工验收', `
          <div class="row" style="justify-content:space-between">
            <span class="dim">内容验收状态</span>${statusBadge(detail.review?.status)}
          </div>
          <div class="note mt12">${esc(detail.review?.detail || '')}</div>
          <div class="field mt12"><label>验收备注（可选）</label>
            <textarea class="textarea" id="review-note" style="min-height:56px"
              placeholder="记录看片结论、需要返工的点"></textarea></div>
          <div class="row mt8" style="gap:8px">
            <button class="btn btn-primary" id="review-accept">标记通过</button>
            <button class="btn btn-danger" id="review-reject">标记拒绝</button>
          </div>`,
          '与“技术成片”分开')}
        ${section('本期任务', taskTable(detail.tasks || []), '最近 50 条')}
        ${section('绑定信息', `<dl class="kv">
          <dt>产物目录</dt><dd class="mono">${esc(detail.artifact_root || '未绑定')}</dd>
          <dt>目录存在</dt><dd>${detail.artifact_root_exists ? '是' : '否'}</dd>
          <dt>类型</dt><dd>${esc(detail.track)}</dd>
          <dt>风格</dt><dd>${esc(detail.style?.name || '未绑定')}</dd>
          <dt>更新</dt><dd>${esc(fmtTime(detail.updated_at, { withYear: true }))}</dd>
        </dl>`) }
      </div>
    </div>`;
  host.querySelectorAll('[data-task]').forEach((row) => {
    row.addEventListener('click', () => { location.hash = `#/tasks?id=${encodeURIComponent(row.dataset.task)}`; });
  });
  const submitReview = async (decision) => {
    const note = host.querySelector('#review-note')?.value || '';
    const task = await runTask(`review.${decision}`, { episode_id: detail.id, note });
    if (task?.id) location.hash = `#/tasks?id=${encodeURIComponent(task.id)}`;
    else if (ctx?.refresh) ctx.refresh();
  };
  host.querySelector('#review-accept')?.addEventListener('click', () => submitReview('accept'));
  host.querySelector('#review-reject')?.addEventListener('click', () => submitReview('reject'));
}

async function renderContent(host, detail) {
  let data;
  try {
    data = await get(`/api/episodes/${encodeURIComponent(detail.id)}/content`);
  } catch (err) { host.innerHTML = errorBox(err); return; }
  const content = data.content;
  if (!content) {
    host.innerHTML = emptyState('没有可展示的内容', '该期未绑定产物目录，或目录中没有文本。');
    return;
  }
  if (content.kind === 'video') {
    const lines = content.source?.lines || [];
    host.innerHTML = `
      ${section('原文 / 旁白', lines.length
        ? `<ol style="margin:0;padding-left:20px;line-height:2">${lines.map((l) => `<li>${esc(l)}</li>`).join('')}</ol>`
        : emptyState('没有旁白文本', '未找到 narration.json 的 lines。'),
        esc(content.source?.path || ''))}
      ${section('文案', `<div class="row" style="justify-content:space-between">
          <span>${esc(content.script?.status || '')}</span>${statusBadge(content.script?.status)}
        </div><div class="note mt12">${esc(content.script?.reason || '')}</div>`)}
      ${section('标题 / Hook / 结尾', `<dl class="kv">
        <dt>标题</dt><dd>${esc(content.meta?.title || '未生成')}</dd>
        <dt>开场 Hook</dt><dd>${esc(content.meta?.opening_hook || '未生成')}</dd>
        <dt>结尾文案</dt><dd>${esc(content.meta?.ending || '未生成')}</dd>
      </dl>`, '这些字段当前没有真实来源')}
      ${section('旁白音频清单', content.narration?.lines?.length
        ? `<div class="table-wrap"><table class="table"><thead><tr><th>#</th><th>文本</th><th>时长</th></tr></thead>
           <tbody>${content.narration.lines.map((l) => `<tr><td class="mono-cell">${l.index}</td>
             <td>${esc(l.text)}</td><td class="mono-cell">${esc(fmtSeconds(l.duration))}</td></tr>`).join('')}</tbody></table></div>`
        : emptyState('没有音频清单', '未找到 audio_manifest.json。'))}`;
    return;
  }

  const source = content.source || {};
  const analysis = content.analysis || {};
  const runs = analysis.runs || [];
  const claims = analysis.claims || [];
  const grouped = {};
  for (const claim of claims) {
    (grouped[claim.claim_type] ||= []).push(claim);
  }
  const runBlock = runs.length ? runs.map((run) => `
    <div class="col" style="gap:8px">
      <div class="row wrap">
        <span class="tag">${esc(run.model || '?')}</span>
        <span class="tiny muted">${esc(fmtTime(run.finished_at, { withYear: true }))}</span>
        <span class="tag">${esc(run.dir)}</span>
        ${run.all_evidence_valid ? '<span class="badge b-verified">证据全部通过</span>'
          : '<span class="badge b-failed">存在证据失败</span>'}
        ${run.human_review === 'NOT_RUN' ? '<span class="badge b-not_run">人工审核 NOT_RUN</span>'
          : `<span class="badge b-verified">人工审核 ${esc(run.human_review)}</span>`}
      </div>
      <div class="table-wrap"><table class="table">
        <thead><tr><th>轮次</th><th>状态</th><th>耗时</th><th>claims</th><th>备注 / 错误</th></tr></thead>
        <tbody>${run.passes.map((p) => `<tr>
          <td class="mono-cell">${esc(p.pass_name)}</td>
          <td>${statusBadge(p.status)}</td>
          <td class="mono-cell">${p.elapsed_s != null ? `${p.elapsed_s}s` : '—'}</td>
          <td class="mono-cell">${p.claims}</td>
          <td class="muted small">${esc(p.error_code || p.notes || '')}</td>
        </tr>`).join('')}</tbody></table></div>
    </div>`).join('') : emptyState('没有绑定本语料的真实运行', 'literary_intelligence/runs 中没有 source_ids 匹配的运行记录。');

  host.innerHTML = `
    ${section('来源与授权', `<dl class="kv">
      <dt>作品</dt><dd>${esc(source.work || '')} · ${esc(source.author || '')}</dd>
      <dt>底本</dt><dd>${esc(source.edition || '')}</dd>
      <dt>来源</dt><dd>${source.url ? `<a href="${esc(source.url)}" target="_blank" rel="noreferrer">${esc(source.source_name || source.url)}</a>` : esc(source.source_name || '')}</dd>
      <dt>定位</dt><dd class="mono">${esc(source.locator || '')}</dd>
      <dt>许可</dt><dd>${esc(source.license || '')}</dd>
      <dt>商用</dt><dd>${esc(source.commercial_use || '')}</dd>
    </dl>`, '原样传递，不推断')}
    ${section('原文', `<pre class="prompt" style="max-height:none;white-space:pre-wrap">${esc(source.original_text || '（缺失）')}</pre>`,
      esc(source.source_name || ''))}
    ${section('规范化文本', `<pre class="prompt" style="max-height:none;white-space:pre-wrap">${esc(source.normalized_text || '（缺失）')}</pre>`)}
    ${section('分段', source.segments?.length
      ? `<div class="table-wrap"><table class="table"><thead><tr><th>ID</th><th>定位</th><th>原文</th></tr></thead>
         <tbody>${source.segments.map((s) => `<tr><td class="mono-cell">${esc(s.segment_id)}</td>
           <td class="mono-cell">${esc(s.locator)}</td><td>${esc(s.raw_text)}</td></tr>`).join('')}</tbody></table></div>`
      : emptyState('没有分段', ''))}
    ${section('文学分析', runBlock, `已记录 claim ${analysis.total_claims} · 已批准 ${analysis.approved_claims}`)}
    ${section('Claims', claims.length ? `<div class="col" style="gap:8px">
        ${Object.entries(grouped).map(([type, items]) => `
          <div><div class="tiny muted mb8">${esc(CLAIM_TYPE_LABEL[type] || type)}（${items.length}）</div>
          <div class="col" style="gap:6px">${items.map((c) => `<div class="claim">
            <div class="claim-statement">${esc(c.statement)}</div>
            <div class="claim-meta">
              <span class="mono">${esc(c.claim_id)}</span>
              <span class="mono">${esc(c.locator)}</span>
              <span class="tag">${esc(REVIEW_LABEL[c.review_status] || c.review_status)}</span>
              <span class="tag">${esc(c.confidence)}</span>
            </div>
          </div>`).join('')}</div></div>`).join('')}
      </div>` : emptyState('没有 claim', ''), esc(analysis.reason || ''))}
    ${section('文案', content.script?.draft_text
      ? `<pre class="prompt" style="max-height:none;white-space:pre-wrap">${esc(content.script.draft_text)}</pre>`
      : `<div class="row" style="justify-content:space-between"><span class="dim">状态</span>${statusBadge(content.script?.status)}</div>
         <div class="note mt12">${esc(content.script?.reason || '')}</div>`, 'editor 只能消费 approved claim')}`;
}

async function renderStoryboard(host, detail) {
  let data;
  try { data = await get(`/api/episodes/${encodeURIComponent(detail.id)}/storyboard`); }
  catch (err) { host.innerHTML = errorBox(err); return; }
  const segments = data.segments || [];
  if (!segments.length) {
    host.innerHTML = emptyState('没有视觉分段', data.note || '该期还没有 segments.json 或视觉素材。');
    return;
  }
  host.innerHTML = `
    <div class="note mb16">${esc(data.note || '')}</div>
    <div class="cards">${segments.map((seg) => `
      <div class="panel">
        <div class="card-thumb ${seg.type === 'image' ? 'vertical' : ''}"
          style="${seg.source_exists ? `background-image:url('${thumbUrl(seg.source, 520)}')` : ''}">
          ${seg.source_exists ? '' : '<div class="thumb-empty">素材缺失</div>'}
          <span class="thumb-badge"><span class="badge ${seg.type === 'video' ? 'b-running' : 'b-verified'}">${esc(seg.type)}</span></span>
        </div>
        <div class="card-body">
          <div class="row" style="justify-content:space-between">
            <span class="card-title">${esc(seg.id)}</span>
            <span class="mono tiny muted">${esc(fmtSeconds(seg.duration))}</span>
          </div>
          <div class="card-meta">
            <span>${esc(seg.motion || '—')}</span><span>·</span>
            <span>${seg.source_exists ? '素材存在' : '素材缺失'}</span>
            ${seg.source_job ? `<span>·</span><span>job ${esc(seg.source_job)}</span>` : ''}
          </div>
          <div class="mono tiny muted" title="${esc(seg.source)}" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(seg.source)}</div>
          ${seg.prompt ? `<details><summary class="tiny muted" style="cursor:pointer">视觉提示词</summary>
            <div class="prompt mt8">${esc(seg.prompt)}</div>
            ${seg.negative_prompt ? `<div class="tiny muted mt8">负面：${esc(seg.negative_prompt)}</div>` : ''}
            ${seg.prompt_source ? `<div class="tiny muted mt8 mono">来源：${esc(seg.prompt_source)}</div>` : ''}
          </details>` : '<div class="tiny muted">没有关联的生成参数</div>'}
        </div>
      </div>`).join('')}</div>`;
}

async function renderVisual(host, detail, ctx) {
  let styles = [];
  try { styles = (await get('/api/styles')).styles || []; } catch { styles = []; }
  const style = detail.style;
  const snapshot = style?.snapshot || {};
  if (!style || !Object.keys(snapshot).length) {
    host.innerHTML = emptyState('该期尚未绑定视觉风格',
      '在「风格管理」中创建或选择一个预设，然后应用到本期。',
      `<a class="btn" href="#/styles">前往风格管理</a>`);
    return;
  }
  const palette = snapshot.color_palette || {};
  const refs = snapshot.reference_assets || [];
  const drift = style.drifted
    ? `<div class="error-box mb12">全局预设已更新，但本期仍使用创建时的快照。历史成片不会被悄悄改变。</div>` : '';
  host.innerHTML = `
    ${drift}
    <div class="split">
      <div>
        ${section(`风格快照 · ${snapshot.name || ''}`, `<dl class="kv">
          <dt>描述</dt><dd>${esc(snapshot.description || '—')}</dd>
          <dt>视觉语言</dt><dd>${esc(snapshot.visual_language || '—')}</dd>
          <dt>光照</dt><dd>${esc(snapshot.lighting || '—')}</dd>
          <dt>镜头语言</dt><dd>${esc(snapshot.camera_language || '—')}</dd>
          <dt>构图</dt><dd>${esc(snapshot.composition || '—')}</dd>
          <dt>人物设计</dt><dd>${esc(snapshot.character_design || '—')}</dd>
          <dt>环境设计</dt><dd>${esc(snapshot.environment_design || '—')}</dd>
          <dt>比例</dt><dd>${esc(snapshot.aspect_ratio || '—')}</dd>
          <dt>适用类型</dt><dd>${esc((snapshot.applicable_content_types || []).join(' / ') || '—')}</dd>
        </dl>`, '期数快照，冻结于绑定时')}
        ${section('正向提示词', `<div class="prompt" style="max-height:none">${esc(snapshot.positive_prompt || '（空）')}</div>`)}
        ${section('负面提示词', `<div class="prompt" style="max-height:none">${esc(snapshot.negative_prompt || '（空）')}</div>`)}
      </div>
      <div>
        ${section('色彩方案', Object.keys(palette).length
          ? `<div class="swatches">${Object.entries(palette).map(([name, hex]) => `<div class="swatch">
              <i style="background:${esc(hex)}"></i><span>${esc(name)}</span><span>${esc(hex)}</span></div>`).join('')}</div>`
          : '<div class="muted">没有色板</div>')}
        ${section('参考资产', refs.length
          ? `<div class="asset-grid">${refs.map((path) => `<div class="asset" data-preview="${esc(path)}">
              <div class="asset-thumb" style="background-image:url('${thumbUrl(path, 360)}')"></div>
              <div class="asset-body"><div class="asset-name mono">${esc(path)}</div></div></div>`).join('')}</div>`
          : '<div class="muted">没有参考图</div>')}
        ${section('应用新风格快照', `
          <div class="field"><label>选择全局预设</label>
            <select class="input" id="style-select">
              <option value="">（保持不变）</option>
              ${styles.map((s) => `<option value="${esc(s.id)}" ${s.id === style.id ? 'selected' : ''}>${esc(s.name)}</option>`).join('')}
            </select></div>
          <div class="note mt12">应用后，本期快照会被替换为当前预设的副本；已生成的成片与 manifest 不变。</div>
          <button class="btn mt12" id="apply-style">应用为快照</button>`,
          '修改全局预设不会影响历史期数')}
      </div>
    </div>`;

  host.querySelectorAll('[data-preview]').forEach((el) => {
    el.addEventListener('click', () => {
      const path = el.dataset.preview;
      openPreview({ path, name: path.split('/').pop(), type: 'image', size: null, mtime: null, referenced: true });
    });
  });
  host.querySelector('#apply-style')?.addEventListener('click', async () => {
    const value = host.querySelector('#style-select').value;
    if (!value) { toast('请先选择一个风格', 'warn'); return; }
    try {
      await patch(`/api/episodes/${encodeURIComponent(detail.id)}`, { style_id: value });
      toast('已应用新的风格快照', 'ok');
      ctx.refresh();
    } catch (err) { toast(err.message, 'bad', 6000); }
  });
}

async function renderAudio(host, detail) {
  let data;
  try { data = await get(`/api/episodes/${encodeURIComponent(detail.id)}/audio`); }
  catch (err) { host.innerHTML = errorBox(err); return; }
  if (!data.lines?.length) {
    host.innerHTML = emptyState('没有配音记录', '未找到 audio_manifest.json 或其中没有行。');
    return;
  }
  const bad = data.lines.filter((l) => !l.sha_ok).length;
  host.innerHTML = `
    ${section('音频清单', `
      <div class="row mb12">
        <span class="tag">speaker ${esc(data.speaker || '?')}</span>
        <span class="tag">${data.lines.length} 行</span>
        <span class="tag">总时长 ${esc(fmtSeconds(data.total_seconds))}</span>
        ${bad ? `<span class="badge b-failed">${bad} 行哈希不一致</span>` : '<span class="badge b-verified">全部哈希一致</span>'}
      </div>
      <div class="table-wrap"><table class="table">
        <thead><tr><th>#</th><th>文本</th><th>时长</th><th>校验</th><th>播放</th><th>文件</th></tr></thead>
        <tbody>${data.lines.map((l) => `<tr>
          <td class="mono-cell">${l.index}</td>
          <td>${esc(l.text)}</td>
          <td class="mono-cell">${esc(fmtSeconds(l.duration_seconds))}</td>
          <td>${l.exists ? (l.sha_ok ? '<span class="badge b-verified">一致</span>' : '<span class="badge b-failed">不一致</span>')
            : '<span class="badge b-not_run">缺失</span>'}</td>
          <td style="min-width:220px">${l.exists ? `<audio class="audio-inline" controls preload="none" src="${mediaUrl(l.file)}"></audio>` : '—'}</td>
          <td class="mono-cell">${esc(l.file)}</td>
        </tr>`).join('')}</tbody></table></div>`, esc(data.manifest || ''))}
    ${section('字幕时间轴', data.timeline?.segments?.length
      ? `<div class="table-wrap"><table class="table">
          <thead><tr><th>段</th><th>语音起</th><th>语音止</th><th>字幕起</th><th>字幕止</th><th>文本</th></tr></thead>
          <tbody>${data.timeline.segments.map((s) => `<tr>
            <td class="mono-cell">${esc(s.segment_id)}</td>
            <td class="mono-cell">${s.speech_start_ms}</td><td class="mono-cell">${s.speech_end_ms}</td>
            <td class="mono-cell">${s.subtitle_start_ms}</td><td class="mono-cell">${s.subtitle_end_ms}</td>
            <td>${esc(s.subtitle_text)}</td></tr>`).join('')}</tbody></table></div>`
      : `<div class="muted">${esc(data.timeline?.note || '没有 timeline.json')}</div>`, '整数毫秒')}`;
}

async function renderAssets(host, detail) {
  let data;
  try { data = await get(`/api/episodes/${encodeURIComponent(detail.id)}/assets`); }
  catch (err) { host.innerHTML = errorBox(err); return; }
  const items = data.items || [];
  if (!items.length) { host.innerHTML = emptyState('没有素材', '产物目录不存在或为空。'); return; }
  host.innerHTML = `<div class="row mb12 wrap">
      <span class="tag">${items.length} 个文件</span>
      <span class="tag">${items.filter((i) => i.referenced).length} 个被生产引用</span>
      <span class="tag">${items.filter((i) => i.temporary).length} 个实验临时文件</span>
    </div>
    <div class="asset-grid">${items.map((item) => `
      <div class="asset" data-path="${esc(item.path)}">
        ${item.type === 'image' || item.type === 'video'
          ? `<div class="asset-thumb" style="background-image:url('${thumbUrl(item.path, 360)}')">
              ${item.referenced ? '<span class="ref-flag">引用</span>' : ''}</div>`
          : `<div class="asset-thumb"><span style="font-size:18px;color:var(--faint)">${
              { audio: '♪', subtitle: '字', text: 'T', json: '{ }', log: '⋯' }[item.type] || '·'}</span>
              ${item.referenced ? '<span class="ref-flag">引用</span>' : ''}</div>`}
        <div class="asset-body">
          <div class="asset-name">${esc(item.name)}</div>
          <div class="asset-meta"><span>${esc(item.type)}</span><span>${esc(fmtBytes(item.size))}</span></div>
          ${item.temporary ? '<div class="tiny muted">临时文件</div>' : ''}
        </div>
      </div>`).join('')}</div>`;
  host.querySelectorAll('[data-path]').forEach((el) => {
    el.addEventListener('click', () => {
      const item = items.find((i) => i.path === el.dataset.path);
      if (item) openPreview(item);
    });
  });
}

async function renderOutput(host, detail) {
  let data;
  try { data = await get(`/api/episodes/${encodeURIComponent(detail.id)}/output`); }
  catch (err) { host.innerHTML = errorBox(err); return; }
  if (!data.latest) {
    host.innerHTML = emptyState('还没有成片', '该期没有通过哈希校验的最终视频。');
    return;
  }
  const latest = data.latest;
  const final = latest.final;
  const probe = final.probe;
  const video = probe?.streams?.find((s) => s.type === 'video');
  const audio = probe?.streams?.find((s) => s.type === 'audio');
  const subtitle = probe?.streams?.find((s) => s.type === 'subtitle');
  host.innerHTML = `
    <div class="split">
      <div>
        ${section('最终成片', `
          <video class="player player-vertical" controls preload="metadata" src="${mediaUrl(final.path)}"></video>
          <div class="row mt12 wrap">
            <span class="tag mono">${esc(final.path)}</span>
            <span class="badge ${final.sha_ok ? 'b-verified' : 'b-failed'}">${final.sha_ok ? '哈希一致' : '哈希不一致'}</span>
            ${latest.manifest_version === 'legacy' ? '<span class="badge b-unknown">旧版 manifest</span>' : '<span class="badge b-verified">当前 manifest</span>'}
          </div>`, esc(latest.dir))}
      </div>
      <div>
        ${section('技术参数', `<dl class="kv">
          <dt>时长</dt><dd>${esc(fmtSeconds(probe?.duration))}</dd>
          <dt>分辨率</dt><dd class="mono">${video ? `${video.width}×${video.height}` : '—'}</dd>
          <dt>帧率</dt><dd class="mono">${esc(video?.fps || '—')}</dd>
          <dt>视频编码</dt><dd class="mono">${esc(video?.codec || '—')}</dd>
          <dt>音频</dt><dd class="mono">${audio ? `${audio.codec} · ${audio.sample_rate} Hz · ${audio.channels} ch` : '无'}</dd>
          <dt>字幕轨</dt><dd class="mono">${esc(subtitle?.codec || '无')}</dd>
          <dt>文件大小</dt><dd>${esc(fmtBytes(final.size))}</dd>
          <dt>SHA-256</dt><dd class="mono">${esc((final.sha256 || '').slice(0, 20))}…</dd>
        </dl>`)}
        ${section('构建信息', `<dl class="kv">
          <dt>manifest</dt><dd class="mono">${esc(latest.manifest)}</dd>
          <dt>内容类型</dt><dd>${esc(latest.content_type || '未记录')}</dd>
          <dt>分段数</dt><dd>${latest.segment_count}</dd>
          <dt>字幕字体</dt><dd class="mono">${esc(latest.font?.postscript_name || '未记录（旧版构建）')}</dd>
          <dt>解码校验</dt><dd>${latest.decode_returncode === 0 ? '通过' : esc(String(latest.decode_returncode))}</dd>
        </dl>`, esc(fmtTime(latest.created_at, { withYear: true })))}
      </div>
    </div>
    ${section('构建历史', buildTable(data.builds || []), esc(data.note || ''))}`;
}

export default {
  async render(view, params, ctx) {
    let detail;
    try {
      detail = await get(`/api/episodes/${encodeURIComponent(params.episodeId)}`);
    } catch (err) {
      view.innerHTML = errorBox(err);
      return;
    }
    const tab = TABS.some(([id]) => id === params.tab) ? params.tab : 'overview';
    const running = (detail.tasks || []).find((t) => t.status === 'RUNNING' || t.status === 'PENDING');
    view.innerHTML = `
      <div class="ep-head">
        <div class="row" style="justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap">
          <div style="min-width:0">
            <div class="ep-title-row">
              <span class="tag mono">EP${String(detail.number).padStart(2, '0')}</span>
              <h1 class="ep-title">${esc(detail.title)}</h1>
              ${statusBadge(detail.status)}
              ${running ? `<a class="badge b-running" href="#/tasks?id=${encodeURIComponent(running.id)}">${statusLabel(running.status)} · ${esc(running.kind)}</a>` : ''}
            </div>
            <div class="ep-meta">
              <span>项目 <b>${esc(detail.project?.name || '—')}</b></span>
              <span>类型 <b>${esc(detail.track)}</b></span>
              <span>风格 <b>${esc(detail.style?.name || '未绑定')}</b></span>
              <span>目录 <b class="mono">${esc(detail.artifact_root || '未绑定')}</b></span>
              <span>更新 <b>${esc(fmtTime(detail.updated_at))}</b></span>
              <span>人工验收 <b>${esc(statusLabel(detail.review?.status))}</b></span>
            </div>
          </div>
          <div class="ep-actions">
            ${detail.track === 'video' ? '<button class="btn btn-primary" id="rebuild-btn">合成重建（新目录）</button>' : ''}
            <a class="btn" href="#/workflow?episode=${encodeURIComponent(detail.id)}">工作流</a>
            <a class="btn btn-ghost" href="#/tasks?episode=${encodeURIComponent(detail.id)}">任务</a>
          </div>
        </div>
        <div class="row mt12" style="gap:14px;align-items:center;flex-wrap:wrap">
          ${progressBar(detail.progress)}
          <span class="tiny muted">${detail.progress.verified}/${detail.progress.required} 个必需步骤已验证；PARTIAL 不计入完成</span>
        </div>
      </div>
      <div class="tabs">${TABS.map(([id, label]) => `<button class="tab ${id === tab ? 'active' : ''}"
        data-tab="${id}">${label}</button>`).join('')}</div>
      <div id="tab-body">${loading()}</div>`;

    const host = view.querySelector('#tab-body');
    const renderTab = async (id) => {
      host.innerHTML = loading();
      try {
        if (id === 'overview') await renderOverview(host, detail, ctx);
        else if (id === 'content') await renderContent(host, detail);
        else if (id === 'storyboard') await renderStoryboard(host, detail);
        else if (id === 'visual') await renderVisual(host, detail, ctx);
        else if (id === 'audio') await renderAudio(host, detail);
        else if (id === 'assets') await renderAssets(host, detail);
        else if (id === 'output') await renderOutput(host, detail);
      } catch (err) {
        host.innerHTML = errorBox(err);
      }
    };
    await renderTab(tab);

    view.querySelectorAll('[data-tab]').forEach((btn) => {
      btn.addEventListener('click', () => {
        location.hash = `#/episodes/${encodeURIComponent(detail.id)}?tab=${btn.dataset.tab}`;
      });
    });

    view.querySelector('#rebuild-btn')?.addEventListener('click', async () => {
      const ok = await confirmDialog({
        title: '合成重建',
        body: `将调用 scripts/r3_build.py，读取 ${detail.artifact_root}/segments.json 与 audio_manifest.json，`
          + '写入一个新的 projects/…/renders/build-<时间> 目录。不会覆盖 experiments/r3b/renders 下的历史成片。',
        confirmLabel: '开始重建',
      });
      if (!ok) return;
      const task = await runTask('build.rebuild', { episode_id: detail.id });
      if (task?.id) location.hash = `#/tasks?id=${encodeURIComponent(task.id)}`;
    });
  },
};

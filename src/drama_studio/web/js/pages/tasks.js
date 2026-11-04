import { get, post } from '../api.js';
import {
  esc, statusBadge, fmtTime, loading, errorBox, emptyState, pageHead, toast,
  confirmDialog, openDrawer,
} from '../ui.js';

const FILTERS = [
  ['', '全部'], ['RUNNING', '运行中'], ['PENDING', '等待'], ['SUCCEEDED', '成功'],
  ['FAILED', '失败'], ['BLOCKED', '受阻'], ['CANCELLED', '已取消'],
];

function duration(task) {
  if (!task.started_at) return '—';
  const end = task.finished_at ? new Date(task.finished_at) : new Date();
  const ms = end - new Date(task.started_at);
  if (!Number.isFinite(ms) || ms < 0) return '—';
  return ms < 60000 ? `${(ms / 1000).toFixed(0)} s` : `${(ms / 60000).toFixed(1)} min`;
}

function row(task, kinds) {
  const label = kinds[task.kind]?.label || task.kind;
  return `<tr class="clickable" data-task="${esc(task.id)}">
    <td><div class="title-cell">${esc(label)}</div><div class="mono tiny muted">${esc(task.kind)}</div></td>
    <td>${statusBadge(task.status)}</td>
    <td class="muted small">${esc(task.episode_id || '—')}</td>
    <td class="muted small">${fmtTime(task.created_at)}</td>
    <td class="mono-cell nowrap">${esc(duration(task))}</td>
    <td class="mono-cell nowrap">${task.exit_code ?? '—'}</td>
    <td class="muted small" style="max-width:380px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
      title="${esc(task.error || '')}">${esc(task.error || task.result?.final || '')}</td>
  </tr>`;
}

async function openTaskDrawer(taskId, kinds, refresh) {
  let task;
  try { task = await get(`/api/tasks/${encodeURIComponent(taskId)}`); }
  catch (err) { toast(err.message, 'bad'); return; }

  const label = kinds[task.kind]?.label || task.kind;
  openDrawer(`${label} · ${task.id}`, `
    <div class="row mb12 wrap">
      ${statusBadge(task.status)}
      <span class="tag mono">${esc(task.kind)}</span>
      ${task.episode_id ? `<a class="tag" href="#/episodes/${encodeURIComponent(task.episode_id)}">${esc(task.episode_id)}</a>` : ''}
      <span class="tag">lock ${esc(task.lock_key)}</span>
    </div>
    <dl class="kv mb16">
      <dt>创建</dt><dd>${esc(fmtTime(task.created_at, { withYear: true }))}</dd>
      <dt>开始</dt><dd>${esc(fmtTime(task.started_at, { withYear: true }))}</dd>
      <dt>结束</dt><dd>${esc(fmtTime(task.finished_at, { withYear: true }))}</dd>
      <dt>耗时</dt><dd>${esc(duration(task))}</dd>
      <dt>退出码</dt><dd class="mono">${task.exit_code ?? '—'}</dd>
      <dt>日志</dt><dd class="mono">${esc(task.log_path || '—')}</dd>
    </dl>
    ${task.error ? `<div class="error-box mb16">${esc(task.error)}</div>` : ''}
    <div class="panel mb16"><div class="panel-head"><span class="panel-title">参数</span></div>
      <div class="panel-body"><pre class="prompt" style="max-height:180px">${esc(JSON.stringify(task.params, null, 2))}</pre></div></div>
    ${task.result && Object.keys(task.result).length ? `<div class="panel mb16"><div class="panel-head">
      <span class="panel-title">结果</span></div>
      <div class="panel-body"><pre class="prompt" style="max-height:220px">${esc(JSON.stringify(task.result, null, 2))}</pre></div></div>` : ''}
    <div class="panel"><div class="panel-head"><span class="panel-title">运行日志</span>
      <span class="panel-sub" id="log-state">${task.status === 'RUNNING' || task.status === 'PENDING' ? '实时读取' : '已结束'}</span></div>
      <div class="panel-body"><div class="log-view" id="task-log">读取中…</div></div></div>
    <div class="row mt16">
      ${task.status === 'RUNNING' || task.status === 'PENDING'
        ? `<button class="btn btn-danger" id="task-cancel">取消任务</button>` : ''}
      <button class="btn" id="task-rerun" ${task.kind === 'tts.synthesize' ? 'disabled' : ''}>重新执行（新任务）</button>
    </div>`, {
    onMount(root) {
      let offset = 0;
      const logEl = root.querySelector('#task-log');
      const stateEl = root.querySelector('#log-state');
      const tick = async () => {
        if (!document.querySelector('.drawer')) { clearInterval(timer); return; }
        try {
          const data = await get(`/api/tasks/${encodeURIComponent(task.id)}/log?offset=${offset}`);
          if (data.text) {
            logEl.textContent += data.text;
            logEl.scrollTop = logEl.scrollHeight;
          }
          offset = data.next_offset;
          if (data.eof) { stateEl.textContent = '已结束'; clearInterval(timer); }
        } catch (err) {
          logEl.textContent += `\n[读取日志失败] ${err.message}`;
          clearInterval(timer);
        }
      };
      const timer = setInterval(tick, 1500);
      tick();

      root.querySelector('#task-cancel')?.addEventListener('click', async () => {
        const ok = await confirmDialog({
          title: '取消任务', body: '将终止该任务的进程树。已产生的部分文件不会被删除。',
          confirmLabel: '确认取消', danger: true,
        });
        if (!ok) return;
        try {
          await post(`/api/tasks/${encodeURIComponent(task.id)}/cancel`);
          toast('已取消', 'warn');
          refresh();
        } catch (err) { toast(err.message, 'bad'); }
      });

      root.querySelector('#task-rerun')?.addEventListener('click', async () => {
        const kind = kinds[task.kind];
        const danger = kind?.danger;
        const ok = await confirmDialog({
          title: '重新执行',
          body: `将以相同参数创建新任务（旧记录保留）。${danger ? '该任务会占用 GPU/LLM，请确认没有其他任务在运行。' : ''}`,
          confirmLabel: '执行', danger: Boolean(danger),
        });
        if (!ok) return;
        try {
          const created = await post('/api/tasks', { kind: task.kind, params: task.params });
          toast(created.status === 'BLOCKED' ? created.error : `新任务：${created.id}`,
            created.status === 'BLOCKED' ? 'warn' : 'ok', 6000);
          refresh();
        } catch (err) { toast(err.message, 'bad', 6000); }
      });
    },
  });
}

function launcherForm(kindKey, kinds, episodes) {
  const kind = kinds[kindKey];
  if (!kind) return '';
  const common = kind.enabled
    ? ''
    : `<div class="error-box mt8">${esc(kind.blocked_reason || '当前不可用')}</div>`;
  let fields = '';
  if (kindKey === 'build.rebuild') {
    fields = `<div class="field"><label>期数</label>
      <select class="input" name="episode_id">${episodes.map((e) => `<option value="${esc(e.id)}">EP${String(e.number).padStart(2, '0')} · ${esc(e.title)}</option>`).join('')}</select></div>
      <div class="field"><label>多轨音频时间轴（可选）</label>
        <input class="input mono" name="audio_timeline" placeholder="例如：work/audio_timeline.json；留空走旧旁白混音"></div>
      <div class="field"><label>音频资产注册表（可选）</label>
        <input class="input mono" name="audio_assets" placeholder="留空自动使用 assets/audio/manifest.json"></div>`;
  } else if (kindKey === 'comfy.batch') {
    fields = `<div class="field"><label>jobs JSON（experiments/ 之下）</label>
      <input class="input mono" name="jobs" placeholder="experiments/r3a/jobs_flux.json"></div>
      <div class="field"><label>仅执行指定 job（可选，逗号分隔）</label>
        <input class="input mono" name="only" placeholder="V1,V2"></div>`;
  } else if (kindKey === 'review.accept' || kindKey === 'review.reject') {
    fields = `<div class="field"><label>期数</label>
      <select class="input" name="episode_id">${episodes.map((e) => `<option value="${esc(e.id)}">EP${String(e.number).padStart(2, '0')} · ${esc(e.title)}</option>`).join('')}</select></div>
      <div class="field"><label>备注（可选）</label>
        <textarea class="textarea" name="note" style="min-height:56px"></textarea></div>`;
  } else if (['package.build', 'segments.build', 'quality.check', 'static.check', 'motion.plan', 'motion.render', 'audio.qa',
              'aesthetic.plan', 'aesthetic.compare', 'aesthetic.review'].includes(kindKey)) {
    fields = `<div class="field"><label>期数</label>
      <select class="input" name="episode_id">${episodes.map((e) => `<option value="${esc(e.id)}">EP${String(e.number).padStart(2, '0')} · ${esc(e.title)}</option>`).join('')}</select></div>`;
    if (kindKey === 'quality.check') {
      fields += `<div class="field"><label>manifest（可选）</label>
        <input class="input mono" name="manifest" placeholder="留空则取最新 build_manifest.json"></div>`;
    }
    if (kindKey === 'motion.plan') {
      fields += `<div class="field"><label>风格预设（可选）</label>
        <input class="input mono" name="style" placeholder="ink_wash / court_green_fine_line；留空读取 production_script.style_id"></div>
        <div class="field"><label>局部运动区域（可选）</label>
          <input class="input mono" name="regions" placeholder="留空读取 motion_regions.json"></div>
        <div class="field"><label>静态质量门</label>
          <select class="input" name="skip_static_gate">
            <option value="">require · 缺报告即失败（默认）</option>
            <option value="true">skip · 显式跳过（记录原因）</option>
          </select></div>`;
    }
    if (kindKey === 'static.check') {
      fields += `<div class="form-row">
        <div class="field"><label>镜头</label><input class="input mono" name="shot_id" placeholder="shot_001" required></div>
        <div class="field"><label>风格（可选）</label><input class="input mono" name="style" placeholder="留空读取期数 style_snapshot"></div>
      </div>
      <div class="field"><label>图片（可选）</label><input class="input mono" name="image" placeholder="留空取 assets/images/&lt;shot_id&gt;/ 第一张"></div>
      <div class="form-row">
        <div class="field"><label>人工清单（可选）</label><input class="input mono" name="manual" placeholder="manual.json"></div>
        <div class="field"><label>美学 JSON（可选）</label><input class="input mono" name="aesthetic" placeholder="shot_aesthetic.json"></div>
      </div>
      <div class="field"><label>报告输出（可选）</label><input class="input mono" name="out" placeholder="默认 work/static/&lt;shot_id&gt;/static_quality.json"></div>`;
    }
    if (kindKey === 'motion.render') {
      fields += `<div class="field"><label>plan（可选）</label>
        <input class="input mono" name="plan" placeholder="留空读取 motion_shots.json"></div>`;
    }
    if (kindKey === 'audio.qa') {
      fields += `<div class="field"><label>多轨时间轴（可选）</label>
        <input class="input mono" name="audio_timeline" placeholder="填写后检查 audio_timeline.json；留空走逐行音频 QA"></div>
        <div class="field"><label>音频资产注册表（可选）</label>
          <input class="input mono" name="audio_assets" placeholder="留空自动使用 assets/audio/manifest.json"></div>
        <div class="field"><label>audio_manifest（可选）</label>
        <input class="input mono" name="manifest" placeholder="留空读取本期 audio_manifest.json"></div>
        <div class="field"><label>timeline（可选）</label>
          <input class="input mono" name="timeline" placeholder="留空取最新 renders/*/timeline.json"></div>`;
    }
    if (kindKey === 'aesthetic.plan') {
      fields += `<div class="field"><label>风格预设（可选）</label>
        <input class="input mono" name="style" placeholder="ink_wash / court_green_fine_line"></div>
        <div class="form-row">
          <div class="field"><label>designs（可选）</label><input class="input mono" name="designs" placeholder="留空读取 designs.json"></div>
          <div class="field"><label>axes（可选）</label><input class="input mono" name="axes" placeholder="留空读取 axes.json"></div>
        </div>
        <div class="form-row">
          <div class="field"><label>宽</label><input class="input" name="width" type="number" value="576"></div>
          <div class="field"><label>高</label><input class="input" name="height" type="number" value="1024"></div>
          <div class="field"><label>seed 基数</label><input class="input" name="seed_base" type="number" value="8100"></div>
        </div>`;
    }
    if (kindKey === 'aesthetic.compare') {
      fields += `<div class="field"><label>plan（可选）</label>
        <input class="input mono" name="plan" placeholder="留空读取 aesthetic/aesthetic_plan.json"></div>
        <div class="field"><label>图片根目录（可选）</label>
          <input class="input mono" name="images" placeholder="留空取最新 snapshot/images"></div>`;
    }
    if (kindKey === 'aesthetic.review') {
      fields += `<div class="field"><label>结论</label>
        <select class="input" name="decision"><option value="PASS">PASS</option><option value="REVISE">REVISE</option><option value="REJECT">REJECT</option></select></div>
        <div class="form-row">
          <div class="field"><label>镜头（可选）</label><input class="input mono" name="shot_id" placeholder="shot_001"></div>
          <div class="field"><label>版本（可选）</label><select class="input" name="variant"><option value="">—</option><option value="A">A</option><option value="B">B</option></select></div>
        </div>
        <div class="field"><label>备注</label><textarea class="textarea" name="note" style="min-height:56px"></textarea></div>`;
    }
  } else if (kindKey === 'script.generate') {
    fields = `<div class="field"><label>期数</label>
      <select class="input" name="episode_id">${episodes.map((e) => `<option value="${esc(e.id)}">EP${String(e.number).padStart(2, '0')} · ${esc(e.title)}</option>`).join('')}</select></div>
      <div class="form-row">
        <div class="field"><label>音色（可选）</label><input class="input" name="speaker" placeholder="例如：中文女"></div>
        <div class="field"><label>音色档案（可选）</label><input class="input mono" name="voice_profile" placeholder="config/voices.yaml 的 profile_id"></div>
        <div class="field"><label>语速（可选）</label><input class="input" name="speed" type="number" step="0.05" min="0.5" max="2.0" placeholder="留空用档案/默认"></div>
      </div>
      <div class="field"><label>max_tokens</label><input class="input" name="max_tokens" type="number" value="2000"></div>`;
  } else if (kindKey === 'story.check') {
    fields = `<div class="field"><label>期数</label>
      <select class="input" name="episode_id">${episodes.map((e) => `<option value="${esc(e.id)}">EP${String(e.number).padStart(2, '0')} · ${esc(e.title)}</option>`).join('')}</select></div>
      <div class="field"><label>ProductionScript（可选）</label>
        <input class="input mono" name="script" placeholder="默认：本期 production_script.json"></div>
      <div class="form-row">
        <div class="field"><label>Character Bible（可选）</label>
          <input class="input mono" name="characters" placeholder="默认：本期 character_bible.yaml"></div>
        <div class="field"><label>Shot Bible（可选）</label>
          <input class="input mono" name="shots" placeholder="默认：本期 shot_bible.yaml"></div>
      </div>
      <div class="form-row">
        <div class="field"><label>Voice Library（可选）</label>
          <input class="input mono" name="voices" placeholder="例如：config/voices.yaml"></div>
        <div class="field"><label>报告输出（可选）</label>
          <input class="input mono" name="out" placeholder="默认：本期 story_bible_report.json"></div>
      </div>`;
  } else if (kindKey === 'tts.synthesize') {
    fields = `<div class="field"><label>期数</label>
      <select class="input" name="episode_id">${episodes.map((e) => `<option value="${esc(e.id)}">EP${String(e.number).padStart(2, '0')} · ${esc(e.title)}</option>`).join('')}</select></div>
      <div class="field"><label>合成模式</label>
        <select class="input" name="tts_mode">
          <option value="">读取 config/audio.yaml（默认 zero_shot）</option>
          <option value="sft">sft · 预置音色（CosyVoice-300M-SFT）</option>
          <option value="zero_shot">zero_shot · 参考音克隆（CosyVoice2-0.5B）</option>
        </select></div>
      <div class="field"><label>音色档案（可选）</label>
        <input class="input mono" name="voice_profile" placeholder="profile_id；逐行 voice_profile 优先；留空走旧配置"></div>
      <div class="form-row">
        <div class="field"><label>音色（仅 SFT）</label>
          <input class="input" name="speaker" placeholder="例如：中文女；留空读取 narration.json / config"></div>
        <div class="field"><label>语速（可选）</label>
          <input class="input" name="speed" type="number" step="0.05" min="0.5" max="2.0" placeholder="1.0"></div>
      </div>
      <div class="field"><label>音色库路径（可选）</label>
        <input class="input mono" name="voices" placeholder="默认 config/voices.yaml"></div>
      <div class="field"><label>Voice Cast 文件（可选）</label>
        <input class="input mono" name="voice_cast" placeholder="YAML：按行号/line_id 映射 profile"></div>
      <div class="field"><label>诵读模式（可选）</label>
        <select class="input" name="mode">
          <option value="">读取 narration.json</option>
          <option value="narration">narration · 普通旁白</option>
          <option value="recitation">recitation · 标准朗诵</option>
          <option value="classical_recitation">classical_recitation · 古典吟诵</option>
        </select></div>`;
  } else if (kindKey === 'li.run') {
    fields = `<div class="field"><label>语料目录</label>
      <input class="input mono" name="corpus" required
        placeholder="literary_intelligence/corpus/&lt;corpus_id&gt;"></div>
      <div class="field"><label>max_tokens</label><input class="input" name="max_tokens" type="number" value="1600"></div>`;
  }
  const confirmField = kind.danger || ['comfy.batch', 'li.run'].includes(kindKey)
    ? `<label class="row" style="gap:7px"><input type="checkbox" name="confirm"> 我确认该操作会占用 GPU / LLM，并遵守单飞约束</label>` : '';
  return `<div class="form mt12">
    <div class="note">${esc(kind.description)}<br>成本：${esc(kind.cost)}<br>安全：${esc(kind.safety)}</div>
    ${fields}
    ${confirmField}
    ${common}
    <div><button class="btn btn-primary" id="launch-task" ${kind.enabled ? '' : 'disabled'}>启动任务</button></div>
  </div>`;
}

export default {
  async render(view, params) {
    let kindsData;
    let tasksData;
    let episodesData;
    try {
      [kindsData, tasksData, episodesData] = await Promise.all([
        get('/api/tasks/kinds'),
        get(`/api/tasks${params.episode ? `?episode_id=${encodeURIComponent(params.episode)}` : ''}`),
        get('/api/episodes'),
      ]);
    } catch (err) { view.innerHTML = errorBox(err); return; }
    const kinds = Object.fromEntries((kindsData.kinds || []).map((k) => [k.key, k]));
    const episodes = episodesData.episodes || [];
    const status = params.status || '';
    const tasks = (tasksData.tasks || []).filter((t) => !status || t.status === status);

    view.innerHTML = `
      ${pageHead('任务中心', '任务由受限注册表创建。每条记录对应一次真实进程；日志与退出码原样保存。',
        `<a class="btn btn-ghost" href="#/tasks${params.episode ? '' : ''}">刷新</a>`)}
      <div class="split">
        <div class="panel">
          <div class="panel-head"><span class="panel-title">任务记录</span>
            <span class="panel-sub">${tasks.length} 条</span></div>
          <div class="panel-body tight">
            <div class="chips" style="padding:10px 14px">
              ${FILTERS.map(([value, label]) => {
                const q = new URLSearchParams();
                if (params.episode) q.set('episode', params.episode);
                if (value) q.set('status', value);
                return `<a class="chip ${status === value ? 'active' : ''}" href="#/tasks${q.toString() ? `?${q}` : ''}">${label}</a>`;
              }).join('')}
            </div>
            <div id="task-table">${tasks.length ? `<div class="table-wrap"><table class="table">
              <thead><tr><th>类型</th><th>状态</th><th>期数</th><th>创建</th><th>耗时</th><th>退出码</th><th>错误 / 结果</th></tr></thead>
              <tbody>${tasks.map((t) => row(t, kinds)).join('')}</tbody></table></div>`
              : emptyState('没有任务记录', '在下方启动一个任务，或到期数工作区执行合成。')}</div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-head"><span class="panel-title">启动任务</span>
            <span class="panel-sub">仅注册表内入口</span></div>
          <div class="panel-body">
            <div class="field"><label>任务类型</label>
              <select class="input" id="kind-select">
                ${(kindsData.kinds || []).map((k) => `<option value="${esc(k.key)}" ${k.enabled ? '' : 'disabled'}>
                  ${esc(k.label)}${k.enabled ? '' : '（不可用）'}</option>`).join('')}
              </select></div>
            <div id="kind-form">${launcherForm((kindsData.kinds || [])[0]?.key, kinds, episodes)}</div>
          </div>
        </div>
      </div>`;

    const bindRows = () => {
      view.querySelectorAll('[data-task]').forEach((rowEl) => {
        rowEl.addEventListener('click', () => {
          location.hash = `#/tasks?id=${encodeURIComponent(rowEl.dataset.task)}`;
        });
      });
    };
    bindRows();

    const selectedKind = view.querySelector('#kind-select');
    selectedKind.addEventListener('change', () => {
      view.querySelector('#kind-form').innerHTML = launcherForm(selectedKind.value, kinds, episodes);
      bindLaunch();
    });

    const bindLaunch = () => {
      const btn = view.querySelector('#launch-task');
      if (!btn) return;
      btn.addEventListener('click', async () => {
        const form = btn.closest('.form');
        const kindKey = selectedKind.value;
        const kind = kinds[kindKey];
        const paramsOut = {};
        form.querySelectorAll('input[name], select[name]').forEach((el) => {
          if (el.name === 'confirm') {
            paramsOut.confirm = el.checked;
          } else if (el.value !== '') {
            paramsOut[el.name] = el.type === 'number' ? Number(el.value) : el.value;
          }
        });
        if (kind.danger && !paramsOut.confirm) { toast('请先勾选确认', 'warn'); return; }
        const ok = await confirmDialog({
          title: `启动：${kind.label}`,
          body: `${kind.description}\n\n成本：${kind.cost}\n安全：${kind.safety}`,
          confirmLabel: '启动', danger: Boolean(kind.danger),
        });
        if (!ok) return;
        try {
          const task = await post('/api/tasks', { kind: kindKey, params: paramsOut });
          if (task.status === 'BLOCKED') toast(task.error || '前置不满足', 'warn', 7000);
          else toast(`任务已创建：${task.id}`, 'ok');
          this.render(view, params);
        } catch (err) { toast(err.message, 'bad', 7000); }
      });
    };
    bindLaunch();

    if (params.id) openTaskDrawer(params.id, kinds, () => this.render(view, params));

    const timer = setInterval(async () => {
      if (!document.body.contains(view)) { clearInterval(timer); return; }
      try {
        const fresh = await get(`/api/tasks${params.episode ? `?episode_id=${encodeURIComponent(params.episode)}` : ''}`);
        const list = (fresh.tasks || []).filter((t) => !status || t.status === status);
        const table = view.querySelector('#task-table');
        if (table && list.length) {
          table.innerHTML = `<div class="table-wrap"><table class="table">
            <thead><tr><th>类型</th><th>状态</th><th>期数</th><th>创建</th><th>耗时</th><th>退出码</th><th>错误 / 结果</th></tr></thead>
            <tbody>${list.map((t) => row(t, kinds)).join('')}</tbody></table></div>`;
          bindRows();
        }
      } catch { /* keep last good view */ }
    }, 4000);
  },
};

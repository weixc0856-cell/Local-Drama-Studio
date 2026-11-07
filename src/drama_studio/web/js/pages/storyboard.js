import { get, patch, thumbUrl } from '../api.js';
import { esc, pageHead, loading, errorBox, emptyState, statusBadge, toast } from '../ui.js';

const SIZES = ['ews', 'ws', 'fs', 'ms', 'mcu', 'cu', 'ecu', 'ots'];
const MOVES = ['static', 'dolly_in', 'dolly_out', 'tracking', 'pan', 'tilt', 'crane', 'orbit', 'handheld'];
const DOFS = ['shallow', 'medium', 'deep'];

const state = { projectId: null, detail: null, selected: null, mode: 'cards' };

function narrationText(detail, ids) {
  if (!ids || !ids.length) return '';
  const segments = (detail.narration && detail.narration.segments) || [];
  return ids.map((id) => (segments.find((s) => s.id === id) || {}).text || id).join(' / ');
}

function shotCard(shot, detail) {
  const asset = (detail.assets || {})[shot.shot_id] || {};
  const cover = asset.keyframe ? `background-image:url('${thumbUrl(asset.keyframe, 480)}')` : '';
  const line = narrationText(detail, shot.narration_ids);
  return `<button class="shot-card ${shot.shot_id === state.selected ? 'active' : ''}" data-shot="${esc(shot.shot_id)}">
    <div class="shot-thumb" style="${cover}">${asset.keyframe ? '' : '待生成关键帧'}</div>
    <div class="shot-body">
      <div class="row" style="justify-content:space-between;align-items:center">
        <span class="shot-id">${esc(shot.shot_id)}</span>
        ${statusBadge(shot.generation && shot.generation.status)}
      </div>
      <div class="shot-sub">${esc(shot.shot_size)} · ${esc(shot.camera.move)} · ${shot.duration_seconds}s</div>
      <div class="shot-line">${esc(line)}</div>
    </div>
  </button>`;
}

function tableView(shots, detail) {
  const rows = shots.map((shot) => `<tr data-shot="${esc(shot.shot_id)}" class="${shot.shot_id === state.selected ? 'active' : ''}">
    <td class="mono">${esc(shot.shot_id)}</td>
    <td>${esc(shot.scene_id)}</td>
    <td>${esc(shot.shot_size)}</td>
    <td>${esc(shot.camera.move)}</td>
    <td class="mono">${shot.camera.lens_mm}mm</td>
    <td class="mono">${shot.duration_seconds}s</td>
    <td>${esc(narrationText(detail, shot.narration_ids))}</td>
    <td>${statusBadge(shot.generation && shot.generation.status)}</td>
  </tr>`).join('');
  return `<table class="film-table"><thead><tr>
    <th>镜头</th><th>场景</th><th>景别</th><th>运镜</th><th>镜头</th><th>时长</th><th>旁白</th><th>状态</th>
  </tr></thead><tbody>${rows}</tbody></table>`;
}

function leftPanel(detail) {
  const shots = detail.storyboard.shots;
  const scenes = [...new Set(shots.map((shot) => shot.scene_id))];
  const narration = (detail.narration && detail.narration.segments) || [];
  return `<div class="film-panel">
    <h3>场景</h3>
    ${scenes.map((scene) => {
      const ids = shots.filter((shot) => shot.scene_id === scene).map((shot) => shot.shot_id);
      return `<div class="side-item"><strong>${esc(scene)}</strong><div class="shot-sub">${ids.join(' · ')}</div></div>`;
    }).join('')}
    <h3 style="margin-top:14px">旁白</h3>
    ${narration.map((seg) => `<div class="side-item"><span class="mono">${esc(seg.id)}</span> ${esc(seg.text)}</div>`).join('')}
  </div>`;
}

function inspector(shot) {
  if (!shot) return `<div class="film-panel inspector"><h3>镜头属性</h3><div class="muted">选择一个镜头</div></div>`;
  const camera = shot.camera || {};
  const layers = shot.layers || {};
  const motion = shot.motion || {};
  const options = (list, value) => list.map((item) => `<option value="${item}" ${item === value ? 'selected' : ''}>${item}</option>`).join('');
  return `<div class="film-panel inspector">
    <h3>镜头属性 · ${esc(shot.shot_id)}</h3>
    <label>场景</label><input data-field="scene_id" value="${esc(shot.scene_id)}">
    <div class="row2">
      <div><label>时长（秒）</label><input data-field="duration_seconds" type="number" step="0.5" min="0.5" value="${shot.duration_seconds}"></div>
      <div><label>景别</label><select data-field="shot_size">${options(SIZES, shot.shot_size)}</select></div>
    </div>
    <div class="row2">
      <div><label>运镜</label><select data-field="camera_move">${options(MOVES, camera.move)}</select></div>
      <div><label>角度</label><input data-field="camera_angle" value="${esc(camera.angle || 'eye')}"></div>
    </div>
    <div class="row2">
      <div><label>焦距 mm</label><input data-field="lens_mm" type="number" value="${camera.lens_mm || 35}"></div>
      <div><label>景深</label><select data-field="dof">${options(DOFS, camera.dof || 'deep')}</select></div>
    </div>
    <label>前景</label><input data-field="foreground" value="${esc(layers.foreground || '')}">
    <label>中景</label><input data-field="midground" value="${esc(layers.midground || '')}">
    <label>背景</label><input data-field="background" value="${esc(layers.background || '')}">
    <label>主运动</label><input data-field="motion_primary" value="${esc(motion.primary || '')}">
    <label>次要运动（逗号分隔，最多 2 个）</label><input data-field="secondary" value="${esc((motion.secondary || []).join(', '))}">
    <label><input type="checkbox" data-field="character_in_frame" ${shot.character_in_frame ? 'checked' : ''}> 画面中有人物</label>
    <label>关键帧备注</label><textarea data-field="keyframe_note" rows="2">${esc(shot.keyframe_note || '')}</textarea>
    <div class="actions" style="margin-top:12px">
      <button class="btn btn-primary" id="save-shot">保存镜头</button>
    </div>
  </div>`;
}

function readInspector(root) {
  const value = (name) => root.querySelector(`[data-field="${name}"]`)?.value ?? '';
  return {
    scene_id: value('scene_id').trim(),
    duration_seconds: Number(value('duration_seconds')),
    shot_size: value('shot_size'),
    camera_move: value('camera_move'),
    camera_angle: value('camera_angle').trim() || 'eye',
    lens_mm: Number(value('lens_mm')),
    dof: value('dof'),
    foreground: value('foreground').trim(),
    midground: value('midground').trim(),
    background: value('background').trim(),
    motion_primary: value('motion_primary').trim(),
    secondary: value('secondary').split(',').map((item) => item.trim()).filter(Boolean),
    character_in_frame: root.querySelector('[data-field="character_in_frame"]')?.checked ?? false,
    keyframe_note: value('keyframe_note').trim(),
  };
}

function renderBody(view, ctx) {
  const detail = state.detail;
  if (!detail || !detail.storyboard) {
    view.innerHTML = pageHead('剧本与分镜', '') + emptyState('还没有分镜', '该项目没有 storyboard.json');
    return;
  }
  const shots = detail.storyboard.shots;
  const shot = shots.find((item) => item.shot_id === state.selected) || null;
  const center = state.mode === 'cards'
    ? `<div class="shot-grid">${shots.map((item) => shotCard(item, detail)).join('')}</div>`
    : tableView(shots, detail);
  const title = (detail.meta && detail.meta.title) || state.projectId;
  view.innerHTML = pageHead(
    `${title} · 剧本与分镜`,
    `${esc(detail.meta && detail.meta.aspect_ratio || '9:16')} · ${esc(state.projectId)} · ${shots.length} 个镜头`,
    `<span class="seg"><button data-mode="cards" class="${state.mode === 'cards' ? 'on' : ''}">分镜卡片</button><button data-mode="table" class="${state.mode === 'table' ? 'on' : ''}">镜头表</button></span>`,
  ) + `<div class="film-layout">
    ${leftPanel(detail)}
    <div>${center}</div>
    ${inspector(shot)}
  </div>`;

  view.querySelectorAll('[data-shot]').forEach((el) => {
    el.addEventListener('click', () => {
      state.selected = el.dataset.shot;
      renderBody(view, ctx);
    });
  });
  view.querySelectorAll('[data-mode]').forEach((el) => {
    el.addEventListener('click', () => { state.mode = el.dataset.mode; renderBody(view, ctx); });
  });
  view.querySelector('#save-shot')?.addEventListener('click', async () => {
    const inspectorEl = view.querySelector('.inspector');
    try {
      await patch(`/api/film/projects/${encodeURIComponent(state.projectId)}/storyboard/${encodeURIComponent(state.selected)}`, readInspector(inspectorEl));
      toast('镜头已保存', 'ok');
      await ctx.refresh();
    } catch (err) {
      toast(err.message || '保存失败', 'bad');
    }
  });
}

export default {
  title: '剧本与分镜',
  async render(view, params, ctx) {
    view.innerHTML = loading('读取项目…');
    try {
      let projectId = params.project;
      if (!projectId) {
        const list = await get('/api/film/projects');
        projectId = (list.projects || [])[0]?.project_id;
      }
      if (!projectId) {
        view.innerHTML = pageHead('剧本与分镜', '') + emptyState('暂无作品', '先去项目中心创建或准备项目数据');
        return;
      }
      state.projectId = projectId;
      state.detail = await get(`/api/film/projects/${encodeURIComponent(projectId)}`);
      const shots = (state.detail.storyboard && state.detail.storyboard.shots) || [];
      if (!state.selected || !shots.some((shot) => shot.shot_id === state.selected)) {
        state.selected = shots[0]?.shot_id || null;
      }
      renderBody(view, ctx);
    } catch (err) {
      view.innerHTML = errorBox(err);
    }
  },
};

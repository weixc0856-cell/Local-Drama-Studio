import { get, post, patch } from './api.js';
import { esc, modal, toast, errorBox, closeModal } from './ui.js';

export async function loadStyleOptions() {
  try {
    const data = await get('/api/styles');
    return data.styles || [];
  } catch {
    return [];
  }
}

function styleOptions(styles, selected) {
  return `<option value="">（不绑定）</option>` + styles.map((s) =>
    `<option value="${esc(s.id)}" ${s.id === selected ? 'selected' : ''}>${esc(s.name)} · ${esc(s.aspect_ratio)}</option>`
  ).join('');
}

export function formDirtyGuard(root, selector) {
  const form = root.querySelector(selector);
  if (!form) return null;
  const snapshot = () => new FormData(form);
  const initial = new URLSearchParams([...snapshot().entries()].map(([k, v]) => [k, String(v)])).toString();
  return () => {
    const current = new URLSearchParams([...snapshot().entries()].map(([k, v]) => [k, String(v)])).toString();
    if (current === initial) return true;
    return window.confirm('有未保存的修改，确定放弃吗？');
  };
}

export function openProjectModal({ project = null, onDone } = {}) {
  const editing = Boolean(project);
  const v = (key, fallback = '') => esc(project?.[key] ?? fallback);
  const ratio = project?.aspect_ratio || '9:16';
  modal(editing ? '编辑内容项目' : '新建内容项目', `
    <form class="form" id="project-form">
      <div class="field"><label>项目名称 *</label>
        <input class="input" name="name" maxlength="120" required autofocus value="${v('name')}"
          placeholder="例如：东方意境系列"></div>
      <div class="field"><label>简介</label>
        <textarea class="textarea" name="description" style="min-height:64px"
          placeholder="这个系列做什么内容">${v('description')}</textarea></div>
      <div class="form-row">
        <div class="field"><label>内容定位</label>
          <input class="input" name="positioning" value="${v('positioning')}"
            placeholder="例如：东方山水意境 / 9:16 竖屏"></div>
        <div class="field"><label>目标平台（逗号分隔）</label>
          <input class="input" name="target_platforms" value="${esc((project?.target_platforms || []).join(', '))}"
            placeholder="抖音, 小红书"></div>
      </div>
      <div class="form-row">
        <div class="field"><label>视频比例</label>
          <select class="input" name="aspect_ratio">
            ${['9:16', '16:9', '1:1'].map((r) => `<option ${r === ratio ? 'selected' : ''}>${r}</option>`).join('')}
          </select></div>
        <div class="field"><label>默认声音</label>
          <input class="input" name="default_voice" value="${v('default_voice')}" placeholder="例如：中文女"></div>
      </div>
    </form>`, {
    footer: `<button class="btn btn-ghost" data-close>取消</button>
             <button class="btn btn-primary" id="project-save">${editing ? '保存修改' : '创建项目'}</button>`,
    guardClose: (root) => (formDirtyGuard(root, '#project-form')?.() ?? true),
    onMount(root) {
      root.querySelector('#project-save').addEventListener('click', async () => {
        const form = root.querySelector('#project-form');
        if (!form.reportValidity()) return;
        const fd = new FormData(form);
        const body = {
          name: (fd.get('name') || '').trim(),
          description: fd.get('description') || '',
          positioning: fd.get('positioning') || '',
          default_voice: fd.get('default_voice') || '',
          aspect_ratio: fd.get('aspect_ratio') || '9:16',
          target_platforms: String(fd.get('target_platforms') || '')
            .split(',').map((s) => s.trim()).filter(Boolean),
        };
        try {
          if (editing) await patch(`/api/projects/${encodeURIComponent(project.id)}`, body);
          else await post('/api/projects', body);
          closeModal();
          toast(editing ? '项目已保存' : '项目已创建', 'ok');
          if (onDone) onDone();
        } catch (err) {
          toast(err.message, 'bad', 6000);
        }
      });
    },
  });
}

export async function openEpisodeModal({ projects, projectId, onDone } = {}) {
  const styles = await loadStyleOptions();
  const projectOpts = projects.map((p) =>
    `<option value="${esc(p.id)}" ${p.id === projectId ? 'selected' : ''}>${esc(p.name)}</option>`
  ).join('');
  modal('新建期数', `
    <form class="form" id="episode-form">
      <div class="form-row">
        <div class="field"><label>所属项目 *</label>
          <select class="input" name="project_id" required>${projectOpts}</select></div>
        <div class="field"><label>期数编号 *</label>
          <input class="input" name="number" type="number" min="1" value="1" required></div>
      </div>
      <div class="field"><label>标题 *</label>
        <input class="input" name="title" maxlength="160" required placeholder="例如：第 1 期 · 春日短句"></div>
      <div class="form-row">
        <div class="field"><label>生产类型</label>
          <select class="input" name="track">
            <option value="video">video（已有素材，可合成）</option>
            <option value="literary">literary（文献/分析阶段）</option>
          </select></div>
        <div class="field"><label>视觉风格</label>
          <select class="input" name="style_id">${styleOptions(styles)}</select></div>
      </div>
      <div class="field"><label>真实产物目录（可选）</label>
        <input class="input mono" name="artifact_root" placeholder="experiments/r3b 或 literary_intelligence/corpus/...">
        <span class="hint">必须是仓库内已存在的目录；工作台不会创建或移动素材。留空则所有步骤显示“产物目录缺失”。</span></div>
      <div class="field"><label>备注</label>
        <textarea class="textarea" name="notes" style="min-height:60px"></textarea></div>
    </form>`, {
    footer: `<button class="btn btn-ghost" data-close>取消</button>
             <button class="btn btn-primary" id="episode-save">创建期数</button>`,
    guardClose: (root) => (formDirtyGuard(root, '#episode-form')?.() ?? true),
    onMount(root) {
      root.querySelector('#episode-save').addEventListener('click', async () => {
        const form = root.querySelector('#episode-form');
        if (!form.reportValidity()) return;
        const fd = new FormData(form);
        const body = {
          project_id: fd.get('project_id'),
          number: Number(fd.get('number')),
          title: (fd.get('title') || '').trim(),
          track: fd.get('track'),
          style_id: fd.get('style_id') || null,
          artifact_root: (fd.get('artifact_root') || '').trim() || null,
          notes: fd.get('notes') || '',
        };
        try {
          const created = await post('/api/episodes', body);
          closeModal();
          toast('期数已创建', 'ok');
          if (onDone) onDone(created);
        } catch (err) {
          toast(err.message, 'bad', 6000);
        }
      });
    },
  });
}

export async function runTask(kind, params, { onStarted } = {}) {
  try {
    const task = await post('/api/tasks', { kind, params });
    if (task.status === 'BLOCKED') {
      toast(task.error || '前置条件不满足', 'warn', 7000);
    } else {
      toast(`任务已启动：${task.id}`, 'ok');
    }
    if (onStarted) onStarted(task);
    return task;
  } catch (err) {
    toast(err.message, 'bad', 7000);
    return null;
  }
}

export function showError(err) {
  return errorBox(err);
}

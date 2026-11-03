import { get, post, patch } from '../api.js';
import {
  esc, modal, toast, closeModal, loading, errorBox, emptyState, pageHead,
} from '../ui.js';
import { formDirtyGuard } from '../forms.js';

function paletteSwatches(palette) {
  const entries = Object.entries(palette || {});
  if (!entries.length) return '<span class="muted tiny">无色板</span>';
  return `<div class="swatches">${entries.slice(0, 8).map(([name, hex]) =>
    `<div class="swatch"><i style="background:${esc(hex)}"></i><span>${esc(name)}</span></div>`).join('')}</div>`;
}

function styleForm(style = {}) {
  const value = (key, fallback = '') => esc(style[key] ?? fallback);
  return `<form class="form" id="style-form">
    <div class="form-row">
      <div class="field"><label>风格名称 *</label><input class="input" name="name" required value="${value('name')}"></div>
      <div class="field"><label>画面比例</label><input class="input" name="aspect_ratio" value="${value('aspect_ratio', '9:16')}"></div>
    </div>
    <div class="field"><label>描述</label><textarea class="textarea" name="description" style="min-height:56px">${value('description')}</textarea></div>
    <div class="field"><label>视觉语言</label><textarea class="textarea" name="visual_language" style="min-height:72px">${value('visual_language')}</textarea></div>
    <div class="form-row">
      <div class="field"><label>光照</label><input class="input" name="lighting" value="${value('lighting')}"></div>
      <div class="field"><label>镜头语言</label><input class="input" name="camera_language" value="${value('camera_language')}"></div>
    </div>
    <div class="field"><label>构图</label><input class="input" name="composition" value="${value('composition')}"></div>
    <div class="form-row">
      <div class="field"><label>人物设计</label><input class="input" name="character_design" value="${value('character_design')}"></div>
      <div class="field"><label>环境设计</label><input class="input" name="environment_design" value="${value('environment_design')}"></div>
    </div>
    <div class="field"><label>正向提示词</label><textarea class="textarea" name="positive_prompt" style="min-height:96px">${value('positive_prompt')}</textarea></div>
    <div class="field"><label>负面提示词</label><textarea class="textarea" name="negative_prompt" style="min-height:64px">${value('negative_prompt')}</textarea></div>
    <div class="form-row">
      <div class="field"><label>色板（JSON：名称 → HEX）</label>
        <textarea class="textarea" name="color_palette">${esc(JSON.stringify(style.color_palette || {}, null, 2))}</textarea></div>
      <div class="field"><label>适用内容类型（逗号分隔）</label>
        <input class="input" name="applicable_content_types" value="${esc((style.applicable_content_types || []).join(', '))}">
        <label class="hint">参考资产（每行一个仓库相对路径）</label>
        <textarea class="textarea" name="reference_assets">${esc((style.reference_assets || []).join('\n'))}</textarea>
      </div>
    </div>
  </form>`;
}

function collect(root) {
  const fd = new FormData(root.querySelector('#style-form'));
  let palette = {};
  try {
    palette = JSON.parse(fd.get('color_palette') || '{}');
    if (typeof palette !== 'object' || Array.isArray(palette)) throw new Error('色板必须是对象');
  } catch (err) {
    throw new Error(`色板 JSON 无效：${err.message}`);
  }
  return {
    name: (fd.get('name') || '').trim(),
    aspect_ratio: fd.get('aspect_ratio') || '9:16',
    description: fd.get('description') || '',
    visual_language: fd.get('visual_language') || '',
    lighting: fd.get('lighting') || '',
    camera_language: fd.get('camera_language') || '',
    composition: fd.get('composition') || '',
    character_design: fd.get('character_design') || '',
    environment_design: fd.get('environment_design') || '',
    positive_prompt: fd.get('positive_prompt') || '',
    negative_prompt: fd.get('negative_prompt') || '',
    color_palette: palette,
    applicable_content_types: String(fd.get('applicable_content_types') || '')
      .split(',').map((s) => s.trim()).filter(Boolean),
    reference_assets: String(fd.get('reference_assets') || '')
      .split('\n').map((s) => s.trim()).filter(Boolean),
  };
}

export default {
  async render(view) {
    const page = this;
    let data;
    try { data = await get('/api/styles'); }
    catch (err) { view.innerHTML = errorBox(err); return; }
    const styles = data.styles || [];
    view.innerHTML = `
      ${pageHead('风格管理', '风格是可编辑的配置，不是生产状态。修改全局预设不会改变已绑定期数的快照。',
        '<button class="btn btn-primary" id="new-style">新建风格</button>')}
      ${styles.length ? `<div class="grid grid-2">${styles.map((s) => `
        <div class="panel">
          <div class="panel-body col" style="gap:8px">
            <div class="row" style="justify-content:space-between;align-items:flex-start">
              <div><div class="card-title">${esc(s.name)}</div>
                <div class="tiny muted mt8">${esc(s.description || '')}</div></div>
              <span class="tag">${esc(s.aspect_ratio)}</span>
            </div>
            ${paletteSwatches(s.color_palette)}
            <div class="tiny muted">${esc(s.visual_language || '').slice(0, 160)}</div>
            <div class="row wrap" style="gap:5px">
              ${(s.applicable_content_types || []).map((t) => `<span class="tag">${esc(t)}</span>`).join('')}
              ${(s.source_files || []).length ? `<span class="tag">证据文件 ${s.source_files.length}</span>` : ''}
            </div>
            <div class="row" style="gap:8px">
              <button class="btn btn-sm" data-edit="${esc(s.id)}">编辑</button>
              <a class="btn btn-sm btn-ghost" href="#/episodes">应用到某期</a>
            </div>
          </div>
        </div>`).join('')}</div>`
        : emptyState('还没有风格预设', '创建一个风格，或在期数中绑定已有预设。')}`;

    const openEditor = (style) => {
      modal(style ? `编辑风格 · ${style.name}` : '新建风格', styleForm(style || {}), {
        wide: true,
        footer: `<button class="btn btn-ghost" data-close>取消</button>
          <button class="btn btn-primary" id="save-style">保存</button>`,
        guardClose: (root) => (formDirtyGuard(root, '#style-form')?.() ?? true),
        onMount(root) {
          root.querySelector('#save-style').addEventListener('click', async () => {
            try {
              const body = collect(root);
              if (!body.name) { toast('风格名称不能为空', 'warn'); return; }
              if (style) await patch(`/api/styles/${encodeURIComponent(style.id)}`, body);
              else await post('/api/styles', body);
              closeModal();
              toast('已保存', 'ok');
              page.render(view);
            } catch (err) { toast(err.message, 'bad', 6000); }
          });
        },
      });
    };

    view.querySelector('#new-style')?.addEventListener('click', () => openEditor(null));
    view.querySelectorAll('[data-edit]').forEach((btn) => {
      btn.addEventListener('click', () => openEditor(styles.find((s) => s.id === btn.dataset.edit)));
    });
  },
};

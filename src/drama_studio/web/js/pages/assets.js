import { get, thumbUrl } from '../api.js';
import {
  esc, fmtBytes, fmtTime, loading, errorBox, emptyState, pageHead, toast,
} from '../ui.js';
import { openPreview } from '../preview.js';

const TYPES = [
  ['', '全部'], ['image', '图片'], ['video', '视频'], ['audio', '音频'],
  ['subtitle', '字幕'], ['text', '文本'], ['json', 'JSON'], ['font', '字体'], ['log', '日志'],
];

let localState = { type: '', query: '', includeTemp: false, items: [] };

function matches(item) {
  if (localState.type && item.type !== localState.type) return false;
  if (!localState.includeTemp && item.temporary) return false;
  if (localState.query) {
    const q = localState.query.toLowerCase();
    if (!item.path.toLowerCase().includes(q)) return false;
  }
  return true;
}

function grid(items) {
  if (!items.length) return emptyState('没有匹配的素材', '调整类型/关键词，或勾选“包含实验临时文件”。');
  return `<div class="asset-grid">${items.map((item) => `
    <div class="asset" data-path="${esc(item.path)}">
      ${item.type === 'image' || item.type === 'video'
        ? `<div class="asset-thumb" style="background-image:url('${thumbUrl(item.path, 360)}')">
            ${item.referenced ? '<span class="ref-flag">引用</span>' : ''}</div>`
        : `<div class="asset-thumb"><span style="font-size:18px;color:var(--faint)">${
            { audio: '♪', subtitle: '字', text: 'T', json: '{ }', font: 'Aa', log: '⋯' }[item.type] || '·'}</span>
            ${item.referenced ? '<span class="ref-flag">引用</span>' : ''}</div>`}
      <div class="asset-body">
        <div class="asset-name" title="${esc(item.path)}">${esc(item.name)}</div>
        <div class="asset-meta">
          <span>${esc(item.type)}</span><span>${esc(fmtBytes(item.size))}</span>
          <span>· ${esc(item.category || '')}</span>
          ${item.episode_id ? `<span>· ${esc(item.episode_id)}</span>` : ''}
          ${item.temporary ? '<span>· 临时</span>' : ''}
        </div>
      </div>
    </div>`).join('')}</div>`;
}

export default {
  async render(view, params) {
    let data;
    try {
      data = await get(`/api/assets?include_temporary=${localState.includeTemp ? 'true' : 'false'}&limit=1200`);
    } catch (err) { view.innerHTML = errorBox(err); return; }
    localState.items = data.items || [];
    localState.formalTotal = data.formal_total || 0;
    localState.tempTotal = data.temporary_total || 0;
    localState.truncated = Boolean(data.truncated);
    localState.type = params.type || localState.type || '';
    localState.query = params.q || '';

    const draw = () => {
      const items = localState.items.filter(matches);
      view.querySelector('#asset-grid').innerHTML = grid(items);
      const total = localState.includeTemp
        ? (localState.formalTotal || 0) + (localState.tempTotal || 0)
        : (localState.formalTotal || 0);
      const note = localState.truncated ? '（已达显示上限）' : '';
      view.querySelector('#asset-count').textContent =
        `${items.length} 个匹配 · 仓库内共 ${total} 个可扫描文件${note}`;
      view.querySelectorAll('[data-path]').forEach((el) => {
        el.addEventListener('click', () => {
          const item = localState.items.find((i) => i.path === el.dataset.path);
          if (item) openPreview(item);
        });
      });
    };

    view.innerHTML = `
      ${pageHead('素材库', '按真实文件扫描。实验临时文件默认隐藏；“引用”表示被当前生产 manifest 或分镜引用。')}
      <div class="panel mb16">
        <div class="panel-body">
          <div class="row wrap" style="justify-content:space-between">
            <div class="chips" id="type-chips">
              ${TYPES.map(([value, label]) => `<button class="chip ${localState.type === value ? 'active' : ''}"
                data-type="${value}">${label}</button>`).join('')}
            </div>
            <div class="row">
              <input class="input" id="asset-search" placeholder="搜索文件名 / 路径" value="${esc(localState.query)}"
                style="width:260px">
              <label class="row small muted" style="gap:6px;cursor:pointer">
                <input type="checkbox" id="include-temp" ${localState.includeTemp ? 'checked' : ''}>
                包含实验临时文件（${data.temporary_total || 0}）
              </label>
            </div>
          </div>
          <div class="tiny muted mt8" id="asset-count"></div>
        </div>
      </div>
      <div id="asset-grid"></div>`;

    draw();

    view.querySelectorAll('[data-type]').forEach((btn) => {
      btn.addEventListener('click', () => {
        localState.type = btn.dataset.type;
        view.querySelectorAll('[data-type]').forEach((b) => b.classList.toggle('active', b === btn));
        draw();
      });
    });
    let debounce = null;
    view.querySelector('#asset-search').addEventListener('input', (event) => {
      clearTimeout(debounce);
      debounce = setTimeout(() => { localState.query = event.target.value.trim(); draw(); }, 200);
    });
    view.querySelector('#include-temp').addEventListener('change', async (event) => {
      localState.includeTemp = event.target.checked;
      try {
        const fresh = await get(`/api/assets?include_temporary=${localState.includeTemp ? 'true' : 'false'}&limit=1200`);
        localState.items = fresh.items || [];
        localState.formalTotal = fresh.formal_total || 0;
        localState.tempTotal = fresh.temporary_total || 0;
        localState.truncated = Boolean(fresh.truncated);
        draw();
      } catch (err) { toast(err.message, 'bad'); }
    });
  },
};

import { mediaUrl, thumbUrl } from './api.js';
import { esc, modal, fmtBytes, fmtTime } from './ui.js';

const TEXT_TYPES = new Set(['text', 'json', 'subtitle', 'other']);

export function openPreview(item) {
  const type = item.type;
  let body = '';
  if (type === 'image') {
    body = `<img src="${mediaUrl(item.path)}" alt="${esc(item.name)}"
      style="max-width:100%;max-height:66vh;display:block;margin:0 auto;border-radius:6px;border:1px solid var(--border)">`;
  } else if (type === 'video') {
    body = `<video class="player" controls preload="metadata" src="${mediaUrl(item.path)}"></video>`;
  } else if (type === 'audio') {
    body = `<audio class="audio-inline" controls preload="metadata" src="${mediaUrl(item.path)}"></audio>`;
  } else if (TEXT_TYPES.has(type)) {
    body = `<div class="log-view" id="preview-text"><span class="spinner"></span></div>`;
  } else {
    body = `<div class="muted">该类型没有内嵌预览。</div>`;
  }
  const meta = `<dl class="kv mt16">
    <dt>路径</dt><dd class="mono">${esc(item.path)}</dd>
    <dt>类型</dt><dd>${esc(type)}</dd>
    <dt>大小</dt><dd>${esc(fmtBytes(item.size))}</dd>
    <dt>修改时间</dt><dd>${esc(fmtTime(item.mtime, { withYear: true }))}</dd>
    <dt>生产引用</dt><dd>${item.referenced ? '是' : '否'}</dd>
    ${item.temporary ? '<dt>标记</dt><dd>实验临时文件</dd>' : ''}
  </dl>`;
  modal(item.name, body + meta, {
    wide: type === 'video' || type === 'image',
    onMount(root) {
      const target = root.querySelector('#preview-text');
      if (!target) return;
      fetch(mediaUrl(item.path))
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.text();
        })
        .then((text) => {
          target.textContent = text.slice(0, 200000) || '（空文件）';
        })
        .catch((err) => { target.textContent = `无法读取：${err.message}`; });
      if (!root.querySelector('img') && type !== 'video') return;
    },
  });
}

export function previewThumb(item) {
  if (item.thumb || item.type === 'image' || item.type === 'video') {
    return `<div class="asset-thumb" style="background-image:url('${thumbUrl(item.path, 360)}')">`
      + `${item.referenced ? '<span class="ref-flag">引用</span>' : ''}</div>`;
  }
  const iconChar = { audio: '♪', subtitle: '字', text: 'T', json: '{ }', font: 'Aa', log: '⋯' }[item.type] || '·';
  return `<div class="asset-thumb"><span style="font-size:20px;color:var(--faint)">${iconChar}</span>
    ${item.referenced ? '<span class="ref-flag">引用</span>' : ''}</div>`;
}

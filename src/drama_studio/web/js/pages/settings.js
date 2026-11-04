import { get, post } from '../api.js';
import {
  esc, fmtTime, loading, errorBox, pageHead, statusBadge, rawStatusBadge, toast,
} from '../ui.js';

function envTable(env) {
  const services = (env.services || []).map((s) => `<tr>
    <td class="title-cell">${esc(s.name)}</td>
    <td>${rawStatusBadge(s.status)}</td>
    <td class="mono-cell">${esc(s.url)}</td>
    <td class="muted small">${esc(s.detail)}</td>
  </tr>`).join('');
  const tools = (env.tools || []).map((t) => `<tr>
    <td class="title-cell">${esc(t.name)}</td>
    <td>${rawStatusBadge(t.status)}</td>
    <td class="mono-cell">${esc(t.path || '—')}</td>
    <td class="muted small">${esc(t.detail || '')}</td>
  </tr>`).join('');
  const disks = (env.disk || []).map((d) => `<tr>
    <td class="title-cell">${esc(d.name)}</td>
    <td>${rawStatusBadge(d.status)}</td>
    <td class="mono-cell">${esc(d.path)}</td>
    <td class="muted small">${d.free_gib != null ? `${d.free_gib} / ${d.total_gib} GiB 可用` : esc(d.detail || '')}</td>
  </tr>`).join('');
  return `<div class="table-wrap"><table class="table">
    <thead><tr><th>服务</th><th>状态</th><th>地址</th><th>详情</th></tr></thead>
    <tbody>${services}</tbody></table></div>
    <div class="table-wrap mt16"><table class="table">
    <thead><tr><th>工具</th><th>状态</th><th>路径</th><th>版本</th></tr></thead>
    <tbody>${tools}</tbody></table></div>
    <div class="table-wrap mt16"><table class="table">
    <thead><tr><th>磁盘</th><th>状态</th><th>路径</th><th>空间</th></tr></thead>
    <tbody>${disks}</tbody></table></div>`;
}

export default {
  async render(view) {
    let env;
    let kinds;
    let health;
    try {
      [env, kinds, health] = await Promise.all([
        get('/api/env'), get('/api/tasks/kinds'), get('/api/health'),
      ]);
    } catch (err) { view.innerHTML = errorBox(err); return; }

    const gpu = env.gpu || {};
    view.innerHTML = `
      ${pageHead('系统设置', '只展示可以可靠读取的状态。无法探测的项目显示 UNKNOWN，不以配置或设备管理器推测。',
        `<button class="btn" id="force-probe">强制重新探测</button>
         <button class="btn btn-primary" id="run-doctor">运行 doctor</button>`)}

      <div class="split">
        <div class="col">
          <div class="panel">
            <div class="panel-head"><span class="panel-title">服务与工具</span>
              <span class="panel-sub">探测于 ${esc(fmtTime(env.checked_at))}</span></div>
            <div class="panel-body">${envTable(env)}</div>
          </div>

          <div class="panel">
            <div class="panel-head"><span class="panel-title">任务注册表</span>
              <span class="panel-sub">${(kinds.kinds || []).filter((k) => k.enabled).length} 个可用</span></div>
            <div class="panel-body tight">
              <div class="table-wrap"><table class="table">
                <thead><tr><th>类型</th><th>名称</th><th>状态</th><th>成本</th><th>安全约束</th></tr></thead>
                <tbody>${(kinds.kinds || []).map((k) => `<tr>
                  <td class="mono-cell nowrap">${esc(k.key)}</td>
                  <td class="title-cell">${esc(k.label)}</td>
                  <td>${k.enabled ? '<span class="badge b-verified">可用</span>'
                    : '<span class="badge b-blocked">不可用</span>'}</td>
                  <td class="muted small">${esc(k.cost)}</td>
                  <td class="muted small">${esc(k.enabled ? k.safety : k.blocked_reason || '')}</td>
                </tr>`).join('')}</tbody></table></div>
            </div>
          </div>
        </div>

        <div class="col">
          <div class="panel">
            <div class="panel-head"><span class="panel-title">运行环境</span></div>
            <div class="panel-body">
              <dl class="kv">
                <dt>仓库根</dt><dd class="mono">${esc(health.root)}</dd>
                <dt>版本</dt><dd class="mono">${esc(health.version)}</dd>
                <dt>LLM</dt><dd class="mono">${esc(env.llm_model || '—')}</dd>
                <dt>ComfyUI</dt><dd class="mono">${esc(env.comfyui_url || '—')}</dd>
                <dt>CosyVoice 默认模式</dt><dd class="mono">${esc(env.tts_mode || '—')} · ${esc(env.tts_default_speaker || '—')}</dd>
                <dt>GPU / XPU</dt><dd>${gpu.name
                  ? `${esc(gpu.name)} · ${esc(gpu.vram_free_gib)} / ${esc(gpu.vram_total_gib)} GiB`
                  : esc(gpu.detail || 'UNKNOWN')}</dd>
              </dl>
              <div class="note mt12">${esc(gpu.source ? `来源：${gpu.source}` : 'ComfyUI 未运行时无法读取显存；本页不会估算。')}</div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-head"><span class="panel-title">数据边界</span></div>
            <div class="panel-body col" style="gap:8px">
              <div class="note">工作台状态：<span class="mono">projects/workspace.db</span>（项目、期数、风格、任务记录）。</div>
              <div class="note">产物状态：每次请求从 <span class="mono">assets/</span>、<span class="mono">experiments/</span>、
                <span class="mono">literary_intelligence/</span> 的真实文件派生，不写回。</div>
              <div class="note">任务日志：<span class="mono">logs/workspace/tasks/</span>；缩略图缓存：<span class="mono">logs/workspace/thumbs/</span>。</div>
              <div class="note">LLM 只使用 8080；ComfyUI 8188；CosyVoice 50000。工作台不创建第二个端口。</div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-head"><span class="panel-title">已知限制</span></div>
            <div class="panel-body col" style="gap:8px">
              <div class="note">内容与分镜当前只读：ContentPackage → R3 输入 Adapter 尚未实现。</div>
              <div class="note">TTS 任务未启用：scripts/r3_tts.py 仍硬编码 experiments/r3b。</div>
              <div class="note">人工验收没有写入入口；期数页会显示 NOT_RUN。</div>
            </div>
          </div>
        </div>
      </div>`;

    view.querySelector('#force-probe').addEventListener('click', async () => {
      try { await get('/api/env?force=true'); toast('已重新探测', 'ok'); this.render(view); }
      catch (err) { toast(err.message, 'bad'); }
    });
    view.querySelector('#run-doctor').addEventListener('click', async () => {
      try {
        const task = await post('/api/tasks', { kind: 'doctor.run', params: {} });
        toast(`诊断任务：${task.id}`, 'ok');
        location.hash = `#/tasks?id=${encodeURIComponent(task.id)}`;
      } catch (err) { toast(err.message, 'bad', 7000); }
    });
  },
};

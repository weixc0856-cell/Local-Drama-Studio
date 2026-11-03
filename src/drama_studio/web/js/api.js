export class ApiError extends Error {
  constructor(message, code, detail, status) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.detail = detail;
    this.status = status;
  }
}

async function request(path, options = {}) {
  const init = { ...options, headers: { ...(options.headers || {}) } };
  if (init.body && typeof init.body !== 'string') {
    init.body = JSON.stringify(init.body);
    init.headers['Content-Type'] = 'application/json';
  }
  let res;
  try {
    res = await fetch(path, init);
  } catch (err) {
    throw new ApiError(`无法连接本地工作台：${err.message}`, 'network_error', null, 0);
  }
  const type = res.headers.get('content-type') || '';
  let data = null;
  if (type.includes('application/json')) {
    data = await res.json().catch(() => null);
  } else {
    data = await res.text().catch(() => '');
  }
  if (!res.ok) {
    const err = data && data.error ? data.error : {};
    throw new ApiError(err.message || `请求失败（HTTP ${res.status}）`, err.code || 'http_error', err.detail, res.status);
  }
  return data;
}

export const get = (path) => request(path);
export const post = (path, body) => request(path, { method: 'POST', body: body ?? {} });
export const patch = (path, body) => request(path, { method: 'PATCH', body: body ?? {} });

export const mediaUrl = (path) => `/api/media/${encodePath(path)}`;
export const thumbUrl = (path, width = 480) => `/api/thumb/${encodePath(path)}?width=${width}`;

export function encodePath(path) {
  return String(path || '')
    .split('/')
    .map((part) => encodeURIComponent(part))
    .join('/');
}

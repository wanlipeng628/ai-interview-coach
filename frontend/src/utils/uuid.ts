/**
 * 生成 UUID v4。
 * crypto.randomUUID 仅在安全上下文（HTTPS / localhost）可用；
 * 生产环境走 http://公网IP 访问时不可用，回退到 Math.random 实现，避免运行时抛错。
 */
export function uuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

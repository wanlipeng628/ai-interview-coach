import { existsSync } from 'node:fs'
import { registerHooks } from 'node:module'
import { dirname, resolve as resolvePath } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

// 测试直跑 TS 源码时没有 Vite 的解析器：这里补上 `@/` 别名与无扩展名的相对引用
const srcDir = resolvePath(dirname(fileURLToPath(import.meta.url)), '../../src')

const resolveCandidate = (base: string) => {
  for (const candidate of [base, `${base}.ts`, `${base}.tsx`, `${base}/index.ts`]) {
    if (existsSync(candidate)) {
      return { url: pathToFileURL(candidate).href, shortCircuit: true }
    }
  }
  return null
}

let registered = false

/** 必须在动态 import 业务模块之前调用；静态 import 会被提升，所以不能靠模块顶层副作用 */
export const registerProjectResolver = () => {
  if (registered) return
  registered = true

  registerHooks({
    resolve(specifier, context, nextResolve) {
      if (specifier.startsWith('@/')) {
        return (
          resolveCandidate(resolvePath(srcDir, specifier.slice(2))) ?? nextResolve(specifier, context)
        )
      }
      // 只接管项目内的相对引用，node_modules 与 node: 内建模块交给默认解析
      if (specifier.startsWith('.') && context.parentURL?.startsWith('file:')) {
        const parentDir = dirname(fileURLToPath(context.parentURL))
        const resolved = resolveCandidate(resolvePath(parentDir, specifier))
        if (resolved) return resolved
      }
      return nextResolve(specifier, context)
    },
  })
}

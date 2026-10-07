/**
 * 设计 token 的 JS 镜像
 * 供 ECharts 等运行时 JS 组件读取，与 _tokens.scss 保持同步。
 * 修改 token 时两端必须同步。
 */

export const tokens = {
  color: {
    primary: {
      50: '#eef3ff',
      100: '#dae5ff',
      200: '#b9cdff',
      300: '#89abff',
      400: '#5c8bff',
      500: '#2f6bff',
      600: '#1f55db',
      700: '#1842b0',
      800: '#143488',
      900: '#0f2866',
    },
    text: {
      primary: '#101828',
      secondary: '#475467',
      tertiary: '#667085',
      quaternary: '#98a2b3',
    },
    success: {
      base: '#17a568',
      light: '#e7f7ef',
      text: '#067647',
    },
    warning: {
      base: '#f59e0b',
      light: '#fef3c7',
      text: '#b54708',
    },
    danger: {
      base: '#e26a2c',
      light: '#feece3',
      text: '#b42318',
    },
    info: {
      base: '#2e90fa',
      light: '#eff8ff',
      text: '#175cd3',
    },
    bg: {
      page: '#f5f7fb',
      card: '#ffffff',
      tint: '#f7f9fc',
      hover: '#f2f4f7',
    },
    border: {
      base: '#e4e7ec',
      light: '#f2f4f7',
    },
    dark: {
      bg: '#0e1629',
      border: '#263451',
      text: '#e9eefc',
      textSec: '#b8c2dd',
      textMute: '#8d98b4',
    },
    chart: {
      purple: '#7a5af8',
      pink: '#ee46bc',
      teal: '#0891b2',
    },
  },
  radius: {
    sm: '6px',
    md: '8px',
    lg: '12px',
  },
  shadow: {
    sm: '0 1px 2px rgba(16, 24, 40, 0.04)',
    md: '0 4px 12px rgba(16, 24, 40, 0.06)',
    lg: '0 12px 30px rgba(19, 34, 66, 0.08)',
  },
} as const

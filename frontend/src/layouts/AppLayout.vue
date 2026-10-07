<template>
  <div class="app-layout">
    <header v-if="isMobile" class="topbar">
      <div class="topbar__brand">
        <div class="brand__mark">C</div>
        <strong>AI 面试成长教练</strong>
      </div>
      <el-avatar :size="30">林</el-avatar>
    </header>

    <aside class="sidebar">
      <div class="brand">
        <div class="brand__mark">C</div>
        <div>
          <strong>AI 面试成长教练</strong>
          <span>Interview Growth Coach</span>
        </div>
      </div>

      <nav class="menu">
        <div
          v-for="item in menus"
          :key="item.path"
          class="menu__item"
          :class="{ 'menu__item--active': route.path.startsWith(item.activePath ?? item.path) }"
          :title="isIconRail ? item.label : undefined"
          @click="router.push(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </nav>

      <div class="profile">
        <el-avatar :size="34">林</el-avatar>
        <div>
          <strong>程序员小林</strong>
          <span>Java 后端工程师</span>
        </div>
      </div>
    </aside>

    <main class="main">
      <router-view />
    </main>

    <nav v-if="isMobile" class="tabbar">
      <div
        v-for="item in tabbarMenus"
        :key="item.path"
        class="tabbar__item"
        :class="{ 'tabbar__item--active': route.path.startsWith(item.path) }"
        @click="router.push(item.path)"
      >
        <el-icon :size="20"><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </div>
      <div
        class="tabbar__item"
        :class="{ 'tabbar__item--active': moreActive }"
        @click="moreVisible = true"
      >
        <el-icon :size="20"><MoreFilled /></el-icon>
        <span>更多</span>
      </div>
    </nav>

    <el-drawer
      v-if="isMobile"
      v-model="moreVisible"
      class="more-drawer"
      title="更多"
      direction="btt"
      size="auto"
    >
      <div class="more-menu">
        <div
          v-for="item in drawerMenus"
          :key="item.path"
          class="more-menu__item"
          :class="{ 'more-menu__item--active': route.path.startsWith(item.path) }"
          @click="handleDrawerSelect(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import {
  ChatDotRound,
  Clock,
  DataAnalysis,
  Document,
  House,
  MoreFilled,
  TrendCharts,
  User,
  Notebook,
} from '@element-plus/icons-vue'
import { computed, ref } from 'vue'
import type { Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useMediaQuery } from '@/composables/useMediaQuery'

type MenuItem = {
  label: string
  path: string
  activePath?: string
  icon: Component
}

const route = useRoute()
const router = useRouter()

// 移动端顶栏 / 底部 TabBar / 「更多」抽屉：桌面端整体不渲染，DOM 与改造前完全一致
const isMobile = useMediaQuery('(max-width: 768px)')
// 图标栏模式只有图标没有文案，用 title 兜住；非该区间时 title 为 undefined，属性不会落到 DOM 上
const isIconRail = useMediaQuery('(min-width: 769px) and (max-width: 1023px)')

// 侧栏菜单保持改造前的 6 项，桌面端渲染结果不变
const menus: MenuItem[] = [
  { label: '首页概览', path: '/dashboard', icon: House },
  { label: 'AI 模拟面试', path: '/mock-interview', activePath: '/mock-interview', icon: ChatDotRound },
  { label: '面试报告', path: '/report', activePath: '/report', icon: Document },
  { label: '能力画像', path: '/ability-profile', icon: DataAnalysis },
  { label: '专项训练', path: '/training', icon: Notebook },
  { label: '面试历史', path: '/interview-history', icon: Clock },
]

// 底部 TabBar 的 4 个页面入口，第 5 格固定为「更多」
const tabbarMenus: (MenuItem & { icon: Component })[] = [
  { label: '首页', path: '/dashboard', icon: House },
  { label: '面试', path: '/mock-interview', activePath: '/mock-interview', icon: ChatDotRound },
  { label: '报告', path: '/report', activePath: '/report', icon: Document },
  { label: '画像', path: '/ability-profile', icon: DataAnalysis },
]

// 「更多」抽屉承载侧栏里没进 TabBar 的入口
const drawerMenus: (MenuItem & { icon: Component })[] = [
  { label: '专项训练', path: '/training', icon: TrendCharts },
  { label: '面试历史', path: '/interview-history', icon: Clock },
  { label: '个人信息', path: '/resume', icon: User },
]

const moreVisible = ref(false)

const moreActive = computed(() =>
  drawerMenus.some((item) => route.path.startsWith(item.activePath ?? item.path)),
)

const handleDrawerSelect = (path: string) => {
  moreVisible.value = false
  router.push(path)
}
</script>

<style scoped lang="scss">
@use '../assets/styles/responsive' as *;
@use '../assets/styles/tokens' as *;

.app-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 232px 1fr;
  background: var(--c-bg-page);
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 22px 18px;
  color: var(--c-dark-text);
  background: var(--c-dark-bg);
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 28px;

  &__mark {
    width: 38px;
    height: 38px;
    display: grid;
    place-items: center;
    border-radius: var(--r-md);
    font-weight: var(--fw-bold);
    background: var(--c-primary-500);
  }

  span {
    display: block;
    margin-top: 4px;
    color: var(--c-dark-text-mute);
    font-size: 12px;
  }
}

.menu {
  display: grid;
  gap: 8px;

  &__item {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 44px;
    padding: 0 12px;
    border-radius: var(--r-md);
    color: var(--c-dark-text-sec);
    cursor: pointer;
  }

  &__item--active {
    color: var(--c-text-inverse);
    background: var(--c-primary-500);
  }
}

.profile {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--c-dark-border);
  border-radius: var(--r-md);

  span {
    display: block;
    margin-top: 4px;
    color: var(--c-dark-text-mute);
    font-size: 12px;
  }
}

.main {
  min-width: 0;
}

@include icon-rail {
  .app-layout {
    grid-template-columns: 72px minmax(0, 1fr);
  }

  .sidebar {
    padding: 22px 10px;
  }

  .brand {
    justify-content: center;
    margin-bottom: 22px;
  }

  .brand > div:last-child,
  .profile > div:last-child,
  .menu__item span {
    display: none;
  }

  .menu__item {
    justify-content: center;
    padding: 0;
  }

  .profile {
    justify-content: center;
    padding: 12px 0;
  }
}

@include mobile {
  .app-layout {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
    min-height: 100dvh;
  }

  .sidebar {
    display: none;
  }

  .topbar {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: $topbar-height;
    padding: 0 14px;
    color: var(--c-dark-text);
    background: var(--c-dark-bg);
  }

  .topbar__brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;

    .brand__mark {
      width: 30px;
      height: 30px;
      font-size: 15px;
    }
  }

  .main {
    padding-bottom: calc(#{$tabbar-height} + #{$safe-bottom});
  }

  .tabbar {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 20;
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    padding-bottom: $safe-bottom;
    background: var(--c-bg-card);
    border-top: 1px solid var(--c-border);
  }

  .tabbar__item {
    display: grid;
    justify-items: center;
    align-content: center;
    gap: 3px;
    min-height: $tabbar-height;
    padding: 4px 2px;
    color: var(--c-text-tertiary);
    font-size: 11px;
    cursor: pointer;

    &--active {
      color: var(--c-primary-500);
    }
  }

  .more-menu {
    display: grid;
    gap: 8px;

    &__item {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 48px;
      padding: 0 14px;
      border-radius: var(--r-md);
      color: var(--c-text-secondary);
      cursor: pointer;
    }

    &__item--active {
      color: var(--c-primary-500);
      background: var(--c-primary-50);
    }
  }
}
</style>

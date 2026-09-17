<template>
  <div class="app-layout">
    <header class="topbar">
      <div class="topbar__brand">
        <div class="brand__mark">C</div>
        <strong>AI 面试成长教练</strong>
      </div>
      <el-avatar :size="30">林</el-avatar>
    </header>

    <aside class="sidebar">
      <div class="brand">
        <div class="brand__mark">C</div>
        <div class="brand__text">
          <strong>AI 面试成长教练</strong>
          <span>Interview Growth Coach</span>
        </div>
      </div>

      <nav class="menu">
        <div
          v-for="item in menus"
          :key="item.path"
          class="menu__item"
          :class="{ 'menu__item--active': isActive(item) }"
          @click="router.push(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </nav>

      <div class="profile">
        <el-avatar :size="34">林</el-avatar>
        <div class="profile__text">
          <strong>程序员小林</strong>
          <span>Java 后端工程师</span>
        </div>
      </div>
    </aside>

    <main class="main">
      <router-view />
    </main>

    <nav class="tabbar">
      <div
        v-for="item in tabbarMenus"
        :key="item.path"
        class="tabbar__item"
        :class="{ 'tabbar__item--active': isActive(item) }"
        @click="router.push(item.path)"
      >
        <el-icon :size="20"><component :is="item.icon" /></el-icon>
        <span>{{ item.tabLabel }}</span>
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

    <el-drawer v-model="moreVisible" class="more-drawer" title="更多" direction="btt" size="auto">
      <div class="more-menu">
        <div
          v-for="item in drawerMenus"
          :key="item.path"
          class="more-menu__item"
          :class="{ 'more-menu__item--active': isActive(item) }"
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
} from '@element-plus/icons-vue'
import { computed, ref } from 'vue'
import type { Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'

type MenuItem = {
  label: string
  path: string
  icon: Component
  tabLabel?: string
}

const route = useRoute()
const router = useRouter()

const menus: MenuItem[] = [
  { label: '首页概览', path: '/dashboard', icon: House, tabLabel: '首页' },
  { label: 'AI 模拟面试', path: '/mock-interview', icon: ChatDotRound, tabLabel: '面试' },
  { label: '面试报告', path: '/report', icon: Document, tabLabel: '报告' },
  { label: '能力画像', path: '/ability-profile', icon: DataAnalysis, tabLabel: '画像' },
  { label: '专项训练', path: '/training', icon: TrendCharts },
  { label: '面试历史', path: '/interview-history', icon: Clock },
  { label: '个人信息', path: '/resume', icon: User },
]

const tabbarMenus = menus.filter((item) => item.tabLabel)
const drawerMenus = menus.filter((item) => !item.tabLabel)

const moreVisible = ref(false)

const isActive = (item: MenuItem) => route.path.startsWith(item.path)
const moreActive = computed(() => drawerMenus.some(isActive))

const handleDrawerSelect = (path: string) => {
  moreVisible.value = false
  router.push(path)
}
</script>

<style scoped lang="scss">
@use '../assets/styles/responsive' as *;

.app-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 232px 1fr;
  background: #f5f7fb;
}

.topbar,
.tabbar {
  display: none;
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 22px 18px;
  color: #e9eefc;
  background: #0e1629;
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 28px;

  span {
    display: block;
    margin-top: 4px;
    color: #8d98b4;
    font-size: 12px;
  }
}

.brand__mark {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  font-weight: 800;
  background: #2f6bff;
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
    border-radius: 8px;
    color: #b8c2dd;
    cursor: pointer;
  }

  &__item--active {
    color: #fff;
    background: #2f6bff;
  }
}

.profile {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px;
  border: 1px solid #263451;
  border-radius: 8px;

  span {
    display: block;
    margin-top: 4px;
    color: #95a0ba;
    font-size: 12px;
  }
}

.main {
  min-width: 0;
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
    border-radius: 8px;
    color: #344054;
    cursor: pointer;
  }

  &__item--active {
    color: #2f6bff;
    background: #eef3fb;
  }
}

// 768~1024px 中间态：侧栏收窄为图标栏
@media (min-width: #{$mobile-max + 1px}) and (max-width: #{$tablet-max}) {
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

  .brand__text,
  .profile__text,
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
    color: #e9eefc;
    background: #0e1629;
  }

  .topbar__brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;
  }

  .topbar__brand .brand__mark {
    width: 30px;
    height: 30px;
    font-size: 15px;
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
    background: #fff;
    border-top: 1px solid #eef2f7;
  }

  .tabbar__item {
    display: grid;
    justify-items: center;
    align-content: center;
    gap: 3px;
    min-height: $tabbar-height;
    padding: 4px 2px;
    color: #667085;
    font-size: 11px;
    cursor: pointer;

    &--active {
      color: #2f6bff;
    }
  }
}
</style>

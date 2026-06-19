<template>
  <div class="app-layout">
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
          @click="router.push(item.path)"
        >
          <el-icon><House /></el-icon>
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
  </div>
</template>

<script setup lang="ts">
import { House } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const menus = [
  { label: '首页概览', path: '/dashboard' },
  { label: 'AI 模拟面试', path: '/mock-interview', activePath: '/mock-interview' },
  { label: '面试报告', path: '/report', activePath: '/report' },
  { label: '能力画像', path: '/ability-profile' },
  { label: '专项训练', path: '/training' },
  { label: '面试历史', path: '/interview-history' },
]
</script>

<style scoped lang="scss">
.app-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 232px 1fr;
  background: #f5f7fb;
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

  &__mark {
    width: 38px;
    height: 38px;
    display: grid;
    place-items: center;
    border-radius: 8px;
    font-weight: 800;
    background: #2f6bff;
  }

  span {
    display: block;
    margin-top: 4px;
    color: #8d98b4;
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
</style>

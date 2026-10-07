<template>
  <section class="welcome-panel card card--float is-emphasis">
    <div class="welcome-panel__content">
      <p class="page-header__eyebrow">首页概览</p>
      <h1>晚上好，{{ userName }}</h1>
      <p class="page-header__desc">这里汇总你的训练数据、能力变化与最近面试记录。</p>
    </div>
    <div class="welcome-panel__actions">
      <el-button type="primary" size="large" @click="$emit('start')">
        快捷开始面试
      </el-button>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  userName: string
}>()

defineEmits<{
  start: []
}>()
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.welcome-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 28px;

  &__content {
    min-width: 0;

    h1 {
      margin: 6px 0 0;
      font-size: 28px;
      font-weight: 700;
      color: var(--c-text-primary);
    }
  }

  &__actions {
    flex-shrink: 0;
  }
}

@include mobile {
  .welcome-panel {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
    padding: 18px;

    h1 {
      font-size: 21px;
    }
  }
}
</style>

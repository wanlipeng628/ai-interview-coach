<template>
  <el-card shadow="never" class="weak-card card card--float">
    <template #header>
      <div class="card__header">
        <h2>Top5 薄弱知识点</h2>
        <el-button link type="primary">查看训练</el-button>
      </div>
    </template>

    <div class="weak-list">
      <div v-for="item in items" :key="item.name" class="weak-item">
        <div class="weak-item__content">
          <strong>{{ item.name }}</strong>
          <span>{{ item.description }}</span>
        </div>
        <div class="weak-item__meta">
          <el-tag :type="tagType(item.riskLevel)" effect="light">{{ item.riskLevel }}</el-tag>
          <b>{{ item.score }}</b>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { WeakKnowledgePoint } from '@/types/dashboard'

defineProps<{
  items: WeakKnowledgePoint[]
}>()

const tagType = (level: WeakKnowledgePoint['riskLevel']) => {
  if (level === '高风险') return 'danger'
  if (level === '中风险') return 'warning'
  return 'success'
}
</script>

<style scoped lang="scss">
.weak-card {
  height: 100%;
}

.card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  h2 {
    margin: 0;
    font-size: var(--fs-lg);
    font-weight: var(--fw-semibold);
    color: var(--c-text-primary);
  }
}

.weak-list {
  display: grid;
  gap: 14px;
}

.weak-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--c-border-light);

  &:last-child {
    padding-bottom: 0;
    border-bottom: 0;
  }

  &__content {
    display: grid;
    gap: 5px;
    min-width: 0;

    strong {
      color: var(--c-text-primary);
      font-weight: 600;
    }

    span {
      color: var(--c-text-tertiary);
      font-size: 13px;
    }
  }

  &__meta {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;

    b {
      min-width: 28px;
      text-align: right;
      color: var(--c-text-secondary);
      font-weight: 600;
    }
  }
}
</style>

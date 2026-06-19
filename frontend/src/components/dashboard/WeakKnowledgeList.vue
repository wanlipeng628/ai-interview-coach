<template>
  <el-card shadow="never" class="weak-card">
    <template #header>
      <div class="header">
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
  border: 0;
  border-radius: 8px;
  box-shadow: 0 12px 30px rgba(19, 34, 66, 0.05);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;

  h2 {
    margin: 0;
    font-size: 17px;
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
  border-bottom: 1px solid #eef2f7;

  &:last-child {
    padding-bottom: 0;
    border-bottom: 0;
  }

  &__content {
    display: grid;
    gap: 5px;

    strong {
      color: #101828;
    }

    span {
      color: #667085;
      font-size: 13px;
    }
  }

  &__meta {
    display: flex;
    align-items: center;
    gap: 10px;

    b {
      min-width: 28px;
      text-align: right;
      color: #344054;
    }
  }
}
</style>

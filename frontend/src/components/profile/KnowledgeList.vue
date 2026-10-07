<template>
  <el-card shadow="never" class="knowledge-card card card--float">
    <template #header><h2>知识点掌握情况</h2></template>
    <div class="knowledge-list">
      <div v-for="item in items" :key="item.name" class="knowledge-item">
        <div class="knowledge-item__top">
          <strong>{{ item.name }}</strong>
          <el-tag :type="tagType(item.status)" effect="light">{{ item.status }}</el-tag>
        </div>
        <el-progress :percentage="item.score" :stroke-width="8" />
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { KnowledgeNode } from '@/types/profile'

defineProps<{ items: KnowledgeNode[] }>()

const tagType = (status: KnowledgeNode['status']) => {
  if (status === '薄弱') return 'danger'
  if (status === '需要巩固') return 'warning'
  return 'success'
}
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.knowledge-card {
  h2 {
    margin: 0;
    font-size: var(--fs-lg);
    font-weight: var(--fw-semibold);
  }
}

.knowledge-list {
  display: grid;
  gap: 18px;
}

.knowledge-item__top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  align-items: center;
  gap: 10px;

  strong {
    color: var(--c-text-primary);
    font-weight: 600;
  }
}

@include mobile {
  .knowledge-list {
    gap: 14px;
  }

  .knowledge-item__top {
    strong {
      min-width: 0;
      overflow-wrap: anywhere;
    }
  }
}
</style>

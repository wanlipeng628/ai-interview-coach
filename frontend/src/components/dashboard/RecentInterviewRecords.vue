<template>
  <el-card shadow="never" class="records-card card card--float">
    <template #header>
      <div class="card__header">
        <h2>最近面试记录</h2>
        <el-button link type="primary">全部记录</el-button>
      </div>
    </template>

    <!-- 桌面端：表格 -->
    <el-table v-if="!isMobile" :data="records" height="288" class="records-table">
      <el-table-column prop="company" label="公司" min-width="120" />
      <el-table-column prop="role" label="岗位" min-width="150" />
      <el-table-column prop="date" label="日期" width="120" />
      <el-table-column label="成绩" width="90">
        <template #default="{ row }">
          <strong :class="{ low: row.score < 70 }">{{ row.score }}</strong>
        </template>
      </el-table-column>
      <el-table-column label="结果" width="100">
        <template #default="{ row }">
          <el-tag :type="row.score >= 70 ? 'success' : 'warning'" effect="light">{{ row.result }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <!-- 移动端：卡片列表（与历史页一致模式） -->
    <div v-else class="record-cards">
      <article v-for="row in records" :key="row.id" class="record-card">
        <header class="record-card__head">
          <h3>{{ row.company }}</h3>
          <el-tag :type="row.score >= 70 ? 'success' : 'warning'" effect="light" size="small">{{ row.result }}</el-tag>
        </header>
        <dl class="record-card__meta">
          <div>
            <dt>岗位</dt>
            <dd>{{ row.role }}</dd>
          </div>
          <div>
            <dt>日期</dt>
            <dd>{{ row.date }}</dd>
          </div>
        </dl>
        <div class="record-card__score">
          <span>成绩</span>
          <strong :class="{ low: row.score < 70 }">{{ row.score }}</strong>
        </div>
      </article>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { InterviewRecord } from '@/types/dashboard'
import { useMediaQuery } from '@/composables/useMediaQuery'

defineProps<{
  records: InterviewRecord[]
}>()

const isMobile = useMediaQuery('(max-width: 768px)')
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.records-card {
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

.records-table {
  strong {
    color: var(--c-success-text);
    font-weight: 600;
  }

  .low {
    color: var(--c-danger-text);
  }
}

// —— 移动端卡片列表 ——
.record-cards {
  display: grid;
  gap: 10px;
}

.record-card {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  background: var(--c-bg-card);

  &__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;

    h3 {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      line-height: 1.4;
      word-break: break-word;
    }
  }

  &__meta {
    display: grid;
    gap: 6px;
    margin: 0;
    font-size: 13px;

    div {
      display: flex;
      gap: 8px;
    }

    dt {
      flex: none;
      width: 48px;
      color: var(--c-text-tertiary);
    }

    dd {
      margin: 0;
      color: var(--c-text-primary);
      word-break: break-word;
    }
  }

  &__score {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--c-text-tertiary);
    font-size: 13px;

    strong {
      font-size: 18px;
      color: var(--c-success-text);
      font-weight: 700;

      &.low {
        color: var(--c-danger-text);
      }
    }
  }
}
</style>

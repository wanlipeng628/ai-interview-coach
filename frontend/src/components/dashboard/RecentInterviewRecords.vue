<template>
  <el-card shadow="never" class="records-card">
    <template #header>
      <div class="header">
        <h2>最近面试记录</h2>
        <el-button link type="primary">全部记录</el-button>
      </div>
    </template>

    <el-table :data="records" height="288" class="records-table">
      <el-table-column prop="company" label="公司" min-width="120" />
      <el-table-column prop="role" label="岗位" min-width="150" />
      <el-table-column prop="date" label="日期" width="120" />
      <el-table-column label="成绩" width="90">
        <template #default="{ row }">
          <strong :class="{ danger: row.score < 70 }">{{ row.score }}</strong>
        </template>
      </el-table-column>
      <el-table-column label="结果" width="100">
        <template #default="{ row }">
          <el-tag :type="row.score >= 70 ? 'success' : 'warning'">{{ row.result }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import type { InterviewRecord } from '@/types/dashboard'

defineProps<{
  records: InterviewRecord[]
}>()
</script>

<style scoped lang="scss">
.records-card {
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

.records-table {
  strong {
    color: #17a568;
  }

  .danger {
    color: #e26a2c;
  }
}
</style>

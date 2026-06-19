<template>
  <el-card shadow="never" class="info-panel">
    <template #header>
      <h2>面试信息</h2>
    </template>

    <div class="info-list">
      <div>
        <span>当前岗位</span>
        <strong>{{ info.jobRole }}</strong>
      </div>
      <div>
        <span>面试时长</span>
        <strong>{{ formattedDuration }} / {{ info.durationLimitMinutes }} 分钟</strong>
      </div>
      <div>
        <span>面试状态</span>
        <el-tag :type="info.status === 'finished' ? 'success' : 'primary'">
          {{ info.status === 'finished' ? '已结束' : '进行中' }}
        </el-tag>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { InterviewInfo } from '@/types/interview'

const props = defineProps<{
  info: InterviewInfo
}>()

const formattedDuration = computed(() => {
  const minutes = Math.floor(props.info.durationSeconds / 60)
  const seconds = props.info.durationSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})
</script>

<style scoped lang="scss">
.info-panel {
  border: 0;
  border-radius: 8px;
}

h2 {
  margin: 0;
  font-size: 17px;
}

.info-list {
  display: grid;
  gap: 18px;

  div {
    display: grid;
    gap: 6px;
  }

  span {
    color: #667085;
    font-size: 13px;
  }

  strong {
    color: #101828;
    font-size: 18px;
  }
}
</style>

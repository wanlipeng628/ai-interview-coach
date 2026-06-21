<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p>专项训练</p>
        <h1>针对薄弱点的训练清单</h1>
      </div>
      <el-button :loading="training.loading" type="primary" @click="training.fetchTasks()">
        刷新任务
      </el-button>
    </header>

    <el-alert
      v-if="training.errorMessage"
      :title="training.errorMessage"
      type="error"
      show-icon
      :closable="false"
    />

    <TrainingPlanCard :plan="training.plan" />

    <TrainingTopicList
      :tasks="training.tasks"
      @status="handleStatusChange"
      @start="handleStart"
      @open-report="handleOpenReport"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import TrainingPlanCard from '@/components/training/TrainingPlanCard.vue'
import TrainingTopicList from '@/components/training/TrainingTopicList.vue'
import { useTrainingStore } from '@/stores/training.store'
import type { TrainingTask } from '@/types/training'

const router = useRouter()
const training = useTrainingStore()

const handleStatusChange = async (taskId: number, status: TrainingTask['status']) => {
  await training.updateTaskStatus(taskId, status)
  ElMessage.success('训练状态已更新')
}

const handleStart = (taskId: number) => {
  router.push(`/training/${taskId}`)
}

const handleOpenReport = (sessionId: string) => {
  router.push(`/report/${sessionId}`)
}

onMounted(() => {
  training.fetchTasks()
})
</script>

<style scoped lang="scss">
.page {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-radius: 8px;
  background: #fff;

  p {
    margin: 0 0 8px;
    color: #2f6bff;
    font-weight: 800;
  }

  h1 {
    margin: 0;
    font-size: 24px;
  }
}
</style>

<template>
  <div class="page">
    <PageHeader eyebrow="专项训练" title="针对薄弱点的训练清单">
      <template #actions>
        <el-button :loading="training.loading" type="primary" @click="training.fetchTasks()">
          刷新任务
        </el-button>
      </template>
    </PageHeader>

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

import PageHeader from '@/components/common/PageHeader.vue'
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
@use '../../assets/styles/responsive' as *;

.page {
  display: grid;
  gap: 18px;
  padding: 24px;
}

@include mobile {
  .page {
    gap: 12px;
    padding: 14px;
  }
}
</style>

<template>
  <el-card shadow="never" class="task-card">
    <template #header><h2>训练任务</h2></template>
    <el-empty
      v-if="tasks.length === 0"
      description="暂无训练任务，生成面试报告后会自动沉淀薄弱点"
    />
    <div v-else class="tasks">
      <article v-for="task in tasks" :key="task.id" class="task">
        <div>
          <div class="task__title">
            <strong>{{ task.title }}</strong>
            <el-tag :type="getSeverityType(task.severity)">
              {{ getSeverityText(task.severity) }}
            </el-tag>
          </div>
          <p>{{ task.reason || '建议围绕该知识点补充原理、场景、方案和项目案例。' }}</p>
          <div v-if="task.sourceSessionId" class="source-actions">
            <span>来源面试</span>
            <el-button
              v-if="task.hasReport"
              text
              type="primary"
              @click="emit('openReport', task.sourceSessionId)"
            >
              查看报告
            </el-button>
            <el-tag v-else type="info">报告不可用</el-tag>
          </div>
        </div>

        <div class="task__actions">
          <el-button type="primary" @click="emit('start', task.id)">
            {{ task.status === 'DONE' ? '重新训练' : '开始训练' }}
          </el-button>
          <el-select
            :model-value="task.status"
            class="status"
            @change="(value: string | number | boolean) => handleStatusChange(task.id, value)"
          >
            <el-option label="待训练" value="TODO" />
            <el-option label="训练中" value="IN_PROGRESS" />
            <el-option label="已完成" value="DONE" />
          </el-select>
        </div>
      </article>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { TrainingTask } from '@/types/training'

defineProps<{ tasks: TrainingTask[] }>()

const emit = defineEmits<{
  status: [taskId: number, status: TrainingTask['status']]
  start: [taskId: number]
  openReport: [sessionId: string]
}>()

const handleStatusChange = (taskId: number, value: string | number | boolean) => {
  emit('status', taskId, String(value) as TrainingTask['status'])
}

const getSeverityType = (severity: string) => {
  if (severity === 'High') return 'danger'
  if (severity === 'Low') return 'info'
  return 'warning'
}

const getSeverityText = (severity: string) => {
  if (severity === 'High') return '高优先级'
  if (severity === 'Low') return '低优先级'
  return '中优先级'
}
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.task-card {
  border: 0;
  border-radius: 8px;
}

h2 {
  margin: 0;
  font-size: 17px;
}

.tasks {
  display: grid;
  gap: 14px;
}

.task {
  display: grid;
  grid-template-columns: 1fr 220px;
  gap: 16px;
  padding: 16px;
  border-radius: 8px;
  background: #f7f9fd;

  &__title {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  &__actions {
    display: grid;
    align-content: start;
    gap: 10px;
  }

  p {
    margin: 8px 0;
    color: #475467;
    line-height: 1.7;
  }
}

.source-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #98a2b3;
}

.status {
  width: 100%;
}

@media (max-width: 760px) {
  .task {
    grid-template-columns: 1fr;
  }
}

@include mobile {
  .task {
    gap: 12px;
    padding: 14px;
  }

  .task__title {
    align-items: flex-start;
    gap: 8px;

    strong {
      min-width: 0;
      overflow-wrap: anywhere;
    }
  }

  .task__actions .el-button {
    width: 100%;
  }

  .source-actions {
    flex-wrap: wrap;
  }
}
</style>

<template>
  <el-card shadow="never" class="topic-card">
    <template #header><h2>训练主题</h2></template>
    <div class="topics">
      <div v-for="topic in topics" :key="topic.id" class="topic">
        <div>
          <strong>{{ topic.title }}</strong>
          <p>{{ topic.description }}</p>
          <el-progress :percentage="topic.progress" />
        </div>
        <div class="topic__side">
          <el-tag>{{ topic.difficulty }}</el-tag>
          <span>{{ topic.duration }}</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { TrainingTopic } from '@/types/training'

defineProps<{ topics: TrainingTopic[] }>()
</script>

<style scoped lang="scss">
.topic-card {
  border: 0;
  border-radius: 8px;
}

h2 {
  margin: 0;
  font-size: 17px;
}

.topics {
  display: grid;
  gap: 14px;
}

.topic {
  display: grid;
  grid-template-columns: 1fr 86px;
  gap: 16px;
  padding: 16px;
  border-radius: 8px;
  background: #f7f9fd;

  p {
    color: #667085;
  }

  &__side {
    display: grid;
    justify-items: end;
    align-content: start;
    gap: 10px;
  }
}
</style>

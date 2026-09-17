<template>
  <el-card shadow="never" class="info-panel">
    <template #header>
      <h2>面试信息</h2>
      <el-button
        v-if="isMobile"
        class="info-panel__toggle"
        link
        type="primary"
        @click="expanded = !expanded"
      >
        {{ expanded ? '收起' : '展开' }}
        <el-icon>
          <component :is="expanded ? ArrowUp : ArrowDown" />
        </el-icon>
      </el-button>
    </template>

    <div v-show="!isMobile || expanded" class="info-list">
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
import { ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { computed, ref } from 'vue'

import { useMediaQuery } from '@/composables/useMediaQuery'
import type { InterviewInfo } from '@/types/interview'

const props = defineProps<{
  info: InterviewInfo
}>()

const isMobile = useMediaQuery('(max-width: 768px)')
const expanded = ref(false)

const formattedDuration = computed(() => {
  const minutes = Math.floor(props.info.durationSeconds / 60)
  const seconds = props.info.durationSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

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

// 折叠按钮只在移动端渲染，桌面端 #header 内仍只有 h2，样式与改造前一致
@include mobile {
  .info-panel :deep(.el-card__header) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .info-panel__toggle {
    min-height: $touch-target;
  }

  .info-list {
    gap: 12px;

    strong {
      font-size: 15px;
    }
  }
}
</style>

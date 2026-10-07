<template>
  <el-card
    shadow="never"
    class="info-panel card card--float"
    :class="{ 'info-panel--collapsed': isMobile && !expanded }"
  >
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
        <span class="info-list__label">当前岗位</span>
        <strong>{{ info.jobRole }}</strong>
      </div>
      <div>
        <span class="info-list__label">面试时长</span>
        <strong>{{ formattedDuration }} / {{ info.durationLimitMinutes }} 分钟</strong>
      </div>
      <div>
        <span class="info-list__label">面试状态</span>
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

.info-panel.card {
  h2 {
    margin: 0;
  }
}

.info-list {
  display: grid;
  gap: 18px;

  div {
    display: grid;
    gap: 6px;
  }

  // 标签文字：用类名而非裸 span，避免命中同容器内 el-tag 的根 span
  &__label {
    color: var(--c-text-tertiary);
    font-size: 13px;
  }

  strong {
    color: var(--c-text-primary);
    font-size: var(--fs-xl);
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

  // 折叠后 body 内只剩 display:none 的列表，不收起内边距就会在标题下留一条空白
  .info-panel--collapsed :deep(.el-card__body) {
    padding-top: 0;
    padding-bottom: 0;
  }

  .info-list {
    gap: 12px;

    strong {
      font-size: 15px;
    }
  }
}
</style>

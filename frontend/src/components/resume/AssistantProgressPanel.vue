<template>
  <el-card
    shadow="never"
    class="progress-panel card card--float"
    :class="{ 'progress-panel--collapsed': isMobile && !expanded }"
  >
    <template #header>
      <h2>简历分节</h2>
      <el-button
        v-if="isMobile"
        class="progress-panel__toggle"
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

    <div v-show="!isMobile || expanded" class="progress-body">
      <el-progress :percentage="percent" :stroke-width="8" />
      <p class="progress-body__summary">
        已完成 {{ progress.completed.length }} / {{ sections.length }} 个分节
      </p>

      <ol class="steps">
        <li v-for="(section, index) in sections" :key="section.key" :class="stateClass(section.key)">
          <span class="steps__marker">
            <el-icon v-if="isCompleted(section.key)"><Check /></el-icon>
            <template v-else>{{ index + 1 }}</template>
          </span>
          <div class="steps__content">
            <strong>{{ section.label }}</strong>
            <span>{{ stateLabel(section.key) }}</span>
          </div>
        </li>
      </ol>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ArrowDown, ArrowUp, Check } from '@element-plus/icons-vue'
import { computed, ref } from 'vue'

import { useMediaQuery } from '@/composables/useMediaQuery'
import type { AssistantProgress, ResumeSection } from '@/types/resumeAssistant'
import { RESUME_SECTIONS } from '@/types/resumeAssistant'

const props = defineProps<{
  progress: AssistantProgress
}>()

const sections = RESUME_SECTIONS
const isMobile = useMediaQuery('(max-width: 768px)')
const expanded = ref(false)

const percent = computed(() =>
  Math.round((props.progress.completed.length / sections.length) * 100),
)

const isCompleted = (key: ResumeSection) => props.progress.completed.includes(key)
const isCurrent = (key: ResumeSection) =>
  props.progress.current === key && !isCompleted(key)

const stateClass = (key: ResumeSection) => ({
  'steps__item--done': isCompleted(key),
  'steps__item--current': isCurrent(key),
})

const stateLabel = (key: ResumeSection) => {
  if (isCompleted(key)) return '已完成'
  if (isCurrent(key)) return '进行中'
  return '待填写'
}
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.progress-panel.card {
  height: 100%;

  h2 {
    margin: 0;
  }
}

.progress-body {
  display: grid;
  gap: 12px;
}

.progress-body__summary {
  margin: 0 0 6px;
  color: var(--c-text-tertiary);
  font-size: 13px;
}

.steps {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;

  &__item--done,
  &__item--current {
    .steps__content strong {
      color: var(--c-text-primary);
    }
  }

  &__item--done .steps__marker {
    color: var(--c-text-inverse);
    background: var(--c-success);
  }

  &__item--current .steps__marker {
    color: var(--c-text-inverse);
    background: var(--c-primary-500);
  }
}

.steps > li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--r-md);
  background: var(--c-bg-tint);
  color: var(--c-text-tertiary);
}

.steps__marker {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-size: 13px;
  font-weight: var(--fw-semibold);
  background: var(--c-border);
  color: var(--c-text-tertiary);
}

.steps__content {
  display: grid;
  gap: 2px;

  strong {
    font-size: var(--fs-md);
    font-weight: var(--fw-semibold);
  }

  span {
    font-size: 12px;
  }
}

@include mobile {
  .progress-panel :deep(.el-card__header) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .progress-panel__toggle {
    min-height: $touch-target;
  }

  .progress-panel--collapsed :deep(.el-card__body) {
    padding-top: 0;
    padding-bottom: 0;
  }
}
</style>

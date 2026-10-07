<template>
  <el-dialog
    :model-value="modelValue"
    :fullscreen="isMobile"
    class="result-dialog"
    title="生成的简历"
    width="760px"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div v-if="result" class="result">
      <div class="result__head">
        <h3>{{ result.title }}</h3>
        <p v-if="result.summary">{{ result.summary }}</p>
      </div>
      <div class="markdown-body" v-html="renderedContent" />
    </div>

    <template #footer>
      <div class="result__actions">
        <el-button :disabled="saved" @click="handleSave">
          {{ saved ? '已保存' : '保存为简历' }}
        </el-button>
        <el-button @click="$emit('continue')">继续补充</el-button>
        <el-button type="primary" @click="$emit('interview')">去模拟面试</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useMediaQuery } from '@/composables/useMediaQuery'
import type { ResumeResult } from '@/types/resumeAssistant'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  modelValue: boolean
  result: ResumeResult | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: []
  continue: []
  interview: []
}>()

const isMobile = useMediaQuery('(max-width: 768px)')
const saved = ref(false)

const renderedContent = computed(() => renderMarkdown(props.result?.content ?? ''))

watch(
  () => props.result,
  () => {
    saved.value = false
  },
)

const handleSave = () => {
  saved.value = true
  emit('save')
}
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.result {
  display: grid;
  gap: 16px;

  &__head {
    padding-bottom: 12px;
    border-bottom: 1px solid var(--c-border-light);

    h3 {
      margin: 0;
      font-size: var(--fs-xl);
    }

    p {
      margin: 6px 0 0;
      color: var(--c-text-tertiary);
      font-size: var(--fs-sm);
    }
  }
}

.result__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

// v-html 内容不带 scoped 属性，需用 :deep 命中
.markdown-body {
  max-height: 56vh;
  overflow-y: auto;
  color: var(--c-text-primary);
  line-height: 1.8;

  :deep(h1) {
    margin: 0 0 16px;
    font-size: var(--fs-2xl);
  }

  :deep(h2) {
    margin: 22px 0 10px;
    padding-left: 10px;
    border-left: 3px solid var(--c-primary-500);
    font-size: var(--fs-lg);
  }

  :deep(h3) {
    margin: 16px 0 8px;
    font-size: var(--fs-md);
  }

  :deep(p) {
    margin: 0 0 10px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  :deep(ul),
  :deep(ol) {
    margin: 0 0 12px;
    padding-left: 20px;
  }

  :deep(li) {
    margin-bottom: 6px;
    color: var(--c-text-secondary);
  }

  :deep(strong) {
    color: var(--c-text-primary);
    font-weight: var(--fw-semibold);
  }

  :deep(code) {
    padding: 1px 5px;
    border-radius: var(--r-sm);
    background: var(--c-bg-hover);
    font-size: 13px;
  }
}

@include mobile {
  .markdown-body {
    max-height: none;
  }

  .result__actions {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;

    .el-button {
      width: 100%;
      margin-left: 0;
    }
  }
}
</style>

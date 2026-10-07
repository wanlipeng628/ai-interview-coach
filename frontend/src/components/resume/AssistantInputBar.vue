<template>
  <footer class="input-bar">
    <el-input
      v-model="draft"
      type="textarea"
      :rows="isMobile ? 2 : 3"
      resize="none"
      :disabled="disabled"
      placeholder="请输入你的回答，说得具体一些，AI 会帮你整理成简历。"
      @keydown.enter.exact.prevent="handleSend"
    />
    <div class="actions">
      <span v-if="generating" class="status-text">AI 正在处理...</span>
      <span v-else-if="readyToFinalize" class="status-text status-text--ready">
        信息已收集完整，可以生成简历了
      </span>
      <el-button
        v-if="readyToFinalize"
        :loading="finalizing"
        :disabled="disabled"
        type="success"
        @click="$emit('finalize')"
      >
        生成简历
      </el-button>
      <el-button
        :loading="sending"
        :disabled="disabled || !draft.trim()"
        type="primary"
        @click="handleSend"
      >
        发送
      </el-button>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { useMediaQuery } from '@/composables/useMediaQuery'

defineProps<{
  disabled: boolean
  sending: boolean
  finalizing: boolean
  generating: boolean
  readyToFinalize: boolean
}>()

const emit = defineEmits<{
  send: [answer: string]
  finalize: []
}>()

const isMobile = useMediaQuery('(max-width: 768px)')
const draft = ref('')

const handleSend = () => {
  const answer = draft.value.trim()
  if (!answer) return
  emit('send', answer)
  draft.value = ''
}
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.input-bar {
  display: grid;
  gap: 12px;
  padding: 16px;
  border-radius: var(--r-md);
  background: var(--c-bg-card);
  box-shadow: var(--sh-md);
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.status-text {
  margin-right: auto;
  color: var(--c-text-tertiary);
  font-size: 13px;

  &--ready {
    color: var(--c-success-text);
  }
}

@include mobile {
  .input-bar {
    gap: 10px;
    padding: 12px;
  }

  .actions {
    flex-wrap: wrap;
    gap: 8px;
  }

  .status-text {
    width: 100%;
    font-size: 12px;
  }
}
</style>

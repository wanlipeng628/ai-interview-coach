<template>
  <footer class="input-bar">
    <el-input
      v-model="draft"
      type="textarea"
      :rows="3"
      resize="none"
      :disabled="disabled"
      placeholder="请输入你的回答，建议按照：背景、方案、结果、反思的结构表达。"
      @keydown.enter.exact.prevent="handleSend"
    />
    <div class="actions">
      <span v-if="generating" class="status-text">AI 正在生成下一题...</span>
      <el-button :disabled="disabled" type="danger" plain @click="$emit('finish')">
        结束面试
      </el-button>
      <el-button
        :loading="generating"
        :disabled="disabled || !draft.trim()"
        type="primary"
        @click="handleSend"
      >
        发送回答
      </el-button>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  disabled: boolean
  generating: boolean
}>()

const emit = defineEmits<{
  send: [answer: string]
  finish: []
}>()

const draft = ref('')

const handleSend = () => {
  const answer = draft.value.trim()
  if (!answer) return
  emit('send', answer)
  draft.value = ''
}
</script>

<style scoped lang="scss">
.input-bar {
  display: grid;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 30px rgba(19, 34, 66, 0.06);
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.status-text {
  margin-right: auto;
  color: #667085;
  font-size: 13px;
}
</style>

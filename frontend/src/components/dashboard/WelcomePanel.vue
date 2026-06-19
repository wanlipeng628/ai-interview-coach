<template>
  <section class="welcome-panel">
    <div>
      <p class="eyebrow">首页概览</p>
      <h1>晚上好，{{ userName }}</h1>
      <p class="subtitle">坚持练习，离理想 Offer 更进一步！</p>
    </div>
    <el-button type="primary" size="large" @click="$emit('start')">
      快捷开始面试
    </el-button>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  userName: string
}>()

defineEmits<{
  start: []
}>()
</script>

<style scoped lang="scss">
.welcome-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 28px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 30px rgba(19, 34, 66, 0.05);
}

.eyebrow {
  margin: 0 0 8px;
  color: #2f6bff;
  font-weight: 700;
}

h1 {
  margin: 0;
  font-size: 26px;
  color: #101828;
}

.subtitle {
  margin: 8px 0 0;
  color: #667085;
}
</style>

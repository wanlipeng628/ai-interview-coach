<template>
  <div class="prepare-page">
    <section class="prepare-panel">
      <div class="headline">
        <p>AI 模拟面试</p>
        <h1>开始一场新的 Java 面试</h1>
        <span>确认岗位、时长和简历信息后，再创建面试会话。</span>
      </div>

      <el-form label-position="top" class="form">
        <el-form-item label="面试岗位">
          <el-input v-model="form.jobRole" maxlength="40" placeholder="请输入面试岗位" />
        </el-form-item>

        <el-form-item label="面试时长">
          <el-segmented v-model="form.durationMinutes" :options="durationOptions" />
        </el-form-item>

        <el-form-item label="简历信息">
          <el-input
            v-model="form.resumeText"
            type="textarea"
            :rows="8"
            resize="none"
            placeholder="可以粘贴简历、自我介绍或项目经历。面试官会基于这些信息判断经验年限和追问方向。"
          />
        </el-form-item>

        <div class="actions">
          <el-button @click="router.push('/dashboard')">返回首页</el-button>
          <el-button :loading="interview.loading" type="primary" @click="handleStart">
            开始面试
          </el-button>
        </div>
      </el-form>
    </section>

    <aside class="tips">
      <h2>开始前确认</h2>
      <ul>
        <li>点击“开始面试”后才会创建新的面试记录。</li>
        <li>面试过程中不会实时评分，结束后统一生成报告。</li>
        <li>建议回答尽量包含背景、方案、结果和反思。</li>
      </ul>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useInterviewStore } from '@/stores/interview.store'

const router = useRouter()
const interview = useInterviewStore()

const durationOptions = [
  { label: '30 分钟', value: 30 },
  { label: '45 分钟', value: 45 },
  { label: '60 分钟', value: 60 },
]

const form = reactive({
  jobRole: 'Java开发工程师',
  durationMinutes: 45,
  resumeText: '',
})

const handleStart = async () => {
  if (!form.jobRole.trim()) {
    ElMessage.warning('请先填写面试岗位')
    return
  }

  try {
    await interview.startInterview({
      jobRole: form.jobRole,
      durationMinutes: form.durationMinutes,
      resumeText: form.resumeText,
    })
    router.push(`/mock-interview/${interview.info.sessionId}`)
  } catch {
    ElMessage.error('创建面试会话失败，请确认后端服务已启动')
  }
}
</script>

<style scoped lang="scss">
.prepare-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  padding: 24px;
}

.prepare-panel,
.tips {
  border-radius: 8px;
  background: #fff;
}

.prepare-panel {
  padding: 28px;
}

.headline {
  margin-bottom: 28px;

  p {
    margin: 0 0 8px;
    color: #2f6bff;
    font-weight: 800;
  }

  h1 {
    margin: 0 0 10px;
    color: #101828;
    font-size: 28px;
  }

  span {
    color: #667085;
  }
}

.form {
  max-width: 760px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.tips {
  align-self: start;
  padding: 24px;

  h2 {
    margin: 0 0 16px;
    font-size: 18px;
  }

  ul {
    display: grid;
    gap: 12px;
    padding-left: 18px;
    margin: 0;
    color: #667085;
    line-height: 1.7;
  }
}

@media (max-width: 1080px) {
  .prepare-page {
    grid-template-columns: 1fr;
  }
}
</style>

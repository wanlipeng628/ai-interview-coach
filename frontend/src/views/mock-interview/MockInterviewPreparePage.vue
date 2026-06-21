<template>
  <div class="prepare-page">
    <section class="prepare-panel">
      <div class="headline">
        <p>AI 模拟面试</p>
        <h1>开始前先确认面试配置</h1>
        <span>选择方向、模式和时长后再创建会话，避免重复产生无效记录。</span>
      </div>

      <el-alert
        v-if="interview.latestActive?.hasActive"
        class="active-alert"
        type="info"
        show-icon
        :closable="false"
      >
        <template #title>
          存在一场未完成面试：{{ interview.latestActive.jobRole }}，已回答
          {{ interview.latestActive.answeredCount }} 轮。
        </template>
        <el-button size="small" type="primary" @click="handleContinue">继续上次面试</el-button>
      </el-alert>

      <el-form label-position="top" class="form">
        <el-form-item label="面试岗位">
          <el-input v-model="form.jobRole" maxlength="40" placeholder="请输入面试岗位" />
        </el-form-item>

        <el-form-item label="面试方向">
          <el-select v-model="form.direction" class="full">
            <el-option
              v-for="item in directionOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="面试官模式">
          <el-segmented v-model="form.interviewerMode" :options="modeOptions" />
        </el-form-item>

        <el-form-item label="面试时长">
          <el-segmented v-model="form.durationMinutes" :options="durationOptions" />
        </el-form-item>

        <el-form-item label="默认简历">
          <div class="resume-box">
            <el-switch v-model="form.useDefaultResume" />
            <span v-if="resume.profile">{{ resume.profile.title }}：{{ resume.profile.summary || '已保存简历' }}</span>
            <span v-else>暂未保存默认简历</span>
            <el-button text type="primary" @click="router.push('/resume')">维护简历</el-button>
          </div>
        </el-form-item>

        <el-form-item v-if="!form.useDefaultResume" label="本次面试简历">
          <el-input
            v-model="form.resumeText"
            type="textarea"
            :rows="8"
            resize="none"
            placeholder="可以粘贴本次面试使用的简历、自我介绍或项目经历。"
          />
        </el-form-item>

        <div class="actions">
          <el-button @click="router.push('/dashboard')">返回首页</el-button>
          <el-button :loading="interview.loading" type="primary" @click="handleStart">
            开始新面试
          </el-button>
        </div>
      </el-form>
    </section>

    <aside class="tips">
      <h2>开始前确认</h2>
      <ul>
        <li>点击“开始新面试”后才会创建新的面试记录。</li>
        <li>面试中不展示评分和参考答案，结束后统一复盘。</li>
        <li>如果只是测试流程，结束后可以在历史页删除无效记录。</li>
      </ul>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useInterviewStore } from '@/stores/interview.store'
import { useResumeStore } from '@/stores/resume.store'

const router = useRouter()
const interview = useInterviewStore()
const resume = useResumeStore()

const durationOptions = [
  { label: '30 分钟', value: 30 },
  { label: '45 分钟', value: 45 },
  { label: '60 分钟', value: 60 },
]

const directionOptions = [
  { label: '完整模拟', value: 'FULL_MOCK' },
  { label: '项目深挖', value: 'PROJECT_DEEP_DIVE' },
  { label: 'Java 基础', value: 'JAVA_BASIC' },
  { label: '并发编程', value: 'CONCURRENCY' },
  { label: 'JVM', value: 'JVM' },
  { label: 'MySQL', value: 'MYSQL' },
  { label: 'Redis', value: 'REDIS' },
  { label: 'Spring', value: 'SPRING' },
  { label: '系统设计', value: 'SYSTEM_DESIGN' },
  { label: '线上问题排查', value: 'TROUBLESHOOTING' },
]

const modeOptions = [
  { label: '温和', value: 'GENTLE' },
  { label: '正常', value: 'NORMAL' },
  { label: '严格', value: 'STRICT' },
  { label: '大厂一面', value: 'BIG_TECH_FIRST_ROUND' },
]

const form = reactive({
  jobRole: 'Java开发工程师',
  direction: 'FULL_MOCK',
  interviewerMode: 'NORMAL',
  durationMinutes: 45,
  useDefaultResume: true,
  resumeText: '',
})

onMounted(() => {
  resume.fetchProfile()
  interview.fetchLatestActive()
})

const handleContinue = () => {
  if (!interview.latestActive?.sessionId) return
  router.push(`/mock-interview/${interview.latestActive.sessionId}`)
}

const handleStart = async () => {
  if (!form.jobRole.trim()) {
    ElMessage.warning('请先填写面试岗位')
    return
  }

  const resumeText = form.useDefaultResume ? resume.profile?.content ?? '' : form.resumeText
  try {
    await interview.startInterview({
      jobRole: form.jobRole,
      direction: form.direction,
      interviewerMode: form.interviewerMode,
      durationMinutes: form.durationMinutes,
      resumeText,
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
  margin-bottom: 22px;

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

.active-alert {
  margin-bottom: 20px;
}

.form {
  max-width: 760px;
}

.full {
  width: 100%;
}

.resume-box {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  color: #475467;
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

<template>
  <div class="page">
    <PageHeader
      eyebrow="我的简历"
      title="维护默认面试简历"
      description="这份简历会在开始模拟面试时自动作为 AI 面试官的上下文。"
    >
      <template #actions>
        <el-upload
          :show-file-list="false"
          :before-upload="beforeUpload"
          :http-request="handleUpload"
          accept=".txt,.md,.pdf,.docx"
        >
          <el-button :loading="resume.uploading" :disabled="resume.saving">
            <el-icon><Upload /></el-icon>
            <span>上传简历文件</span>
          </el-button>
        </el-upload>
        <el-button :loading="resume.saving" type="primary" @click="handleSave">保存简历</el-button>
      </template>
    </PageHeader>

    <el-alert class="assistant-entry" type="info" show-icon :closable="false">
      <template #title>不会写？让 AI 引导你生成简历</template>
      <div class="assistant-entry__body">
        <span>通过几轮对话梳理你的经历，自动整理成一份结构化简历。</span>
        <el-button type="primary" :icon="MagicStick" @click="router.push('/resume-assistant')">
          开始引导
        </el-button>
      </div>
    </el-alert>

    <section class="content">
      <el-card shadow="never" class="editor-card card card--float">
        <el-form label-position="top">
          <el-form-item label="简历标题">
            <el-input v-model="form.title" maxlength="128" />
          </el-form-item>

          <el-form-item label="简历正文">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="18"
              resize="none"
              placeholder="粘贴你的简历、自我介绍、项目经历或技术栈。建议包含工作年限、核心项目、个人职责、技术亮点和求职目标。"
            />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="summary-card card card--float">
        <template #header><h2>简历摘要</h2></template>
        <el-skeleton v-if="resume.loading" :rows="4" animated />
        <el-empty v-else-if="!resume.profile" description="暂未保存默认简历" />
        <div v-else class="summary">
          <p>{{ resume.profile.summary || '暂无摘要' }}</p>
          <span>更新时间：{{ formatTime(resume.profile.updateTime) }}</span>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MagicStick, Upload } from '@element-plus/icons-vue'
import type { UploadRequestOptions } from 'element-plus'

import PageHeader from '@/components/common/PageHeader.vue'
import { useResumeStore } from '@/stores/resume.store'

const router = useRouter()
const resume = useResumeStore()

const form = reactive({
  title: '默认简历',
  content: '',
})

onMounted(() => {
  resume.fetchProfile()
})

watch(
  () => resume.profile,
  (profile) => {
    if (!profile) return
    form.title = profile.title
    form.content = profile.content
  },
)

const formatTime = (value?: string) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN')
}

const handleSave = async () => {
  if (!form.content.trim()) {
    ElMessage.warning('请先填写简历正文')
    return
  }

  await resume.saveProfile(form.title.trim() || '默认简历', form.content.trim())
  ElMessage.success('简历已保存')
}

const allowedExtensions = ['.txt', '.md', '.pdf', '.docx']

const beforeUpload = (file: File) => {
  const name = file.name.toLowerCase()
  const valid = allowedExtensions.some((ext) => name.endsWith(ext))
  if (!valid) {
    ElMessage.error('仅支持 .txt / .md / .pdf / .docx 格式')
    return false
  }
  return true
}

const handleUpload = async (options: UploadRequestOptions) => {
  try {
    const profile = await resume.uploadResume(options.file)
    form.title = profile.title
    form.content = profile.content
    ElMessage.success('简历文件已解析并回填')
  } catch {
    ElMessage.error(resume.errorMessage || '简历文件解析失败')
  }
}
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.page {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
}

.assistant-entry__body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  span {
    color: var(--c-text-secondary);
  }
}

.summary-card {
  align-self: start;

  h2 {
    margin: 0;
    font-size: var(--fs-lg);
    font-weight: var(--fw-semibold);
  }
}

.summary {
  display: grid;
  gap: 14px;

  p {
    margin: 0;
    color: var(--c-text-secondary);
    line-height: 1.8;
  }

  span {
    color: var(--c-text-tertiary);
    font-size: var(--fs-sm);
  }
}

@media (max-width: 1080px) {
  .content {
    grid-template-columns: 1fr;
  }
}

@include mobile {
  .page {
    gap: 12px;
    padding: 14px;
  }

  .content {
    gap: 12px;
  }

  .assistant-entry__body {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;

    .el-button {
      width: 100%;
      margin-left: 0;
    }
  }
}
</style>

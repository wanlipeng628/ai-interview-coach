<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p>我的简历</p>
        <h1>维护默认面试简历</h1>
        <span>这份简历会在开始模拟面试时自动作为 AI 面试官的上下文。</span>
      </div>
      <div class="header-actions">
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
      </div>
    </header>

    <section class="content">
      <el-card shadow="never" class="editor-card">
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

      <el-card shadow="never" class="summary-card">
        <template #header><h2>简历摘要</h2></template>
        <el-skeleton v-if="resume.loading" :rows="4" animated />
        <el-empty v-else-if="!resume.profile" description="暂未保存默认简历" />
        <div v-else class="summary">
          <p>{{ resume.profile.summary || '暂无摘要' }}</p>
          <span>更新时间：{{ resume.profile.updateTime || '-' }}</span>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import type { UploadRequestOptions } from 'element-plus'

import { useResumeStore } from '@/stores/resume.store'

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

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 24px;
  border-radius: 8px;
  background: #fff;

  .header-actions {
    display: flex;
    gap: 12px;
  }

  p {
    margin: 0 0 8px;
    color: #2f6bff;
    font-weight: 800;
  }

  h1 {
    margin: 0 0 8px;
    font-size: 24px;
  }

  span {
    color: #667085;
  }
}

.content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
}

.editor-card,
.summary-card {
  border: 0;
  border-radius: 8px;
}

.summary-card {
  align-self: start;

  h2 {
    margin: 0;
    font-size: 17px;
  }
}

.summary {
  display: grid;
  gap: 14px;

  p {
    margin: 0;
    color: #344054;
    line-height: 1.8;
  }

  span {
    color: #667085;
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

  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
    padding: 18px;

    h1 {
      font-size: 20px;
    }
  }

  .header-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;

    .el-button {
      width: 100%;
    }
  }

  .content {
    gap: 12px;
  }
}
</style>

<template>
  <div class="app">
    <header class="header">
      <h1>文档摘要与问答 MVP</h1>
      <p>上传文本文件即可生成摘要，并基于内容进行问答（含引用来源）。</p>
    </header>

    <section class="card">
      <h2>1. 上传文本文件</h2>
      <div class="uploader">
        <input type="file" accept="text/*" @change="onFileChange" />
        <button :disabled="uploading || !selectedFile" @click="uploadFile">
          {{ uploading ? '上传中...' : '开始上传' }}
        </button>
      </div>
      <p class="hint">支持 .txt / text/* 文件，大小建议 &lt; 200KB。</p>
      <p v-if="uploadError" class="error">{{ uploadError }}</p>
      <div v-if="uploadResult" class="result">
        <p><strong>文件：</strong>{{ uploadResult.filename }}</p>
        <p><strong>文档ID：</strong>{{ uploadResult.doc_id }}</p>
        <p><strong>摘要：</strong>{{ uploadResult.summary }}</p>
        <p><strong>词数：</strong>{{ uploadResult.word_count }}</p>
      </div>
    </section>

    <section class="card" :class="{ disabled: !uploadResult }">
      <h2>2. 问答（含引用）</h2>
      <div class="qa">
        <input
          v-model="question"
          type="text"
          placeholder="输入你的问题，例如：这篇文章主要讲什么？"
          :disabled="!uploadResult || asking"
        />
        <button :disabled="!uploadResult || asking" @click="askQuestion">
          {{ asking ? '思考中...' : '提问' }}
        </button>
      </div>
      <p v-if="askError" class="error">{{ askError }}</p>
      <div v-if="askResult" class="result">
        <p><strong>回答：</strong></p>
        <p class="answer">{{ askResult.answer }}</p>
        <div v-if="askResult.sources.length" class="sources">
          <h3>引用来源</h3>
          <ul>
            <li v-for="source in askResult.sources" :key="source.index">
              <span class="badge">#{{ source.index }}</span>
              {{ source.snippet }}
            </li>
          </ul>
        </div>
        <p v-else class="hint">暂时没有命中来源，尝试换个问题。</p>
      </div>
    </section>

    <footer class="footer">
      <p>后端接口默认地址：{{ apiBase }}</p>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const selectedFile = ref(null)
const uploadResult = ref(null)
const uploadError = ref('')
const uploading = ref(false)

const question = ref('')
const askResult = ref(null)
const askError = ref('')
const asking = ref(false)

const onFileChange = (event) => {
  const [file] = event.target.files
  selectedFile.value = file || null
  uploadError.value = ''
  uploadResult.value = null
  askResult.value = null
  question.value = ''
}

const uploadFile = async () => {
  if (!selectedFile.value) return
  uploadError.value = ''
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const response = await fetch(`${apiBase}/api/upload`, {
      method: 'POST',
      body: formData
    })

    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '上传失败，请稍后重试。')
    }

    uploadResult.value = data
  } catch (error) {
    uploadError.value = error.message
  } finally {
    uploading.value = false
  }
}

const askQuestion = async () => {
  if (!question.value.trim() || !uploadResult.value) return
  askError.value = ''
  asking.value = true
  try {
    const response = await fetch(`${apiBase}/api/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        doc_id: uploadResult.value.doc_id,
        question: question.value
      })
    })

    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '提问失败，请稍后重试。')
    }

    askResult.value = data
  } catch (error) {
    askError.value = error.message
  } finally {
    asking.value = false
  }
}
</script>

<style scoped>
:global(body) {
  margin: 0;
  font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #f6f7fb;
  color: #1f2a37;
}

.app {
  max-width: 960px;
  margin: 0 auto;
  padding: 40px 24px 60px;
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header h1 {
  font-size: 28px;
  margin-bottom: 8px;
}

.card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}

.card.disabled {
  opacity: 0.6;
}

.uploader,
.qa {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

input[type='file'] {
  padding: 6px;
}

input[type='text'] {
  flex: 1;
  min-width: 240px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #d0d5dd;
  font-size: 14px;
}

button {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 10px 18px;
  cursor: pointer;
  font-size: 14px;
}

button:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.result {
  margin-top: 16px;
  background: #f8fafc;
  padding: 16px;
  border-radius: 12px;
}

.answer {
  white-space: pre-line;
}

.sources ul {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
}

.sources li {
  padding: 8px 0;
  border-bottom: 1px solid #e2e8f0;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #e2e8f0;
  color: #1f2937;
  border-radius: 999px;
  font-size: 12px;
  padding: 2px 8px;
  margin-right: 8px;
}

.hint {
  color: #667085;
  font-size: 13px;
}

.error {
  color: #dc2626;
  font-size: 14px;
}

.footer {
  text-align: center;
  font-size: 13px;
  color: #64748b;
}
</style>

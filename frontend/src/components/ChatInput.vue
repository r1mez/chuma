<template>
  <div class="chat-input">
    <el-input
      v-model="input"
      type="textarea"
      :rows="2"
      :autosize="{ minRows: 1, maxRows: 4 }"
      placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
      @keydown="handleKeydown"
      :disabled="loading"
    />
    <el-button
      type="primary"
      :icon="Promotion"
      :loading="loading"
      :disabled="!input.trim()"
      @click="handleSend"
    >
      发送
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Promotion } from '@element-plus/icons-vue'

const props = defineProps<{ loading: boolean }>()
const emit = defineEmits<{ send: [content: string] }>()

const input = ref('')

function handleSend() {
  const text = input.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  input.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<style scoped>
.chat-input {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding: 16px;
  border-top: 1px solid #e4e7ed;
  background: white;
}
.chat-input :deep(.el-textarea) {
  flex: 1;
}
</style>

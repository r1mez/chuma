<template>
  <div class="composer" :class="{ prominent }">
    <textarea
      ref="textareaRef"
      v-model="input"
      :placeholder="placeholder"
      :disabled="loading"
      rows="1"
      @keydown="handleKeydown"
      @input="adjustHeight"
    />
    <div class="composer-footer">
      <span class="composer-tip">Enter 发送 · Shift + Enter 换行</span>
      <button class="send-button" type="button" :disabled="!loading && !input.trim()" :title="loading ? '停止生成' : '发送消息'" @click="loading ? emit('cancel') : handleSend()">
        <Square v-if="loading" :size="14" fill="currentColor" />
        <template v-else><ArrowUp :size="17" /><span>发送</span></template>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { ArrowUp, Square } from 'lucide-vue-next'
const props = withDefaults(defineProps<{ loading: boolean; placeholder?: string; prominent?: boolean }>(), {
  placeholder: '输入你的问题…', prominent: false,
})
const emit = defineEmits<{ send: [content: string]; cancel: [] }>()
const input = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
function handleSend() {
  const text = input.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  input.value = ''
  nextTick(resetHeight)
}
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleSend() }
}
function adjustHeight() {
  const element = textareaRef.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, props.prominent ? 116 : 96)}px`
}
function resetHeight() { if (textareaRef.value) textareaRef.value.style.height = props.prominent ? '88px' : '28px' }
watch(() => props.prominent, () => nextTick(resetHeight), { immediate: true })
</script>

<style scoped>
.composer { width: 100%; padding: 10px; border: 1px solid #dce3ec; border-radius: 11px; background: #fff; box-shadow: 0 10px 30px rgba(16, 24, 40, .07); transition: border-color .15s, box-shadow .15s; }
.composer:focus-within { border-color: #aebbd1; box-shadow: 0 10px 30px rgba(16, 24, 40, .08), 0 0 0 3px rgba(33, 70, 155, .05); }
.composer textarea { width: 100%; height: 28px; min-height: 28px; display: block; resize: none; padding: 8px 9px; border: 0; outline: 0; color: #172033; background: #f7f8fa; border-radius: 8px; font: inherit; font-size: 14px; line-height: 1.6; }
.composer.prominent textarea { height: 88px; min-height: 88px; padding: 13px 14px; }
.composer textarea::placeholder { color: #98a4b7; }
.composer-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 9px 3px 0 7px; }
.composer-tip { color: #a0a9b8; font-size: 11px; }
.send-button { min-width: 72px; height: 36px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 0; border-radius: 8px; color: #fff; background: #10182b; font-size: 13px; font-weight: 600; cursor: pointer; }
.send-button:hover { background: #21469b; }
.send-button:disabled { opacity: .4; cursor: not-allowed; }
@media (max-width: 600px) { .composer-tip { display: none; } }
</style>

<template>
  <div class="composer" :class="{ prominent }">
    <textarea
      ref="textareaRef"
      v-model="input"
      :placeholder="placeholder"
      :disabled="loading"
      aria-label="输入消息"
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
function resetHeight() { if (textareaRef.value) textareaRef.value.style.height = props.prominent ? '64px' : '30px' }
watch(() => props.prominent, () => nextTick(resetHeight), { immediate: true })
</script>

<style scoped>
.composer {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--workspace-border);
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 5px 18px rgba(33, 70, 155, .06);
  transition: border-color .18s ease, box-shadow .18s ease;
}
.composer:focus-within {
  border-color: #9fb2d2;
  box-shadow: 0 5px 18px rgba(33, 70, 155, .08), 0 0 0 3px rgba(33, 70, 155, .07);
}
.composer textarea {
  width: 100%;
  height: 30px;
  min-height: 30px;
  display: block;
  resize: none;
  padding: 8px 10px;
  border: 0;
  outline: 0;
  box-sizing: border-box;
  color: var(--workspace-text);
  background: transparent;
  border-radius: 10px;
  font: inherit;
  font-size: 14px;
  line-height: 1.6;
  transition: background-color .18s ease;
}
.composer textarea:focus { background: #fff; }
.composer.prominent textarea { height: 64px; min-height: 64px; padding: 8px 10px; }
.composer textarea::placeholder { color: #9aa8bc; }
.composer-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 8px 2px 0 4px; }
.composer-tip { color: #8b9ab0; font-size: 11px; }
.send-button {
  min-width: 78px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 0;
  border-radius: 10px;
  color: #fff;
  background: var(--workspace-primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: none;
  transition: background-color .18s ease, box-shadow .18s ease, transform .18s ease;
}
.send-button:hover:not(:disabled) { background: var(--workspace-primary-hover); box-shadow: 0 5px 12px rgba(33, 70, 155, .18); transform: translateY(-1px); }
.send-button:focus-visible { outline: 3px solid rgba(33, 70, 155, .2); outline-offset: 2px; }
.send-button:disabled { opacity: .42; cursor: not-allowed; box-shadow: none; }
@media (max-width: 600px) {
  .composer-tip { display: none; }
  .composer-footer { justify-content: flex-end; }
}
</style>

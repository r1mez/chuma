<template>
  <div class="nav-container">
    <svg width="0" height="0" class="absolute">
      <defs>
        <filter id="goo">
          <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur" />
          <feColorMatrix
            in="blur"
            type="matrix"
            values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -7"
            result="goo"
          />
          <feBlend in="SourceGraphic" in2="goo" />
        </filter>
      </defs>
    </svg>

    <div class="nav-links">
      <div 
        class="nav-indicator" 
        :style="{ 
          transform: `translateX(${indicatorPosition}px)`,
          width: `${indicatorWidth}px` 
        }"
      ></div>
      <button
        v-for="(item, index) in items"
        :key="index"
        ref="itemRefs"
        class="nav-item"
        :class="{ 'active': modelValue === item.value, 'disabled': item.disabled }"
        :disabled="item.disabled"
        @click="!item.disabled && $emit('update:modelValue', item.value)"
      >
        {{ item.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'

export interface NavItem {
  label: string
  value: string
  disabled?: boolean
}

const props = defineProps<{
  items: NavItem[]
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const itemRefs = ref<HTMLElement[]>([])
const indicatorPosition = ref(0)
const indicatorWidth = ref(0)

const updateIndicator = () => {
  const activeIndex = props.items.findIndex(item => item.value === props.modelValue)
  if (activeIndex === -1 || !itemRefs.value[activeIndex]) return

  const activeElement = itemRefs.value[activeIndex]
  indicatorPosition.value = activeElement.offsetLeft
  indicatorWidth.value = activeElement.offsetWidth
}

onMounted(() => {
  nextTick(updateIndicator)
})

watch(() => props.modelValue, () => {
  nextTick(updateIndicator)
})
</script>

<style scoped>
.nav-container {
  position: relative;
  display: inline-block;
  filter: url(#goo);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f1f5f9;
  padding: 8px;
  border-radius: 999px;
  position: relative;
}

.nav-indicator {
  position: absolute;
  top: 8px;
  left: 0;
  height: calc(100% - 16px);
  background: #58bc82; /* 绿色主题色 */
  border-radius: 999px;
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1), width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1;
}

.nav-item {
  position: relative;
  z-index: 2;
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 999px;
  transition: color 0.3s ease;
  white-space: nowrap;
}

.nav-item.active {
  color: white;
}

.nav-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.nav-item:not(.disabled):hover {
  color: #1e293b;
}

.nav-item.active:hover {
  color: white;
}
</style>

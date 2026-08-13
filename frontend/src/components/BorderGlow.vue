<template>
  <div :class="['flat-surface', className]" :style="{ borderRadius: `${borderRadius}px` }">
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  className?: string
  backgroundColor?: string
  borderRadius?: number
  glowColor?: string
  glowRadius?: number
  glowIntensity?: number
  coneSpread?: number
  fillOpacity?: number
}>(), {
  className: '',
  borderRadius: 0,
})
</script>

<style scoped>
.flat-surface {
  position: relative;
  width: 100%;
  background: transparent;
  box-shadow: none;
}
</style>

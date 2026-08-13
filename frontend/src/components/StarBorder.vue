<template>
  <component :is="as" class="flat-border-container" :class="customClass" v-bind="$attrs">
    <slot />
  </component>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  as?: string | object
  customClass?: string
  color?: string
  speed?: string
  thickness?: number
}>(), { as: 'button', customClass: '' })
</script>

<style scoped>
.flat-border-container {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dfe5ed;
  border-radius: 7px;
  background: #fff;
  vertical-align: middle;
}
.flat-border-container :deep(.el-button) { margin: 0; border: 0; }
</style>

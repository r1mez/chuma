<template><WorkspaceLayout :items="items" role-label="管理工作台" /></template>
<script setup lang="ts">
import WorkspaceLayout, { type WorkspaceItem } from './WorkspaceLayout.vue'
const items: WorkspaceItem[] = [
  { path: '/admin/ocr', label: '文档解析', icon: 'ScanText', description: '解析和管理课程 PDF 与图片文档。' },
  { path: '/admin/kg-pipeline', label: '图谱构建', icon: 'Workflow', description: '查看知识图谱构建流程和任务状态。' },
  { path: '/admin/students', label: '学生管理', icon: 'School', description: '维护学生信息与班级归属。' },
  { path: '/admin/alerts', label: '预警面板', icon: 'Bell', description: '查看并处理系统学情预警。' },
]
</script>

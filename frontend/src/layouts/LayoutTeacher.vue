<template><WorkspaceLayout :items="items" role-label="教师工作台" /></template>
<script setup lang="ts">
import WorkspaceLayout, { type WorkspaceItem } from './WorkspaceLayout.vue'
const items: WorkspaceItem[] = [
  { path: '/teacher/dashboard', label: '学情概览', icon: 'ChartNoAxesCombined', description: '掌握班级表现、进度与知识点薄弱情况。' },
  { path: '/teacher/chat', label: 'AI 助教', icon: 'MessageSquare', description: '使用 AI 辅助教学分析与内容准备。' },
  { path: '/teacher/class-assistant', label: '班级分析', icon: 'Bot', description: '生成面向班级的智能学情分析。' },
  { path: '/teacher/interactive', label: '互动专区', icon: 'Users', description: '管理师生讨论与课程互动。' },
  { path: '/teacher/subject', label: '学科管理', icon: 'BookOpen', description: '维护课程、章节与知识内容。' },
  { path: '/teacher/kg-manage', label: '图谱管理', icon: 'Network', description: '维护课程知识图谱结构。' },
  { path: '/teacher/lesson-plans', label: '教案生成', icon: 'Presentation', description: '结合知识图谱与班级学情生成可编辑课件。' },
  { path: '/teacher/assignments', label: '作业布置', icon: 'CalendarRange', description: '结合班级学情和题目推荐发布作业。' },
]
</script>

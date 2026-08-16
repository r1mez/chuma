<template><WorkspaceLayout :items="items" role-label="学生工作台" /></template>
<script setup lang="ts">
import { computed } from 'vue'
import WorkspaceLayout, { type WorkspaceItem } from './WorkspaceLayout.vue'
import { unreadCount } from '@/store/messages'
const items = computed<WorkspaceItem[]>(() => [
  { path: '/student/dashboard', label: '学习概览', icon: 'LayoutDashboard', description: '查看学习进度、个人评级与智能建议。' },
  { path: '/student/knowledge', label: '知识图谱', icon: 'Network', description: '探索课程知识结构与知识点关联。' },
  { path: '/student/practice', label: '题目练习', icon: 'Dumbbell', description: '按学科与难度开展针对性训练。' },
  { path: '/student/assignments', label: '我的作业', icon: 'CalendarRange', description: '完成教师布置的作业并查看提交进度。' },
  { path: '/student/exercise-records', label: '做题记录', icon: 'History', description: '回顾练习历史与错误归因。' },
  { path: '/student/chat', label: 'AI 助学', icon: 'MessageSquare', description: '获得基于课程知识的智能辅导。' },
  { path: '/student/plan', label: '学习计划', icon: 'CalendarRange', description: '规划学习目标并跟踪完成情况。' },
  { path: '/student/interactive', label: '互动专区', icon: 'Users', description: '参与课程讨论与师生互动。' },
  { path: '/student/messages', label: '消息提醒', icon: 'Bell', description: '查看课程通知和互动消息。', badge: unreadCount.value },
])
</script>

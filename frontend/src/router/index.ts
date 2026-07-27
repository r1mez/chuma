import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: () => import('@/pages/auth/Login.vue'),
    },
    {
      path: '/register',
      component: () => import('@/pages/auth/Register.vue'),
    },
    {
      path: '/student',
      component: () => import('@/layouts/DefaultLayout.vue'),
      children: [
        { path: 'dashboard', component: () => import('@/pages/student/Dashboard.vue') },
        { path: 'knowledge', component: () => import('@/pages/student/KnowledgeExplore.vue') },
        { path: 'practice', component: () => import('@/pages/student/PracticeHome.vue') },
        { path: 'practice/panel', component: () => import('@/pages/student/Practice.vue') },
        { path: 'exercise-records', component: () => import('@/pages/student/ExerciseRecords.vue') },
        { path: 'subject-records', component: () => import('@/pages/student/SubjectRecords.vue') },
        { path: 'chat', component: () => import('@/pages/student/Chat.vue') },
        { path: 'plan', component: () => import('@/pages/student/LearningPlan.vue') },
        { path: 'ocr', component: () => import('@/pages/student/OcrParse.vue') },
        { path: 'kg-pipeline', component: () => import('@/pages/student/KgPipeline.vue') },
        { path: 'interactive', component: () => import('@/pages/student/InteractiveZone.vue') },
        { path: 'interactive/:id', component: () => import('@/pages/student/InteractiveDetail.vue') },
        { path: 'messages', component: () => import('@/pages/student/MessageNotifications.vue') },
      ],
    },
    {
      path: '/teacher',
      component: () => import('@/layouts/TeacherLayout.vue'),
      children: [
        { path: 'dashboard', component: () => import('@/pages/teacher/Analytics.vue') },
        { path: 'chat', component: () => import('@/pages/teacher/Chat.vue') },
        { path: 'interactive', component: () => import('@/pages/teacher/InteractiveZone.vue') },
        { path: 'subject', component: () => import('@/pages/teacher/SubjectManage.vue') },
      ],
    },
    {
      path: '/',
      redirect: '/login',
    },
  ],
})

export default router

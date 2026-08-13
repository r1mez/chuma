<template>
  <div class="workspace-shell">
    <aside class="workspace-sidebar" :class="{ collapsed }">
      <div class="brand">
        <div class="brand-mark"><GraduationCap :size="20" /></div>
        <div v-if="!collapsed" class="brand-copy">
          <strong>智教慧学</strong>
          <span>{{ roleLabel }}</span>
        </div>
      </div>

      <div v-if="!collapsed" class="nav-caption">工作区</div>
      <nav class="workspace-nav">
        <RouterLink v-for="item in items" :key="item.path" :to="item.path" class="nav-item" :title="item.label">
          <component :is="icons[item.icon] || Circle" :size="18" />
          <span v-if="!collapsed">{{ item.label }}</span>
          <span v-if="item.badge && item.badge > 0" class="nav-badge">{{ item.badge }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-footer">
        <div v-if="!collapsed" class="user-block">
          <span class="avatar">{{ userInitial }}</span>
          <span class="user-copy"><strong>{{ userName }}</strong><small>{{ roleLabel }}</small></span>
        </div>
        <button class="sidebar-action" title="退出登录" @click="logout"><LogOut :size="17" /><span v-if="!collapsed">退出登录</span></button>
        <button class="sidebar-action" :title="collapsed ? '展开导航' : '收起导航'" @click="collapsed = !collapsed">
          <PanelLeftOpen v-if="collapsed" :size="17" />
          <PanelLeftClose v-else :size="17" />
          <span v-if="!collapsed">收起导航</span>
        </button>
      </div>
    </aside>

    <main class="workspace-main">
      <header class="workspace-header">
        <div>
          <h1>{{ currentItem?.label || '工作台' }}</h1>
          <p>{{ currentItem?.description || '专注学习过程，让知识更清晰。' }}</p>
        </div>
        <div class="header-meta"><span class="status-dot"></span>服务正常</div>
      </header>
      <section class="workspace-content"><router-view /></section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { unreadCount } from '@/store/messages'
import {
  GraduationCap, LayoutDashboard, Network, Dumbbell, History, MessageSquare,
  CalendarRange, Users, Bell, ScanText, Workflow, BookOpen, Bot,
  LogOut, PanelLeftOpen, PanelLeftClose, Circle, ChartNoAxesCombined, School
} from 'lucide-vue-next'

export interface WorkspaceItem { path: string; label: string; icon: string; description?: string; badge?: number }
const props = defineProps<{ items: WorkspaceItem[]; roleLabel: string }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)
const icons: Record<string, any> = { LayoutDashboard, Network, Dumbbell, History, MessageSquare, CalendarRange, Users, Bell, ScanText, Workflow, BookOpen, Bot, ChartNoAxesCombined, School }
const currentItem = computed(() => [...props.items].sort((a, b) => b.path.length - a.path.length).find(item => route.path.startsWith(item.path)))
const userName = computed(() => auth.user?.name || '当前用户')
const userInitial = computed(() => userName.value.slice(0, 1).toUpperCase())

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.workspace-shell { min-height: 100vh; display: flex; background: #f7f8fb; color: #172033; }
.workspace-sidebar { width: 240px; height: 100vh; position: sticky; top: 0; flex: 0 0 auto; display: flex; flex-direction: column; box-sizing: border-box; padding: 20px 14px 14px; background: #f4f6f9; border-right: 1px solid #e2e7ef; transition: width .2s ease; }
.workspace-sidebar.collapsed { width: 72px; }
.brand { height: 44px; display: flex; align-items: center; gap: 11px; padding: 0 7px; }
.brand-mark { width: 34px; height: 34px; display: grid; place-items: center; flex: none; color: #fff; background: #21469b; border-radius: 9px; }
.brand-copy { display: flex; min-width: 0; flex-direction: column; line-height: 1.2; }
.brand-copy strong { color: #101828; font-size: 15px; white-space: nowrap; }
.brand-copy span { margin-top: 4px; color: #8a96a8; font-size: 11px; }
.nav-caption { margin: 27px 10px 8px; color: #98a2b3; font-size: 12px; }
.workspace-nav { display: flex; flex: 1; flex-direction: column; gap: 4px; overflow-y: auto; padding-top: 14px; }
.nav-item { min-height: 40px; display: flex; align-items: center; gap: 11px; padding: 0 12px; border-radius: 8px; color: #526078; font-size: 14px; text-decoration: none; transition: background .15s, color .15s; }
.nav-item:hover { color: #172033; background: #e9edf3; }
.nav-item.router-link-active { color: #fff; background: #10182b; }
.nav-item svg { flex: none; }
.nav-badge { margin-left: auto; min-width: 18px; height: 18px; display: grid; place-items: center; border-radius: 9px; color: #fff; background: #e5484d; font-size: 10px; }
.sidebar-footer { display: flex; flex-direction: column; gap: 4px; padding-top: 12px; border-top: 1px solid #e2e7ef; }
.user-block { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; padding: 8px; border: 1px solid #e2e7ef; border-radius: 9px; background: #fff; }
.avatar { width: 30px; height: 30px; display: grid; place-items: center; flex: none; border-radius: 50%; color: #fff; background: #21469b; font-size: 13px; font-weight: 700; }
.user-copy { min-width: 0; display: flex; flex-direction: column; }
.user-copy strong { overflow: hidden; color: #344054; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.user-copy small { margin-top: 2px; color: #98a2b3; font-size: 10px; }
.sidebar-action { width: 100%; min-height: 37px; display: flex; align-items: center; gap: 10px; padding: 0 11px; border: 0; border-radius: 7px; color: #667085; background: transparent; cursor: pointer; }
.sidebar-action:hover { color: #172033; background: #e9edf3; }
.workspace-main { min-width: 0; flex: 1; }
.workspace-header { min-height: 108px; display: flex; align-items: center; justify-content: space-between; gap: 24px; box-sizing: border-box; padding: 28px clamp(24px, 4vw, 64px) 22px; background: #fff; border-bottom: 1px solid #e2e7ef; }
.workspace-header h1 { margin: 0; color: #101828; font-size: 25px; line-height: 1.25; font-weight: 700; letter-spacing: -.02em; }
.workspace-header p { margin: 7px 0 0; color: #7a8699; font-size: 13px; }
.header-meta { display: flex; align-items: center; gap: 7px; color: #667085; font-size: 12px; white-space: nowrap; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: #12a150; }
.workspace-content { box-sizing: border-box; min-height: calc(100vh - 108px); padding: 28px clamp(24px, 4vw, 64px) 48px; }
@media (max-width: 760px) {
  .workspace-sidebar { width: 72px; padding-inline: 9px; }
  .brand-copy, .nav-caption, .nav-item span:not(.nav-badge), .user-block, .sidebar-action span { display: none; }
  .workspace-header { padding-inline: 20px; }
  .workspace-content { padding: 20px; }
  .header-meta { display: none; }
}
</style>

<template>
  <div class="workspace-shell">
    <aside
      class="workspace-sidebar"
      :class="{ collapsed, 'is-transitioning': sidebarTransitioning }"
      @transitionend="handleSidebarTransitionEnd"
    >
      <div class="brand">
        <div class="brand-mark"><GraduationCap :size="20" /></div>
        <div v-if="!collapsed" class="brand-copy">
          <strong>智教慧学</strong>
          <span>{{ roleLabel }}</span>
        </div>
      </div>

      <div v-if="!collapsed" class="nav-caption">工作区</div>
      <nav class="workspace-nav" aria-label="工作区导航">
        <RouterLink v-for="item in items" :key="item.path" :to="item.path" class="nav-item" :title="item.label" :aria-current="route.path.startsWith(item.path) ? 'page' : undefined">
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
        <button class="sidebar-action" :title="collapsed ? '展开导航' : '收起导航'" @click="toggleSidebar">
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
      </header>
      <section class="workspace-content" :class="{ 'chat-content': isChatRoute }"><router-view /></section>
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
  LogOut, PanelLeftOpen, PanelLeftClose, Circle, ChartNoAxesCombined, School, Presentation
} from 'lucide-vue-next'

export interface WorkspaceItem { path: string; label: string; icon: string; description?: string; badge?: number }
const props = defineProps<{ items: WorkspaceItem[]; roleLabel: string }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)
const sidebarTransitioning = ref(false)
const isChatRoute = computed(() => route.path.startsWith('/student/chat'))
const icons: Record<string, any> = { LayoutDashboard, Network, Dumbbell, History, MessageSquare, CalendarRange, Users, Bell, ScanText, Workflow, BookOpen, Bot, ChartNoAxesCombined, School, Presentation }
const currentItem = computed(() => [...props.items].sort((a, b) => b.path.length - a.path.length).find(item => route.path.startsWith(item.path)))
const userName = computed(() => auth.user?.name || '当前用户')
const userInitial = computed(() => userName.value.slice(0, 1).toUpperCase())

function logout() {
  auth.logout()
  router.push('/login')
}

function toggleSidebar() {
  sidebarTransitioning.value = true
  collapsed.value = !collapsed.value
}

function handleSidebarTransitionEnd(event: TransitionEvent) {
  if (event.propertyName === 'width') {
    sidebarTransitioning.value = false
  }
}
</script>

<style scoped>
.workspace-shell { min-height: 100vh; display: flex; background: var(--workspace-subtle); color: var(--workspace-text); }
.workspace-sidebar { width: 240px; height: 100vh; position: sticky; top: 0; flex: 0 0 auto; display: flex; flex-direction: column; box-sizing: border-box; padding: 20px 14px 14px; overflow: hidden; background: #f3f6fb; border-right: 1px solid var(--workspace-border); transition: width .2s ease; }
.workspace-sidebar.collapsed { width: 72px; }
.brand { height: 44px; display: flex; align-items: center; gap: 11px; padding: 0 7px; }
.brand-mark { width: 34px; height: 34px; display: grid; place-items: center; flex: none; color: #fff; background: linear-gradient(145deg, #2d5ac0, #21469b); border-radius: 10px; box-shadow: 0 5px 12px rgba(33, 70, 155, .18); }
.brand-copy { display: flex; min-width: 0; flex-direction: column; line-height: 1.2; }
.brand-copy strong { color: var(--workspace-heading); font-size: 15px; white-space: nowrap; }
.brand-copy span { margin-top: 4px; color: var(--workspace-subtle-text); font-size: 11px; }
.nav-caption { margin: 27px 10px 8px; color: var(--workspace-subtle-text); font-size: 11px; letter-spacing: .08em; }
.workspace-nav { min-width: 0; display: flex; flex: 1; flex-direction: column; gap: 4px; overflow-x: hidden; overflow-y: auto; padding-top: 14px; scrollbar-width: none; }
.workspace-nav::-webkit-scrollbar { width: 0; height: 0; }
.nav-item { min-height: 42px; display: flex; align-items: center; gap: 11px; padding: 0 12px; border: 1px solid transparent; border-radius: 10px; color: #526078; font-size: 14px; text-decoration: none; transition: background .18s ease, color .18s ease, border-color .18s ease; }
.nav-item:hover { color: var(--workspace-heading); background: #e9eff8; }
.nav-item.router-link-active { color: var(--workspace-primary); background: var(--workspace-primary-soft); border-color: var(--workspace-primary-border); font-weight: 600; box-shadow: inset 3px 0 0 var(--workspace-primary); }
.nav-item svg { flex: none; }
.nav-badge { margin-left: auto; min-width: 19px; height: 19px; display: grid; place-items: center; border-radius: 10px; color: #fff; background: var(--workspace-danger); font-size: 10px; font-variant-numeric: tabular-nums; }
.workspace-sidebar.collapsed .workspace-nav { overflow: hidden; }
.workspace-sidebar.collapsed .nav-item { width: 100%; box-sizing: border-box; justify-content: center; gap: 0; padding-inline: 0; }
.workspace-sidebar.collapsed .nav-badge { display: none; }
.workspace-sidebar.is-transitioning .workspace-nav { overflow: hidden; }
.workspace-sidebar.is-transitioning .nav-item { width: 100%; box-sizing: border-box; justify-content: center; gap: 0; padding-inline: 0; }
.workspace-sidebar.is-transitioning .brand-copy,
.workspace-sidebar.is-transitioning .nav-caption,
.workspace-sidebar.is-transitioning .nav-item > span,
.workspace-sidebar.is-transitioning .user-block,
.workspace-sidebar.is-transitioning .sidebar-action span { display: none; }
.sidebar-footer { display: flex; flex-direction: column; gap: 4px; padding-top: 12px; border-top: 1px solid var(--workspace-border); }
.user-block { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; padding: 8px; border: 1px solid var(--workspace-border); border-radius: 10px; background: #fff; box-shadow: 0 1px 2px rgba(16, 24, 40, .02); }
.avatar { width: 30px; height: 30px; display: grid; place-items: center; flex: none; border-radius: 50%; color: #fff; background: var(--workspace-primary); font-size: 13px; font-weight: 700; }
.user-copy { min-width: 0; display: flex; flex-direction: column; }
.user-copy strong { overflow: hidden; color: #344054; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.user-copy small { margin-top: 2px; color: #98a2b3; font-size: 10px; }
.sidebar-action { width: 100%; min-height: 38px; display: flex; align-items: center; gap: 10px; padding: 0 11px; border: 0; border-radius: 8px; color: var(--workspace-muted); background: transparent; cursor: pointer; transition: color .18s ease, background-color .18s ease; }
.sidebar-action:hover { color: var(--workspace-heading); background: #e9eff8; }
.workspace-main { min-width: 0; flex: 1; background: radial-gradient(circle at 88% 0%, rgba(33, 70, 155, .055), transparent 340px), var(--workspace-subtle); }
.workspace-header { position: relative; min-height: 108px; display: flex; align-items: center; justify-content: space-between; gap: 24px; box-sizing: border-box; padding: 28px clamp(24px, 4vw, 64px) 22px; background: #fff; border-bottom: 1px solid var(--workspace-border); box-shadow: 0 1px 0 rgba(16, 24, 40, .02); overflow: hidden; }
.workspace-header::after { content: ""; position: absolute; right: clamp(24px, 4vw, 64px); bottom: -1px; left: clamp(24px, 4vw, 64px); height: 1px; background: linear-gradient(90deg, transparent, rgba(33, 70, 155, .16), rgba(15, 159, 140, .18), transparent); pointer-events: none; }
.workspace-header h1 { margin: 0; color: var(--workspace-heading); font-size: 25px; line-height: 1.25; font-weight: 700; letter-spacing: -.02em; }
.workspace-header p { margin: 7px 0 0; color: #7a8699; font-size: 13px; }
.workspace-content { position: relative; box-sizing: border-box; min-height: calc(100vh - 108px); padding: 28px clamp(24px, 4vw, 64px) 48px; }
.workspace-content.chat-content { height: calc(100vh - 108px); min-height: 0; padding: 0; }
@media (max-width: 760px) {
  .workspace-sidebar { width: 72px; padding-inline: 9px; }
  .brand-copy, .nav-caption, .nav-item span:not(.nav-badge), .user-block, .sidebar-action span { display: none; }
  .workspace-header { padding-inline: 20px; }
  .workspace-content { padding: 20px; }
}
</style>

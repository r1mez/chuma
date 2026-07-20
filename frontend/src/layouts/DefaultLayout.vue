<template>
  <div class="relative w-screen h-screen overflow-hidden bg-transparent font-sans">
    <!-- 背景特效 -->
    <FloatingLines class="fixed inset-0 z-0" mixBlendMode="normal" />

    <!-- 左上角控制面板切换按钮 -->
    <button 
      @click="toggleMenu"
      class="fixed top-6 left-6 z-50 p-3 rounded-2xl bg-white/60 backdrop-blur-xl border border-white/50 shadow-lg hover:bg-white/90 hover:scale-105 transition-all cursor-pointer flex items-center justify-center group"
      title="控制面板"
    >
      <LayoutGrid class="w-6 h-6 text-gray-700 group-hover:text-blue-500 transition-colors" />
    </button>

    <!-- 主内容区（子页面渲染处） -->
    <div class="relative z-10 w-full h-full overflow-auto pt-24 px-8 pb-8">
      <router-view />
    </div>

    <!-- Magic Bento 控制面板悬浮层 -->
    <transition name="fade-scale">
      <div 
        v-show="isMenuOpen" 
        class="fixed inset-0 z-40 flex items-center justify-center bg-black/20 backdrop-blur-md"
        @click.self="toggleMenu"
      >
        <div 
          ref="bentoRef"
          class="grid grid-cols-4 grid-rows-2 gap-6 w-[75%] max-w-[1200px] min-w-[800px] aspect-[2/1]"
          @mousemove="handleMouseMove"
        >
          <div 
            v-for="item in menuItems" 
            :key="item.path"
            @click="handleNav(item.path)"
            class="bento-card group"
          >
            <div class="bento-card-inner">
              <span class="text-2xl font-bold text-gray-800 tracking-wider group-hover:text-blue-600 transition-colors">
                {{ item.name }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { LayoutGrid } from 'lucide-vue-next'
import FloatingLines from '@/components/FloatingLines.vue'

const router = useRouter()
const route = useRoute()

// 控制面板是否打开的响应式状态
const isMenuOpen = ref(true)

// 当在特定子页面刷新时，可选择自动隐藏面板
onMounted(() => {
  // 如果直接进入了具体的子页面（例如 /student/chat），则默认收起面板以便于直接看到内容
  if (route.path !== '/student' && route.path !== '/student/dashboard') {
    isMenuOpen.value = false
  }
})

// 菜单配置
const menuItems = [
  { name: '学习仪表盘', path: '/student/dashboard' },
  { name: '知识图谱', path: '/student/knowledge' },
  { name: '题目练习', path: '/student/practice' },
  { name: '做题记录', path: '/student/exercise-records' },
  { name: 'AI 助教', path: '/student/chat' },
  { name: '学习计划', path: '/student/plan' },
  { name: '文档解析', path: '/student/ocr' },
  { name: '图谱构建', path: '/student/kg-pipeline' }
]

// 导航跳转逻辑
const handleNav = (path: string) => {
  isMenuOpen.value = false
  router.push(path)
}

// 切换菜单显示/隐藏
const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value
}

// Magic Bento 鼠标跟踪发光特效逻辑
const bentoRef = ref<HTMLElement | null>(null)
const handleMouseMove = (e: MouseEvent) => {
  if (!bentoRef.value) return
  const cards = bentoRef.value.querySelectorAll('.bento-card') as NodeListOf<HTMLElement>
  for (const card of cards) {
    const rect = card.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    // 注入 CSS 变量，供伪元素实现径向渐变跟随
    card.style.setProperty('--mouse-x', `${x}px`)
    card.style.setProperty('--mouse-y', `${y}px`)
  }
}
</script>

<style scoped>
/* 悬浮层过渡动画 */
.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.fade-scale-enter-from,
.fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* Magic Bento 卡片基础样式 */
.bento-card {
  position: relative;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 1.5rem;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

/* 悬浮时的卡片上浮和阴影加深 */
.bento-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
  border-color: rgba(255, 255, 255, 0.9);
}

/* 光晕伪元素（鼠标跟踪的核心实现） */
.bento-card::before {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  border-radius: inherit;
  opacity: 0;
  transition: opacity 0.3s ease;
  /* 利用 JS 注入的 CSS 变量绘制跟随鼠标的径向渐变 */
  background: radial-gradient(
    300px circle at var(--mouse-x, 50%) var(--mouse-y, 50%),
    rgba(255, 255, 255, 0.9),
    transparent 40%
  );
  z-index: 1;
  pointer-events: none;
}

.bento-card:hover::before {
  opacity: 1;
}

/* 卡片内部内容层（放置文字） */
.bento-card-inner {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 增加轻微的玻璃质感渐变 */
  background: linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0.1) 100%);
  backdrop-filter: blur(12px);
}

/* --- 保留原有的透视特效和子组件穿透样式 --- */
:deep(.chat-page),
:deep(.kgp-page),
:deep(.ocr-page) {
  background: transparent !important;
}

:deep(.chat-header),
:deep(.chat-messages) {
  background: rgba(255, 255, 255, 0.6) !important;
  backdrop-filter: blur(10px);
}

:deep(.el-card) {
  background: rgba(255, 255, 255, 0.7) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.5) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
}
</style>

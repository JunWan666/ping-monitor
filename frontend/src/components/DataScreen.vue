<template>
  <div class="ds-frame">
    <div v-if="!ready" class="ds-loading">
      <div class="ds-spinner"></div>
      <p>正在加载可视化大屏…</p>
    </div>
    <iframe
      v-else
      ref="frameRef"
      class="ds-iframe"
      :src="frameSrc"
      title="PING 节点实时监控中心"
      allow="fullscreen"
      @load="onFrameLoad"
    ></iframe>
  </div>
</template>

<script setup>
/**
 * 可视化大屏：外壳只做入口判断，画面由 frontend/public/bigscreen/index.html 承载。
 * - 公开访问关闭时（非预览模式）跳登录页，与旧实现行为一致
 * - 预览模式（/datascreen-preview）通过 ?preview=1 让内嵌页走鉴权接口
 * - 内嵌页与外壳同域，可直接读 localStorage 里的 token，无需 postMessage 桥
 * - 旧版实现保留在 DataScreenLegacy.vue，需要回退时改 router.js 的引用即可
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()
const ready = ref(false)
const frameRef = ref(null)

const isPreviewMode = computed(() => Boolean(route.meta?.previewMode))

const frameSrc = computed(() =>
  isPreviewMode.value ? '/bigscreen/index.html?preview=1' : '/bigscreen/index.html'
)

const onFrameLoad = () => {
  // 外层文档标题跟随内嵌大屏（品牌名由后端 screen_config.brand_name 决定）
  try {
    const innerTitle = frameRef.value?.contentDocument?.title
    if (innerTitle) document.title = innerTitle
  } catch (error) {
    // 跨域等异常忽略
  }
}

onMounted(async () => {
  try {
    const status = await api.getPublicDataScreenStatus()
    if (!isPreviewMode.value && status && status.enabled === false) {
      router.replace('/login')
      return
    }
  } catch (error) {
    // 状态接口异常：非预览模式且未登录时按“未开放”处理
    if (!isPreviewMode.value && !localStorage.getItem('token')) {
      router.replace('/login')
      return
    }
  }
  ready.value = true
})
</script>

<style scoped>
.ds-frame {
  position: fixed;
  inset: 0;
  background: #03060e;
}

.ds-iframe {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}

.ds-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: #9db6ce;
  font-size: 14px;
  letter-spacing: 0.04em;
  background: #03060e;
}

.ds-spinner {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 2px solid rgba(56, 240, 255, 0.18);
  border-top-color: #38f0ff;
  animation: ds-spin 0.9s linear infinite;
}

@keyframes ds-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

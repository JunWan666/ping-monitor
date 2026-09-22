<template>
  <div class="ds-frame">
    <iframe
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
 * 后台预览外壳：/datascreen-preview 需要在登录态下看大屏。
 *
 * 正式首页（/）现在由 nginx 直接返回 /bigscreen/index.html，不再经过 SPA，
 * 所以这里只负责预览场景：带 ?preview=1 让内嵌页走鉴权接口（同域，可直接读 localStorage 的 token）。
 * 旧版 5111 行实现保留在 DataScreenLegacy.vue，回退时改 router.js 的引用即可。
 */
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
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
</style>

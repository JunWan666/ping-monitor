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
 * 公开首页和后台预览共用独立的大屏文档；预览参数让 iframe 改用鉴权接口。
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
  display: flex;
  flex: 1 1 0;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border-radius: var(--radius-md, 10px);
  background: #03060e;
}

.ds-iframe {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  border: 0;
  display: block;
}
</style>

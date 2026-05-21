import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export const useViewport = (breakpoint = 768) => {
  const width = ref(window.innerWidth)
  const height = ref(window.visualViewport?.height || window.innerHeight)
  const isMobile = computed(() => width.value <= breakpoint)

  const updateWidth = () => {
    width.value = window.innerWidth
  }

  const updateHeight = () => {
    height.value = window.visualViewport?.height || window.innerHeight
  }

  onMounted(() => {
    window.addEventListener('resize', updateWidth)
    window.addEventListener('resize', updateHeight)
    window.visualViewport?.addEventListener('resize', updateHeight)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', updateWidth)
    window.removeEventListener('resize', updateHeight)
    window.visualViewport?.removeEventListener('resize', updateHeight)
  })

  return {
    width,
    height,
    isMobile
  }
}

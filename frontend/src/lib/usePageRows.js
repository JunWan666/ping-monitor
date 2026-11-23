import { nextTick, onActivated, onBeforeUnmount, ref, watch } from 'vue'

// Keep one page of rows inside the available work area, including its pager.
export const usePageRows = ({ rowHeight = 48, mobileRowHeight = rowHeight, maxRows = 18 } = {}) => {
  const pageRoot = ref(null)
  const pageSize = ref(window.innerWidth <= 768 ? 3 : 8)
  let resizeObserver
  let mutationObserver
  let frame
  let measuredBox

  const measure = () => {
    const root = pageRoot.value?.$el || pageRoot.value
    if (!root?.getBoundingClientRect || !root.getBoundingClientRect().width) return
    const box = root.matches('[data-page-rows-box]') ? root : root.querySelector('[data-page-rows-box]')
    if (box !== measuredBox) {
      if (measuredBox) resizeObserver?.unobserve(measuredBox)
      if (box) resizeObserver?.observe(box)
      measuredBox = box
    }
    if (!box?.clientHeight) return
    const table = box.querySelector('.el-table')
    const header = table ? (table.querySelector('.el-table__header-wrapper')?.offsetHeight || 42) : 0
    // Element Plus tables with an explicit height expose the real available
    // body height. Using the whole box and subtracting the header again makes
    // a fixed-height table lose one row at the boundary (e.g. 198 / 40 = 4
    // even though the body wrapper has room for five 40px rows).
    const body = table?.querySelector('.el-table__body-wrapper')
    const bodyHeight = body?.clientHeight || 0
    const height = bodyHeight > 0 ? bodyHeight : box.clientHeight - header - (table ? 2 : 0)
    const gap = table ? 0 : (parseFloat(getComputedStyle(box).rowGap) || 0)
    const itemHeight = window.innerWidth <= 768 ? (typeof mobileRowHeight === 'function' ? mobileRowHeight() : mobileRowHeight) : rowHeight
    const capacity = Math.max(1, Math.min(maxRows, Math.floor((height + (bodyHeight > 0 ? 1 : gap)) / (itemHeight + gap))))
    if (capacity !== pageSize.value) pageSize.value = capacity
  }
  const schedule = () => {
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(measure)
  }
  watch(pageRoot, (element, _, onCleanup) => {
    const root = element?.$el || element
    if (!root?.querySelector) return
    resizeObserver = new ResizeObserver(schedule)
    resizeObserver.observe(root)
    mutationObserver = new MutationObserver(schedule)
    mutationObserver.observe(root, { childList: true, subtree: true })
    window.addEventListener('resize', schedule)
    schedule()
    onCleanup(() => {
      resizeObserver.disconnect()
      mutationObserver.disconnect()
      measuredBox = undefined
      window.removeEventListener('resize', schedule)
      cancelAnimationFrame(frame)
    })
  }, { flush: 'post' })
  onActivated(() => nextTick(schedule))
  onBeforeUnmount(() => cancelAnimationFrame(frame))
  return { pageRoot, pageSize }
}

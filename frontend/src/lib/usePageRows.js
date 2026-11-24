import { nextTick, onActivated, onBeforeUnmount, ref, watch } from 'vue'

// Keep one page of rows inside the available work area, including its pager.
export const usePageRows = ({ rowHeight = 48, mobileRowHeight = rowHeight, maxRows = 18, fixedPageSize = null, initialPageSize = null, stretchTableRows = false, maxTableRowHeight = 48 } = {}) => {
  const pageRoot = ref(null)
  const pageSize = ref(fixedPageSize ?? initialPageSize ?? (window.innerWidth <= 768 ? 3 : 8))
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
    if (fixedPageSize !== null && pageSize.value !== fixedPageSize) pageSize.value = fixedPageSize
    if (stretchTableRows) {
      const resetRowHeight = () => box.style.removeProperty('--table-row-height')
      if (window.innerWidth <= 768 || !table) {
        resetRowHeight()
        return
      }
      const body = table.querySelector('.el-table__body-wrapper')
      const rows = [...table.querySelectorAll('.el-table__body tr.el-table__row:not(.el-table__expanded-row)')]
      if (!body?.clientHeight || !rows.length) {
        resetRowHeight()
        return
      }
      const bodyHeight = body.clientHeight
      const expandedHeight = [...table.querySelectorAll('.el-table__body tr.el-table__expanded-row')]
        .reduce((sum, row) => sum + row.getBoundingClientRect().height, 0)
      const occupiedHeight = rows.reduce((sum, row) => sum + row.getBoundingClientRect().height, 0)
      const averageHeight = occupiedHeight / rows.length
      const availableHeight = Math.max(0, bodyHeight - expandedHeight)
      const nextHeight = Math.min(maxTableRowHeight, Math.max(rowHeight, averageHeight + (availableHeight - occupiedHeight) / rows.length))
      if (Math.abs(nextHeight - averageHeight) > 0.4) {
        box.style.setProperty('--table-row-height', `${nextHeight.toFixed(2)}px`)
        schedule()
      }
      return
    }
    if (fixedPageSize !== null) return
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

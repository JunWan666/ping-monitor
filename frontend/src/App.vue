<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import zhCn from 'element-plus/es/locale/lang/zh-cn'
</script>

<style>
#app {
  width: 100%;
  height: 100%;
}

.viewport-page:has(> .viewport-list-card) {
  display: flex;
  flex-direction: column;
}

.viewport-list-card,
.viewport-list-card > .el-card__body {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  min-height: 0;
}

.viewport-list-card > .el-card__header {
  flex: 0 0 auto;
  padding: 10px 12px;
}

.viewport-list-card > .el-card__body {
  padding: 8px 12px;
}

.viewport-table-area {
  --table-cell-inset: 11px;
  --table-row-height: 36px;
  flex: 1 1 0;
  min-height: 0;
  min-width: 0;
}

.viewport-table-area .el-table__row td.el-table__cell {
  height: var(--table-row-height);
  padding-block: 0;
}

.viewport-table-area .el-table .el-table__cell > .cell {
  padding-inline: var(--table-cell-inset);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.viewport-table-area .el-table .el-table__cell.is-center > .cell {
  padding-inline: 6px;
}

.viewport-table-area .el-table .el-table__cell.el-table-column--selection > .cell,
.viewport-table-area .el-table .el-table__expand-column > .cell {
  padding-inline: 4px;
}

.viewport-table-area .el-table .caret-wrapper {
  width: 16px;
}

@media (max-width: 1100px) {
  .viewport-table-area { --table-cell-inset: 8px; }
}

.viewport-table-pager {
  display: flex;
  flex: 0 0 auto;
  justify-content: center;
  align-items: center;
  min-height: 42px;
  padding: 8px 0 2px;
  border-top: 1px solid var(--line);
}

.viewport-table-pager .el-pagination {
  justify-content: center;
  flex-wrap: wrap;
  row-gap: 6px;
}

.list-number {
  display: inline-block;
  min-width: 22px;
  padding: 0 4px;
  border-radius: 4px;
  background: #edf2f8;
  color: #445672;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.viewport-table-area .el-table thead th.el-table__cell {
  padding-block: 7px;
  color: #475467;
  background: #f8fafc;
  font-weight: 600;
}

.table-identity {
  display: grid;
  min-width: 0;
  line-height: 1.35;
}

.table-identity strong,
.table-identity small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-identity small {
  color: #667085;
  font-size: 11px;
}

.admin-settings {
  display: flex;
  flex: 1 1 0;
  flex-direction: row;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  gap: 12px;
}

.admin-settings__nav {
  display: flex;
  flex: 0 0 184px;
  flex-direction: column;
  align-items: stretch;
  gap: 4px;
  max-height: 100%;
  overflow-y: auto;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.admin-settings__tab {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
  min-height: 40px;
  padding: 0 12px;
  border: 0;
  border-left: 3px solid transparent;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  transition: background-color 140ms ease, color 140ms ease;
  color: var(--ink-secondary);
  font: inherit;
  font-size: 14px;
  cursor: pointer;
}

.admin-settings__tab:hover,
.admin-settings__tab.active {
  color: var(--brand);
}

.admin-settings__tab:hover {
  background: var(--surface-muted);
}

.admin-settings__tab:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 1px;
}

.admin-settings__tab.active {
  border-left-color: var(--brand);
  background: var(--brand-soft);
  font-weight: 600;
}

.admin-settings__card {
  width: 100%;
  min-width: 0;
  border-radius: var(--radius-md);
}

.admin-settings__select {
  width: 100%;
}

.admin-settings__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-top: 1px solid var(--line);
}

.admin-settings__actions .el-button + .el-button {
  margin-left: 0;
}

@media (max-width: 768px) {
  .admin-settings {
    flex-direction: column;
    gap: 8px;
  }
}
</style>

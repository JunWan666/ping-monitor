<template>
  <div ref="pageRoot" class="domain-monitor-page viewport-page">
    <section v-if="isMobile" class="domain-mobile">
      <el-card shadow="never" class="domain-mobile__toolbar">
        <div class="domain-toolbar">
          <div class="domain-toolbar__title">
            <strong>监控域名</strong>
            <span>共 {{ rows.length }} 个域名</span>
            <span v-if="!smsConfigured" class="domain-sms-hint">未配置阿里云短信 · <router-link :to="notificationSettingsRoute">配置域名通知</router-link></span>
          </div>
          <div class="domain-toolbar__actions">
            <el-button size="small" :loading="loading" @click="load"><el-icon><Refresh /></el-icon>刷新</el-button>
            <el-button type="primary" size="small" @click="open()"><el-icon><Plus /></el-icon>添加域名</el-button>
          </div>
        </div>
      </el-card>
      <div class="domain-mobile__list" data-page-rows-box>
        <el-empty v-if="!rows.length && !loading" description="还没有配置监控域名" :image-size="72" />
        <el-card v-for="(row, index) in pagedRows" :key="row.id" shadow="never" class="domain-mobile__item" :class="{ 'is-expanded': expandedId === row.id }">
          <button type="button" class="domain-mobile__head" :aria-expanded="expandedId === row.id" @click="toggleMobileRow(row.id)">
            <el-icon class="domain-expand-arrow" :class="{ 'is-expanded': expandedId === row.id }" aria-hidden="true"><ArrowRight /></el-icon>
            <strong><span class="list-number">{{ (currentPage - 1) * pageSize + index + 1 }}</span> {{ row.name }}</strong>
            <el-tag :type="status(row)[1]" effect="plain">{{ status(row)[0] }}</el-tag>
          </button>
          <div class="domain-mobile__meta">
            <span>到期日<strong>{{ expiryDate(row) }}</strong></span>
            <span>最近检查<strong>{{ formatDate(row.last_checked_at) }}</strong></span>
          </div>
          <div class="domain-mobile__summary">
            <span>预期 NS：{{ row.expected_ns?.length || 0 }} 台</span>
            <span>解析记录：{{ row.records?.length || 0 }} 条</span>
            <span>钉钉通知 {{ row.notify ? '已开启' : '已关闭' }}</span>
          </div>
          <div class="domain-mobile__controls">
            <label class="domain-state-switch"><span>监控</span><el-switch :model-value="row.enabled" :loading="stateUpdating.has(`${row.id}:enabled`)" :disabled="isRowUpdating(row)" aria-label="启用域名监控" @change="value => changeState(row, 'enabled', value)" /></label>
            <label class="domain-state-switch"><span>钉钉通知</span><el-switch :model-value="row.notify" :loading="stateUpdating.has(`${row.id}:notify`)" :disabled="isRowUpdating(row)" aria-label="启用域名钉钉通知" @change="value => changeState(row, 'notify', value)" /></label>
            <el-button type="primary" link size="small" @click="open(row)"><el-icon><Edit /></el-icon>编辑</el-button>
            <el-button type="danger" link size="small" @click="remove(row)" :disabled="isRowUpdating(row)"><el-icon><Delete /></el-icon>删除</el-button>
          </div>
          <div class="domain-mobile__channels" aria-label="短信通知" role="group">
            <label class="domain-mobile__channel" :style="{ '--channel-color': SMS_COLOR }">
              <span class="domain-channel-label"><el-icon aria-hidden="true"><ChatLineSquare /></el-icon>短信通知</span>
              <el-switch :model-value="row.notify_sms" :loading="stateUpdating.has(`${row.id}:notify_sms`)" :disabled="isRowUpdating(row) || (!smsConfigured && !row.notify_sms)" size="small" :aria-label="`启用 ${row.name} 短信通知`" @change="value => changeState(row, 'notify_sms', value)" />
            </label>
          </div>
          <DomainMonitorDetails v-if="expandedId === row.id" :row="row" :data-domain-details="row.id" />
        </el-card>
      </div>
      <div v-if="rows.length > pageSize" class="domain-mobile__pager">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :total="rows.length" :page-sizes="[15, 20, 50]" layout="sizes, prev, pager, next" :small="true" @current-change="handleCurrentChange" />
      </div>
    </section>

  <el-card v-else shadow="never" class="domain-desktop-card">
    <template #header>
      <div class="domain-toolbar">
        <div class="domain-toolbar__title">
          <strong>监控域名</strong>
          <span>管理 NS、解析记录和注册到期状态</span>
          <span v-if="!smsConfigured" class="domain-sms-hint">未配置阿里云短信 · <router-link :to="notificationSettingsRoute">配置域名通知</router-link></span>
        </div>
        <div class="domain-toolbar__actions">
          <el-dropdown trigger="click" :disabled="!selectedIds.length || bulkUpdating" @command="applyBulkCommand">
            <el-button size="small" :disabled="!selectedIds.length || bulkUpdating" :loading="bulkUpdating">
              {{ selectedIds.length ? '批量设置（' + selectedIds.length + '）' : '批量设置' }}<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="enabled:true">启用监控</el-dropdown-item>
                <el-dropdown-item command="enabled:false">停用监控</el-dropdown-item>
                <el-dropdown-item divided command="notify:true">启用钉钉通知</el-dropdown-item>
                <el-dropdown-item command="notify:false">关闭钉钉通知</el-dropdown-item>
                <el-dropdown-item divided command="notify_sms:true" :disabled="!smsConfigured">启用短信通知</el-dropdown-item>
                <el-dropdown-item command="notify_sms:false">关闭短信通知</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button size="small" @click="load">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
          <el-button type="primary" size="small" @click="open()">
            <el-icon><Plus /></el-icon>添加域名
          </el-button>
        </div>
      </div>
    </template>

    <div class="viewport-table-area" data-page-rows-box>
      <el-table ref="domainTable" v-loading="loading" :data="pagedRows" row-key="id" height="100%" size="small" empty-text="还没有配置监控域名" :expand-row-keys="expandedRowKeys" @selection-change="handleSelectionChange" @expand-change="handleExpandChange">
        <el-table-column type="selection" width="36" align="center" reserve-selection :selectable="row => !bulkUpdating && !isRowUpdating(row)" />
        <el-table-column type="expand" width="36">
          <template #expand="{ expanded }">
            <button type="button" class="domain-expand-button" :aria-label="expanded ? '收起域名详情' : '展开域名详情'" :aria-expanded="expanded">
              <el-icon class="domain-expand-arrow" :class="{ 'is-expanded': expanded }" aria-hidden="true"><ArrowRight /></el-icon>
            </button>
          </template>
          <template #default="{ row }">
            <DomainMonitorDetails :row="row" :data-domain-details="row.id" />
          </template>
        </el-table-column>
        <el-table-column label="序号" width="48" align="center"><template #default="{ $index }">{{ (currentPage - 1) * pageSize + $index + 1 }}</template></el-table-column>
        <el-table-column prop="name" label="域名" min-width="164" show-overflow-tooltip />
        <el-table-column label="监控状态" width="86" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="status(row)[1]">{{ status(row)[0] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="到期日" width="94" show-overflow-tooltip>
          <template #default="{ row }">
            <template v-if="row.manual_expiry">
              <el-tooltip content="手动填写"><span>{{ row.manual_expiry }}</span></el-tooltip>
            </template>
            <template v-else-if="row.expiry">
              {{ expiryDate(row) }}
            </template>
            <span v-else>未取得</span>
          </template>
        </el-table-column>
        <el-table-column v-if="width >= 1360" label="最近检查" width="144" show-overflow-tooltip>
          <template #default="{ row }">{{ formatDate(row.last_checked_at) }}</template>
        </el-table-column>
        <el-table-column label="监控" width="66" align="center">
          <template #default="{ row }"><el-switch :model-value="row.enabled" :loading="stateUpdating.has(`${row.id}:enabled`)" :disabled="bulkUpdating || isRowUpdating(row)" :aria-label="`启用 ${row.name} 监控`" @change="value => changeState(row, 'enabled', value)" /></template>
        </el-table-column>
        <el-table-column label="钉钉通知" width="78" align="center">
          <template #default="{ row }"><el-switch :model-value="row.notify" :loading="stateUpdating.has(`${row.id}:notify`)" :disabled="bulkUpdating || isRowUpdating(row)" :aria-label="`启用 ${row.name} 钉钉通知`" @change="value => changeState(row, 'notify', value)" /></template>
        </el-table-column>
        <el-table-column label="短信通知" width="86" align="center" class-name="domain-channel-column domain-channel-first">
          <template #header>
            <span class="domain-channel-label" :style="{ '--channel-color': SMS_COLOR }"><el-icon aria-hidden="true"><ChatLineSquare /></el-icon>短信通知</span>
          </template>
          <template #default="{ row }">
            <el-switch class="domain-channel-switch" :style="{ '--channel-color': SMS_COLOR }" :model-value="row.notify_sms" :loading="stateUpdating.has(`${row.id}:notify_sms`)" :disabled="bulkUpdating || isRowUpdating(row) || (!smsConfigured && !row.notify_sms)" size="small" :aria-label="`启用 ${row.name} 短信通知`" @change="value => changeState(row, 'notify_sms', value)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="88" align="center" class-name="domain-actions-column">
          <template #default="{ row }">
            <div class="domain-row-actions">
              <el-button type="primary" size="small" link :disabled="isRowUpdating(row) || bulkUpdating" @click="open(row)">编辑</el-button>
              <el-button type="danger" size="small" link :disabled="isRowUpdating(row) || bulkUpdating" @click="remove(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="domain-desktop__pager viewport-table-pager">
      <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :total="rows.length" :page-sizes="[15, 20, 50]" layout="total, sizes, prev, pager, next" :pager-count="5" small @current-change="handleCurrentChange" />
    </div>
  </el-card>

  <el-dialog v-model="dialog" :title="editing ? '编辑域名' : '添加域名'" width="min(670px, 94vw)">
    <el-form label-position="top" @submit.prevent="save">
      <el-form-item label="注册域名" required>
        <el-input v-model.trim="form.name" placeholder="example.com" />
      </el-form-item>
      <el-form-item label="到期日（选填）">
        <div class="expiry-field">
          <el-date-picker
            v-model="form.manual_expiry"
            type="date"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            placeholder="留空时自动查询注册局"
            clearable
          />
          <small>填写后按此日期发送续费提醒。请以注册商后台为准，续费后记得更新。</small>
        </div>
      </el-form-item>
      <el-form-item label="预期 NS" required>
        <div class="ns-field">
          <el-input v-model="form.ns" type="textarea" placeholder="每行一个 NS，也可以用逗号分隔" />
          <el-button type="primary" plain size="small" :loading="discovering" :disabled="!form.name" @click="discover">
            <el-icon><Search /></el-icon>查询当前 NS
          </el-button>
        </div>
        <small>保存前请用注册商后台核对这些值。</small>
      </el-form-item>
      <el-form-item label="记录检查">
        <div class="record-list">
          <div v-for="(record, index) in form.records" :key="record.key" class="record-row">
            <el-input v-model.trim="record.name" aria-label="记录名称" placeholder="*.example.com" />
            <el-select v-model="record.kind" aria-label="记录类型">
              <el-option v-for="kind in ['CNAME', 'A', 'AAAA']" :key="kind" :label="kind" :value="kind" />
            </el-select>
            <el-input v-model="record.values" aria-label="预期记录值" placeholder="预期值，用逗号分隔" />
            <el-button type="danger" link size="small" @click="form.records.splice(index, 1)">
              <el-icon><Delete /></el-icon>移除
            </el-button>
          </div>
          <el-button v-if="form.records.length < 8" type="primary" plain size="small" @click="addRecord">
            <el-icon><Plus /></el-icon>添加记录
          </el-button>
        </div>
      </el-form-item>
      <div class="domain-edit-controls">
        <div class="domain-edit-options" role="group" aria-label="监控与钉钉通知">
          <el-checkbox v-model="form.enabled">启用监控</el-checkbox>
          <el-checkbox v-model="form.notify">钉钉通知</el-checkbox>
        </div>
        <div class="domain-edit-upgrade" role="group" aria-label="短信通知">
          <strong>短信通知</strong>
          <div class="domain-edit-options">
            <el-checkbox v-model="form.notify_sms" :disabled="!smsConfigured && !form.notify_sms" :style="{ '--channel-color': SMS_COLOR }">
              <span class="domain-channel-label"><el-icon aria-hidden="true"><ChatLineSquare /></el-icon>阿里云短信（警告、严重异常和到期提醒）</span>
            </el-checkbox>
          </div>
          <span v-if="!smsConfigured" class="domain-sms-hint">启用前请<router-link :to="notificationSettingsRoute">配置域名通知</router-link></span>
        </div>
      </div>
      <el-form-item v-if="form.notify" label="故障重复提醒间隔（分钟，0 表示仅提醒状态变化）">
        <el-input-number v-model="form.reminder_minutes" :min="0" :max="1440" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">
        <el-icon><Check /></el-icon>保存
      </el-button>
    </template>
  </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, ArrowRight, ChatLineSquare, Check, Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import api from '../api'
import DomainMonitorDetails from './DomainMonitorDetails.vue'
import { domainState, expiryDate } from '../lib/domainPresentation'
import { useViewport } from '../lib/useViewport'
import { usePageRows } from '../lib/usePageRows'

const { isMobile, width } = useViewport()
const { pageRoot, pageSize } = usePageRows({ initialPageSize: 15, rowHeight: 36, stretchTableRows: true })
const rows = ref([])
const currentPage = ref(1)
const loading = ref(false)
const saving = ref(false)
const stateUpdating = ref(new Set())
const selectedIds = ref([])
const domainTable = ref(null)
const bulkUpdating = ref(false)
const smsConfigured = ref(false)
const notificationSettingsRoute = { name: 'AdminSettings', query: { section: 'domain-alert' } }
const SMS_COLOR = '#a34d06'
const discovering = ref(false)
const dialog = ref(false)
const editing = ref(null)
const form = ref({})
const expandedId = ref(null)
const expandedRowKeys = computed(() => expandedId.value == null ? [] : [expandedId.value])
let recordKey = 0

const pagedRows = computed(() => rows.value.slice((currentPage.value - 1) * pageSize.value, currentPage.value * pageSize.value))
watch(pageSize, () => {
  const index = rows.value.findIndex(row => row.id === expandedId.value)
  currentPage.value = index < 0 ? 1 : Math.floor(index / pageSize.value) + 1
})

function handleCurrentChange(page) {
  currentPage.value = page
  if (!pagedRows.value.some(row => row.id === expandedId.value)) expandedId.value = null
}

function handleExpandChange(row, expandedRows) {
  expandedId.value = expandedRows.some(item => item.id === row.id) ? row.id : null
}

function toggleMobileRow(id) {
  expandedId.value = expandedId.value === id ? null : id
}

function handleSelectionChange(selection) {
  selectedIds.value = selection.map(row => row.id)
}

function isRowUpdating(row) {
  const prefix = `${row.id}:`
  return [...stateUpdating.value].some(key => key.startsWith(prefix))
}

const splitValues = (value = '') => value.split(/[\s,，]+/).filter(Boolean)
const formatDate = (value) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
const errorText = (err, fallback) => typeof err?.response?.data?.detail === 'string' ? err.response.data.detail : fallback
const status = (row) => {
  const view = domainState(row)
  return [view.label, view.type]
}

const props = defineProps({ focusRequest: Object })
const openRequestedDomain = async () => {
  const request = props.focusRequest
  if (!request) return
  await load()
  if (props.focusRequest !== request) return
  const index = rows.value.findIndex(row => row.id === request.id)
  if (index < 0) return
  currentPage.value = Math.floor(index / pageSize.value) + 1
  expandedId.value = request.id
  await nextTick()
  pageRoot.value?.querySelector(`[data-domain-details="${request.id}"]`)?.scrollIntoView({ block: 'nearest' })
}
watch(() => props.focusRequest, openRequestedDomain)

async function load() {
  loading.value = true
  try {
    const [domainsResult, notificationStatusResult] = await Promise.allSettled([
      api.getDomains(),
      api.getDomainNotificationStatus(),
    ])
    if (domainsResult.status === 'rejected') throw domainsResult.reason
    rows.value = domainsResult.value
    smsConfigured.value = notificationStatusResult.status === 'fulfilled'
      && Boolean(notificationStatusResult.value.sms_configured)
    if (notificationStatusResult.status === 'rejected') {
      ElMessage.warning('无法读取短信配置状态，暂不能开启短信通知')
    }
    if (!rows.value.some(row => row.id === expandedId.value)) expandedId.value = null
    currentPage.value = Math.min(currentPage.value, Math.max(1, Math.ceil(rows.value.length / pageSize.value)))
  } catch (err) {
    ElMessage.error(errorText(err, '加载域名失败'))
  } finally {
    loading.value = false
  }
}

function open(row) {
  editing.value = row?.id || null
  form.value = {
    name: row?.name || '', ns: (row?.expected_ns || []).join('\n'),
    records: (row?.records || []).map(record => ({ ...record, key: ++recordKey, values: record.values.join(', ') })),
    enabled: row?.enabled ?? true, notify: row?.notify ?? true,
    notify_sms: row?.notify_sms ?? false,
    reminder_minutes: row?.reminder_minutes ?? 30,
    manual_expiry: row?.manual_expiry ?? null,
  }
  dialog.value = true
}

function addRecord() {
  form.value.records.push({ key: ++recordKey, name: '', kind: 'CNAME', values: '' })
}

async function discover() {
  discovering.value = true
  const current = form.value
  const name = current.name
  try {
    const values = (await api.discoverDomainNS(name)).expected_ns
    if (current === form.value && name === current.name) current.ns = values.join('\n')
  } catch (err) {
    ElMessage.warning(errorText(err, '未能获取当前 NS'))
  } finally {
    discovering.value = false
  }
}

async function changeState(row, field, value) {
  const key = `${row.id}:${field}`
  const pending = new Set(stateUpdating.value)
  pending.add(key)
  stateUpdating.value = pending
  try {
    const saved = await api.updateDomainState(row.id, { [field]: Boolean(value) })
    const index = rows.value.findIndex(item => item.id === row.id)
    if (index >= 0) rows.value[index] = { ...rows.value[index], ...saved }
    const labels = {
      enabled: ['域名监控', '已启用', '已停用'],
      notify: ['钉钉告警通知', '已启用', '已关闭'],
      notify_sms: ['短信通知', '已启用', '已关闭'],
    }
    const [label, onText, offText] = labels[field]
    ElMessage.success(`${label}${Boolean(value) ? onText : offText}`)
  } catch (err) {
    ElMessage.error(errorText(err, '状态更新失败'))
  } finally {
    const next = new Set(stateUpdating.value)
    next.delete(key)
    stateUpdating.value = next
  }
}

const bulkOperations = {
  'enabled:true': ['enabled', true, '启用监控'],
  'enabled:false': ['enabled', false, '停用监控'],
  'notify:true': ['notify', true, '启用钉钉通知'],
  'notify:false': ['notify', false, '关闭钉钉通知'],
  'notify_sms:true': ['notify_sms', true, '启用短信通知'],
  'notify_sms:false': ['notify_sms', false, '关闭短信通知'],
}

async function applyBulkCommand(command) {
  const operation = bulkOperations[command]
  const ids = [...selectedIds.value]
  if (!operation || !ids.length) return
  if (ids.length > 500) {
    ElMessage.warning('单次最多批量修改 500 个域名，请减少选择数量')
    return
  }
  const [field, value, label] = operation
  try {
    await ElMessageBox.confirm(
      `确定对已选择的 ${ids.length} 个域名${label}吗？`,
      '确认批量设置',
      { type: value ? 'warning' : 'info', confirmButtonText: '确认修改', cancelButtonText: '取消' },
    )
  } catch {
    return
  }

  bulkUpdating.value = true
  try {
    const result = await api.updateDomainsState({ ids, [field]: value })
    const updated = new Map((result.items || []).map(row => [row.id, row]))
    rows.value = rows.value.map(row => updated.has(row.id) ? { ...row, ...updated.get(row.id) } : row)
    selectedIds.value = []
    domainTable.value?.clearSelection()
    ElMessage.success(`已${label} ${result.updated} 个域名`)
  } catch (err) {
    ElMessage.error(errorText(err, '批量更新失败，请刷新列表后重试'))
  } finally {
    bulkUpdating.value = false
  }
}

async function save() {
  const { name, ns, records, enabled, notify, notify_sms, reminder_minutes, manual_expiry } = form.value
  const expected_ns = splitValues(ns)
  if (!name || !expected_ns.length) {
    ElMessage.warning('请填写注册域名和预期 NS')
    return
  }
  if (records.some(record => !record.name || !splitValues(record.values).length)) {
    ElMessage.warning('请填写每条记录的名称和预期值')
    return
  }
  saving.value = true
  try {
    const body = {
      name, expected_ns, enabled, notify, notify_sms, reminder_minutes, manual_expiry: manual_expiry || null,
      records: records.map(record => ({ name: record.name, kind: record.kind, values: splitValues(record.values) })),
    }
    if (editing.value) await api.updateDomain(editing.value, body)
    else await api.createDomain(body)
    ElMessage.success('已保存')
    dialog.value = false
    await load()
  } catch (err) {
    ElMessage.error(errorText(err, '保存失败，请检查填写的域名和记录'))
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`停止监控 ${row.name}？已有告警仍可在告警记录中查询。`, '删除域名', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.deleteDomain(row.id)
    await load()
  } catch (err) {
    ElMessage.error(errorText(err, '删除失败'))
  }
}

onActivated(() => { if (props.focusRequest) openRequestedDomain(); else load() })
</script>

<style scoped>
.domain-monitor-page { display: flex; flex-direction: column; gap: 10px; width: 100%; height: 100%; min-height: 0; min-width: 0; }
.domain-mobile { display: flex; flex-direction: column; gap: 10px; width: 100%; height: 100%; min-height: 0; overflow: hidden; }
.domain-mobile__toolbar { flex: 0 0 auto; border-radius: 12px; }
.domain-mobile__list { display: flex; flex: 1 1 auto; flex-direction: column; gap: 8px; min-height: 0; overflow-y: auto; }
.domain-mobile__item { flex: 0 0 auto; box-sizing: border-box; border-radius: 12px; }
.domain-mobile__item :deep(.el-card__body) { padding: 10px; }
@media (max-width: 768px) and (max-height: 430px) { .domain-mobile__toolbar :deep(.el-card__body) { padding: 4px 7px; } .domain-mobile__toolbar .domain-toolbar { flex-wrap: nowrap; gap: 5px; } .domain-mobile__toolbar .domain-toolbar__title { width: auto; flex: 1; gap: 4px; } .domain-mobile__toolbar .domain-toolbar__title strong { font-size: 13px; } .domain-mobile__toolbar .domain-toolbar__title span { display: none; } .domain-mobile__toolbar .domain-toolbar__actions { width: auto; flex: 0 0 auto; gap: 4px; } .domain-mobile__toolbar .domain-toolbar__actions :deep(.el-button) { flex: 0 0 auto; height: 27px; padding-inline: 6px; } .domain-mobile__item { flex-basis: auto; } .domain-mobile__item :deep(.el-card__body) { padding: 3px 5px; } .domain-mobile__head strong { font-size: 12px; } .domain-mobile__meta { gap: 4px; margin-top: 3px; font-size: 10px; } .domain-mobile__meta span { gap: 0; } .domain-mobile__meta strong { font-size: 10px; } .domain-mobile__summary { display: none; } .domain-mobile__actions { gap: 2px; margin-top: 4px; } .domain-mobile__actions :deep(.el-button) { min-height: 23px; height: 23px; padding-inline: 6px; } }
@media (max-width: 360px) { .domain-mobile__item { flex-basis: auto; } .domain-mobile__summary { gap: 4px; } .domain-mobile__actions { gap: 2px; } .domain-mobile__actions :deep(.el-button) { padding-inline: 5px; } }
.domain-mobile__head { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-width: 0; }
.domain-mobile__head strong { min-width: 0; overflow: hidden; color: var(--el-text-color-primary); font-size: 15px; text-overflow: ellipsis; white-space: nowrap; }
.domain-mobile__meta { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 10px; color: var(--el-text-color-secondary); font-size: 11px; }
.domain-mobile__meta span { display: grid; gap: 3px; min-width: 0; }
.domain-mobile__meta strong { overflow: hidden; color: var(--el-text-color-primary); font-size: 12px; font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
.domain-mobile__summary { display: flex; flex-wrap: wrap; gap: 6px 12px; margin-top: 8px; color: var(--el-text-color-secondary); font-size: 11px; }
.domain-mobile__actions { display: flex; justify-content: flex-end; gap: 4px; margin-top: 8px; }
.domain-mobile__actions :deep(.el-button + .el-button) { margin-left: 0; }
.domain-mobile__controls { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 4px 12px; margin-top: 7px; }
.domain-state-switch { display: inline-flex; align-items: center; gap: 5px; color: var(--ink-secondary); font-size: 11px; }
.domain-mobile__channels { display: grid; grid-template-columns: minmax(0, 1fr); gap: 4px; border-top: 1px solid var(--line); margin-top: 8px; padding-top: 8px; }
.domain-mobile__channel { display: flex; align-items: center; justify-content: center; gap: 4px; min-height: 28px; font-size: 12px; }
.domain-mobile__channel + .domain-mobile__channel { border-inline-start: 1px solid var(--line); }
.domain-channel-label { display: inline-flex; align-items: center; gap: 4px; color: var(--channel-color); white-space: nowrap; }
.domain-channel-label .el-icon { font-size: 14px; }
.domain-channel-switch, .domain-mobile__channel :deep(.el-switch) { --el-switch-on-color: var(--channel-color); }
.domain-desktop-card :deep(.domain-channel-column .cell) { padding-inline: 4px; }
.domain-desktop-card :deep(.el-table--border .el-table__cell) { border-right: 0; }
.domain-desktop-card :deep(.domain-channel-first),
.domain-desktop-card :deep(.domain-actions-column) { border-left: 1px solid var(--el-table-border-color); }
@media (max-width: 768px) { .domain-mobile__controls { justify-content: space-between; gap: 4px 8px; } }
.domain-mobile__pager { display: flex; flex: 0 0 auto; justify-content: center; padding-bottom: 2px; }
.domain-desktop-card { display: flex; flex: 1 1 auto; flex-direction: column; min-height: 0; }
.domain-desktop-card :deep(.el-card__body) { display: flex; flex: 1 1 0; flex-direction: column; min-height: 0; padding: 8px 12px; }
.domain-desktop__pager { display: flex; flex: 0 0 auto; justify-content: center; padding-top: 8px; }
.domain-mobile__item.is-expanded { flex-basis: auto; }
.domain-mobile__item .domain-details { margin-top: 8px; }
.domain-expand-button, .domain-mobile__head { display: flex; align-items: center; border: 0; background: transparent; color: var(--brand); cursor: pointer; }
.domain-mobile__head { width: 100%; padding: 2px 0; text-align: left; }
.domain-mobile__head strong { flex: 1; }
.domain-expand-button { justify-content: center; width: 28px; height: 28px; border-radius: 5px; }
.domain-expand-button:hover { background: #eaf2ff; }
.domain-expand-button:focus-visible, .domain-mobile__head:focus-visible { outline: 2px solid var(--brand); outline-offset: -2px; }
.domain-expand-arrow { flex: 0 0 auto; font-size: 14px; transition: transform .15s ease; }
.domain-expand-arrow.is-expanded { transform: rotate(90deg); }
.domain-desktop-card :deep(.el-table__expand-icon) { width: 28px; height: 28px; margin-inline: auto; }
.domain-desktop-card :deep(.el-table__expanded-cell) { padding: 6px 10px 10px; background: var(--surface); }
.domain-toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.domain-toolbar__title { display: flex; align-items: baseline; flex-wrap: wrap; gap: 10px; min-width: 0; }
.domain-toolbar__title strong { color: var(--el-text-color-primary); font-size: 16px; }
.domain-toolbar__title span { color: var(--el-text-color-secondary); font-size: 12px; }
.domain-toolbar__title .domain-sms-hint { color: #9a5a00; }
.domain-sms-hint a { color: var(--brand); text-decoration: underline; text-underline-offset: 2px; }
.domain-toolbar__actions { display: flex; align-items: center; gap: 8px; }
.domain-toolbar__actions :deep(.el-button + .el-button),
.domain-row-actions :deep(.el-button + .el-button) { margin-left: 0; }
.domain-row-actions { display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
.domain-row-actions :deep(.el-button) { min-width: 0; padding: 0; }
.expiry-field { display: grid; justify-items: start; gap: 4px; }
.expiry-field small { color: var(--el-text-color-secondary); }
.ns-field { display: flex; gap: 10px; align-items: flex-start; width: 100%; }
.record-list { display: grid; gap: 8px; width: 100%; justify-items: start; }
.record-row { display: grid; width: 100%; grid-template-columns: 1fr 100px 1fr auto; gap: 8px; }
.domain-edit-controls { display: grid; gap: 8px; margin-bottom: 16px; }
.domain-edit-options { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 20px; }
.domain-edit-options :deep(.el-checkbox) { margin-right: 0; }
.domain-edit-upgrade { padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px; }
.domain-edit-upgrade strong { font-size: 13px; font-weight: 600; }
.domain-edit-upgrade .domain-sms-hint { font-size: 12px; color: var(--ink-secondary); }
.domain-edit-options :deep(.el-checkbox:not(.is-disabled) .el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--channel-color, var(--el-color-primary));
  border-color: var(--channel-color, var(--el-color-primary));
}
@media (max-width: 600px) {
  .domain-toolbar__title { width: 100%; }
  .domain-toolbar__actions { width: 100%; }
  .domain-toolbar__actions :deep(.el-button) { flex: 1; }
  .domain-expected { padding: 10px 12px; }
  .record-row { grid-template-columns: 1fr 92px; }
}
</style>

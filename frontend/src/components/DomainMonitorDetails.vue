<template>
  <div class="domain-details" role="region" :aria-label="`${row.name} 的监控详情`">
    <div class="domain-details__config">
      <dl>
        <div><dt>预期 NS</dt><dd>{{ row.expected_ns?.join('、') || '未配置' }}</dd></div>
        <div>
          <dt>预期解析记录</dt>
          <dd v-if="row.records?.length">
            <ul>
              <li v-for="record in row.records" :key="`${record.name}:${record.kind}`">
                <b>{{ record.kind }}</b> {{ record.name }} → {{ record.values?.join('、') || '—' }}
              </li>
            </ul>
          </dd>
          <dd v-else>未配置</dd>
        </div>
        <div><dt>告警通知</dt><dd>{{ row.notify ? '已开启' : '已关闭' }}</dd></div>
      </dl>
    </div>
    <div class="domain-details__results">
      <strong>最近检测结果</strong>
      <ul v-if="detailChecks.length">
        <li v-for="check in detailChecks" :key="check.kind">
          <div class="domain-details__result-heading">
            <span>{{ checkTitle(check.kind) }}</span>
            <el-tag size="small" effect="plain" :type="check.type">{{ check.label }}</el-tag>
          </div>
          <p v-if="check.check.detail">{{ check.check.detail }}</p>
        </li>
      </ul>
      <p v-else>暂无检测结果</p>
      <p v-if="detailHint" class="domain-details__hint">{{ detailHint }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { domainChecks } from '../lib/domainPresentation'

const props = defineProps({ row: { type: Object, required: true } })

const keyParts = (key) => key.split(':')
const checkTitle = (key) => ({
  delegation: '注册局 NS',
  authority: '权威 DNS',
  recursive: '公共 DNS',
  registration: '注册状态',
  expiry: '到期检查',
}[keyParts(key)[0]] || '其他域名检查')

const checkStatus = (row, key, check) => {
  if (key === 'expiry') {
    if (check.state === 'bad') return { label: '需要关注', type: 'warning' }
    if (check.state === 'ok') return { label: '已获取', type: 'success' }
    return { label: '未获取', type: 'info' }
  }
  if (check.active && check.state !== 'bad') {
    return { label: check.state === 'ok' ? '恢复待确认' : '异常待复核', type: 'warning' }
  }
  const coverage = key === 'registration' ? null : row.checks?.[`coverage:${key}`]
  if (check.state === 'ok' && coverage?.active) return { label: '恢复待确认', type: 'warning' }
  if (check.state === 'ok' && check.incomplete) return { label: '结果不完整', type: 'warning' }
  if (check.state === 'ok') return { label: key === 'delegation' ? '与预期一致' : '正常', type: 'success' }
  if (check.state === 'unknown' || check.state === 'unsupported') {
    if (key === 'delegation') return { label: '未取得父区响应', type: coverage?.active ? 'warning' : 'info' }
    if (coverage?.active) return { label: '查询持续失败', type: 'warning' }
    return { label: check.state === 'unsupported' ? '暂不支持' : '暂未确认', type: 'info' }
  }
  if (check.active || check.immediate) return { label: '已确认异常', type: check.active === 2 || check.level === 2 ? 'danger' : 'warning' }
  return { label: '异常待确认', type: 'warning' }
}

const checkSeverity = { danger: 3, warning: 2, info: 1, success: 0 }
const detailChecks = computed(() => {
  const row = props.row
  const byKind = new Map()
  for (const [key, check] of domainChecks(row)) {
    const [kind] = keyParts(key)
    const state = checkStatus(row, key, check)
    const previous = byKind.get(kind)
    if (!previous || checkSeverity[state.type] > checkSeverity[previous.type]) {
      byKind.set(kind, { kind, key, check, ...state })
    }
  }
  return [...byKind.values()]
})

const detailHint = computed(() => {
  const firstIssue = [...detailChecks.value].sort((a, b) => checkSeverity[b.type] - checkSeverity[a.type])[0]
  return firstIssue && firstIssue.type !== 'success' ? checkSummary(firstIssue.key, firstIssue.check) : ''
})

const checkSummary = (key, check) => {
  const [kind] = keyParts(key)
  if (kind === 'expiry') {
    if (check.state === 'unknown' || check.state === 'unsupported') {
      return '暂未取得公开到期日。可以在「编辑域名」中选填日期，继续接收到期提醒。'
    }
    const source = check.source === 'manual' ? '按你手填的日期提醒，续费后请更新' : '日期来自注册局查询'
    return check.state === 'bad' ? `${check.detail}。请到注册商后台核对并续费。` : `${check.detail}。${source}。`
  }
  if (check.active && check.state !== 'bad') {
    return check.state === 'ok'
      ? '本次结果已正常，仍需连续检查确认恢复；此前的异常告警暂未解除。'
      : '本次查询没有完成，此前已确认的异常仍未解除；系统会继续复查。'
  }
  if (kind === 'registration') {
    if (check.state === 'ok') return '已查到域名的注册记录，未发现停解析、赎回或待删除状态。'
    if (check.state === 'unsupported') return '此域名后缀暂时没有公开的注册局查询接口，NS 和解析记录仍会继续检查。'
    if (check.state === 'unknown') return '本次没有取得可验证的注册局结果，暂时无法判断注册状态；系统会继续重试。'
    return check.active || check.immediate
      ? '注册局报告了异常状态，请登录域名注册商核对域名状态。'
      : '注册局返回的状态需要再次核实，系统会继续检查后再确认是否告警。'
  }
  if (check.state === 'ok') {
    if (kind === 'delegation') return '注册局登记的域名服务器与预期一致。'
    if (kind === 'authority') return '域名服务器返回了符合预期的解析记录。'
    return '公共 DNS 查到的记录与预期一致。'
  }
  if (check.state === 'unknown') {
    if (kind === 'delegation') return '本次没有拿到可验证的父区响应，无法判断 NS 是否变更。'
    return '这次没有拿到足够的检测结果。通常是查询超时或部分 DNS 服务暂不可用，尚不代表域名故障。'
  }
  if (kind === 'delegation') {
    return check.active || check.immediate
      ? '注册局登记的域名服务器与预期不一致。请到注册商核对 NS；改用新的 DNS 服务商后，也要更新这里的预期值。'
      : '检测到域名服务器与预期不一致，但还未达到确认次数；系统会继续复查。'
  }
  if (kind === 'authority') {
    return check.active ? '域名服务器返回的记录与预期不一致，请核对 DNS 服务商里的记录。' : '检测到记录差异，系统会再检查后确认是否告警。'
  }
  return check.active ? '公共 DNS 返回的记录与预期不一致，请核对解析记录或等待 DNS 更新。' : '检测到公共 DNS 结果有差异，系统会再检查后确认。'
}
</script>

<style scoped>
.domain-details { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.35fr); gap: 16px 24px; padding: 14px 16px; border: 1px solid #e0e7f0; border-radius: 8px; background: #f8fafc; color: #344054; font-size: 12px; line-height: 1.5; white-space: normal; }
.domain-details dl, .domain-details ul, .domain-details p, .domain-details dd { margin: 0; }
.domain-details ul { padding: 0; list-style: none; }
.domain-details dt, .domain-details__results > strong { color: #344054; font-size: 12px; font-weight: 650; }
.domain-details dt { margin-bottom: 3px; }
.domain-details dd, .domain-details p { color: #526278; overflow-wrap: anywhere; }
.domain-details dl, .domain-details__results ul { display: grid; gap: 7px; }
.domain-details__results > strong { display: block; margin-bottom: 6px; }
.domain-details__result-heading { display: flex; align-items: center; flex-wrap: wrap; gap: 3px 6px; }
.domain-details__results li p { margin-top: 3px; }
.domain-details p.domain-details__hint { margin-top: 8px; color: #854b0f; }
@media (max-width: 768px) { .domain-details { grid-template-columns: minmax(0, 1fr); gap: 9px; padding: 8px 9px; } }
</style>

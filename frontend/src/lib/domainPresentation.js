export const expiryDate = (domain) => {
  const value = domain.manual_expiry || domain.expiry
  return value ? String(value).slice(0, 10) : '未取得'
}

export const domainChecks = (domain) => Object.entries(domain.checks || {})
  .filter(([key, check]) => check && !key.startsWith('coverage:') && !(
    (key === 'registration' || key === 'expiry') && !check.active && ['unknown', 'unsupported'].includes(check.state)
  ))

export const domainState = (domain) => {
  if (!domain.enabled) return { label: '已暂停', type: 'info', category: 'paused' }
  const rawChecks = domain.checks || {}
  // Ignore legacy registration coverage incidents until the next backend check clears them.
  const incidentLevel = rawChecks['coverage:registration']?.active
    ? Math.max(0, ...Object.entries(rawChecks).filter(([key]) => key !== 'coverage:registration').map(([, check]) => check?.active || 0))
    : domain.incident_level
  if (incidentLevel >= 2) return { label: '严重异常', type: 'danger', category: 'issues' }
  if (incidentLevel === 1) return { label: '有异常', type: 'warning', category: 'issues' }
  if (domain.checks?.expiry?.state === 'bad') return { label: '到期提醒', type: 'warning', category: 'issues' }
  const checks = domainChecks(domain).map(([, result]) => result)
  if (!domain.last_checked_at || !checks.length) return { label: '待检查', type: 'info', category: 'pending' }
  if (checks.some(check => check.state === 'bad')) return { label: '异常待复核', type: 'warning', category: 'pending' }
  if (checks.some(check => check.incomplete || ['unknown', 'unsupported'].includes(check.state))) {
    return { label: '部分未确认', type: 'info', category: 'pending' }
  }
  return { label: '正常', type: 'success', category: 'normal' }
}

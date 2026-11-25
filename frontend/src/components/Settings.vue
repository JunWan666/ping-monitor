<template>
  <div ref="pageRoot" class="settings-root viewport-page">
    <section v-if="props.activeTab === 'settings-basic'" class="settings-basic-page" v-loading="loadingConfig">
      <div class="settings-layout admin-settings settings-layout--basic">
        <nav v-if="!isMobile" class="settings-section-nav admin-settings__nav" aria-label="设置分类">
          <button
            v-for="item in visibleSections"
            :key="item.key"
            type="button"
            class="settings-section-nav__item admin-settings__tab"
            :class="{ active: basicSection === item.key }"
            :aria-current="basicSection === item.key ? 'page' : undefined"
            :disabled="busy"
            @click="basicSection = item.key"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            {{ item.label }}
          </button>
        </nav>
        <el-select v-else v-model="basicSection" class="settings-section-select admin-settings__select" :disabled="busy" aria-label="设置分类">
          <el-option v-for="item in visibleSections" :key="item.key" :label="item.label" :value="item.key" />
        </el-select>

        <el-card shadow="never" class="settings-section-card admin-settings__card">
          <template #header>
            <div class="settings-section-heading">
              <h3>{{ activeSection.label }}</h3>
              <p>{{ activeSection.description }}</p>
            </div>
          </template>

          <el-form v-if="basicSection === 'monitor'" :model="config" label-position="top" class="settings-section-form settings-section-form--landscape-row">
            <el-form-item label="检测间隔">
              <div class="settings-value-field">
                <div class="settings-value-control">
                  <el-input-number v-model="config.check_interval" :min="1" :max="1440" />
                  <span>分钟</span>
                </div>
                <p>建议 1–60 分钟。间隔越短，检测越频繁。</p>
              </div>
            </el-form-item>
            <el-form-item label="每次发送包数">
              <div class="settings-value-field">
                <div class="settings-value-control">
                  <el-input-number v-model="config.packet_count" :min="1" :max="100" />
                  <span>个</span>
                </div>
                <p>建议 10–20 个。包数越多，单次检测耗时越长。</p>
              </div>
            </el-form-item>
            <el-form-item label="单包超时时间">
              <div class="settings-value-field">
                <div class="settings-value-control">
                  <el-input-number v-model="config.packet_timeout" :min="1" :max="10" />
                  <span>秒</span>
                </div>
                <p>建议 2–5 秒。超时未响应则计为丢包。</p>
              </div>
            </el-form-item>
            <el-form-item label="地理位置自动刷新">
              <div class="settings-value-field">
                <div class="settings-value-control">
                  <el-switch v-model="config.auto_refresh_location" />
                  <span>{{ config.auto_refresh_location ? '每次检测刷新' : '仅补全空白位置' }}</span>
                </div>
                <p>同时应用于定时监控和手动 Ping。</p>
              </div>
            </el-form-item>
          </el-form>

          <el-form v-else-if="basicSection === 'domain'" :model="domainConfig" label-position="top" class="settings-section-form settings-section-form--landscape-row">
            <el-form-item label="DNS 检查间隔">
              <div class="settings-value-field">
                <div class="settings-value-control">
                  <el-input-number v-model="domainConfig.dns_interval" :min="1" :max="1440" :precision="0" />
                  <span>分钟</span>
                </div>
                <p>检查 NS 委派和解析记录，建议 1 分钟。</p>
              </div>
            </el-form-item>
            <el-form-item label="注册局查询间隔">
              <div class="settings-value-field">
                <div class="settings-value-control">
                  <el-input-number v-model="domainConfig.rdap_interval" :min="1" :max="1440" :precision="0" />
                  <span>分钟</span>
                </div>
                <p>查询注册状态和到期日，建议 5 分钟。</p>
              </div>
            </el-form-item>
            <el-form-item label="连续确认次数">
              <div class="settings-value-field">
                <div class="settings-value-control">
                  <el-input-number v-model="domainConfig.confirmation_count" :min="1" :max="10" :precision="0" />
                  <span>次</span>
                </div>
                <p>用于普通异常和恢复。确认冻结、删除或 NS 异常会立即告警。</p>
              </div>
            </el-form-item>
            <el-form-item label="到期提醒节点" class="settings-field--mobile-wide">
              <div class="settings-value-field">
                <el-select
                  v-model="domainConfig.expiry_days"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  collapse-tags
                  collapse-tags-tooltip
                  :max-collapse-tags="isMobile ? 1 : 3"
                  :reserve-keyword="false"
                  placeholder="选择或输入提前提醒的天数"
                >
                  <el-option v-for="days in [90, 60, 30, 15, 7, 3, 1]" :key="days" :label="`提前 ${days} 天`" :value="days" />
                </el-select>
                <p>可填 1–365 天，最多 12 个节点。留空则仅在到期时提醒。</p>
              </div>
            </el-form-item>
            <p class="settings-section-note settings-field--wide">预期 NS、预期解析记录、手填到期日和单域名提醒规则，可在「域名监控 → 编辑域名」修改。</p>
          </el-form>

          <el-form v-else-if="basicSection === 'alert'" :model="config" label-position="top" class="settings-section-form settings-section-form--landscape-row">
            <el-form-item label="告警平台" class="settings-field--mobile-wide">
              <el-select v-model="notificationPlatform" placeholder="选择告警平台">
                <el-option label="不启用" value="none" />
                <el-option label="Server酱" value="serverchan" />
                <el-option label="钉钉机器人" value="dingtalk" />
                <el-option label="企业微信机器人" value="weixin" />
              </el-select>
            </el-form-item>
            <el-form-item label="通知模式" class="settings-field--mobile-wide">
              <el-select v-model="config.notification_mode">
                <el-option label="状态变化时通知" value="status_change" />
                <el-option label="每次异常都通知" value="every_time" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="notificationPlatform === 'serverchan'" label="Server酱 SendKey" class="settings-field--mobile-wide">
              <el-input v-model="config.serverchan_key" placeholder="请输入 Server酱 SendKey" clearable />
            </el-form-item>
            <el-form-item v-if="notificationPlatform === 'dingtalk' || notificationPlatform === 'weixin'" label="Webhook 地址" class="settings-field--mobile-wide">
              <el-input v-model="config.webhook_url" placeholder="主机告警机器人 Webhook URL" clearable />
            </el-form-item>
            <el-form-item v-if="notificationPlatform === 'dingtalk'" label="加签密钥（选填）" class="settings-field--mobile-wide">
              <div class="settings-value-field">
                <el-input v-model="config.webhook_secret" placeholder="机器人启用加签时填写" clearable />
                <p>钉钉机器人的加签密钥以 SEC 开头。</p>
              </div>
            </el-form-item>
          </el-form>

          <el-form v-else-if="basicSection === 'domain-alert'" :model="domainNotification" label-position="top" class="settings-section-form domain-notification-form" @submit.prevent="saveConfig">
            <section class="domain-notification-panel">
              <div class="domain-notification-panel__heading">
                <h4>钉钉群通知</h4>
              </div>
              <el-form-item label="钉钉 Webhook 地址">
                <el-input v-model="domainNotification.webhook_url" type="password" show-password autocomplete="off" placeholder="粘贴自定义机器人的 Webhook" clearable />
              </el-form-item>
              <el-form-item label="加签密钥（选填）">
                <el-input v-model="domainNotification.webhook_secret" type="password" show-password autocomplete="off" placeholder="启用加签时填写，以 SEC 开头" clearable />
              </el-form-item>
              <p class="domain-notification-help">钉钉群设置 → 机器人 → 自定义机器人</p>
            </section>

            <section class="domain-notification-panel">
              <div class="domain-notification-panel__heading">
                <h4>阿里云短信</h4>
                <el-tag class="domain-notification-status" size="small" effect="plain" :type="smsChanged ? 'warning' : smsSaved ? 'success' : 'info'">
                  {{ smsChanged ? '未保存' : smsSaved ? '已配置' : '未配置' }}
                </el-tag>
              </div>
              <div class="domain-sms-grid">
                <el-form-item label="AccessKey ID">
                  <el-input v-model="domainNotification.sms_access_key_id" autocomplete="off" placeholder="RAM 用户的 AccessKey ID" clearable />
                </el-form-item>
                <el-form-item label="AccessKey Secret">
                  <el-input v-model="domainNotification.sms_access_key_secret" type="password" show-password autocomplete="new-password" :placeholder="smsSecretSet ? '已保存，留空则不修改' : 'RAM 用户的 AccessKey Secret'" clearable />
                </el-form-item>
                <el-form-item label="签名名称 SignName">
                  <el-input v-model="domainNotification.sms_sign_name" placeholder="审核通过的签名，不带【】" clearable />
                </el-form-item>
                <el-form-item label="模板 Code TemplateCode">
                  <el-input v-model="domainNotification.sms_template_code" placeholder="如 SMS_123456789" clearable />
                </el-form-item>
              </div>
              <el-form-item label="接收手机号 PhoneNumbers">
                <div class="domain-sms-phones" @paste.capture="pastePhones">
                  <el-input-tag
                    v-model="phoneTags"
                    clearable
                    :delimiter="PHONE_DELIMITER"
                    :max="MAX_PHONES"
                    tag-type="info"
                    aria-label="接收手机号"
                    placeholder="输入手机号后按回车添加"
                  />
                  <p class="domain-notification-help">{{ phoneTags.length ? `已添加 ${phoneTags.length} 个号码，点号码上的 × 可移除。` : '输入一个手机号按回车，可继续添加多个；国际号码请带国家区号。' }}</p>
                </div>
              </el-form-item>
              <p class="domain-notification-help">模板需包含 ${name}、${time}、${status}、${msg} 四个变量。只在警告、严重异常和到期提醒时发送，恢复通知仍走钉钉；建议使用只授权 dysms:SendSms 的 RAM 用户。全部清空后保存即关闭短信。</p>
            </section>

            <div class="domain-notification-actions settings-field--wide">
              <div class="domain-notification-actions__save">
                <el-button type="primary" native-type="submit" :loading="saving" :disabled="busy || !domainNotificationLoaded">保存域名通知</el-button>
                <el-button :disabled="busy" @click="loadConfig()">重置</el-button>
              </div>
              <div class="domain-notification-actions__tests">
                <el-tooltip :content="dingTalkTestHint" placement="top">
                  <span class="domain-notification-test">
                    <el-dropdown trigger="click" :disabled="!canTestDingTalk" @command="saveAndTestDomainNotification">
                      <el-button :loading="!!testingDomainNotification" :disabled="!canTestDingTalk">
                        测试钉钉通知<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                      </el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item v-for="item in domainTestTypes" :key="item.value" :command="item.value">{{ item.label }}</el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </span>
                </el-tooltip>
                <el-tooltip :content="smsTestHint" placement="top">
                  <span class="domain-notification-test">
                    <el-button :loading="testingSmsNotification" :disabled="!canTestSms" @click="testSmsDomainNotification">测试短信通知</el-button>
                  </span>
                </el-tooltip>
              </div>
            </div>
          </el-form>

          <el-form v-else-if="basicSection === 'data'" :model="config" label-position="top" class="settings-section-form settings-section-form--landscape-row">
            <el-form-item label="原始数据保留">
              <div class="settings-value-field">
                <div class="settings-value-control">
                  <el-input-number v-model="config.data_retention_days" :min="7" :max="365" />
                  <span>天</span>
                </div>
                <p>清理过期的原始 Ping 记录，聚合数据永久保留。</p>
              </div>
            </el-form-item>
            <el-form-item label="每日清理时间">
              <div class="settings-value-field">
                <el-time-select v-model="config.cleanup_time" start="00:00" step="01:00" end="23:00" placeholder="选择时间" class="settings-time-input" />
                <p>建议安排在业务低峰时段。</p>
              </div>
            </el-form-item>
            <el-form-item label="数据聚合间隔">
              <div class="settings-value-field">
                <div class="settings-value-control">
                  <el-input-number v-model="config.aggregate_interval" :min="1" :max="24" />
                  <span>小时</span>
                </div>
                <p>执行小时级数据聚合的频率，建议 1–6 小时。</p>
              </div>
            </el-form-item>
            <el-form-item label="仪表盘趋势点数">
              <div class="settings-value-field">
                <div class="settings-value-control">
                  <el-input-number v-model="config.dashboard_chart_points" :min="3" :max="5" />
                  <span>次检测</span>
                </div>
                <p>控制仪表盘趋势图显示的检查次数，最多显示 5 次。</p>
              </div>
            </el-form-item>
          </el-form>

          <el-form v-else-if="basicSection === 'report'" :model="config" label-position="top" class="settings-section-form" :class="{ 'settings-section-form--schedule': reportSection === 'schedule' }">
            <el-radio-group v-model="reportSection" size="small" class="settings-field--wide">
              <el-radio-button value="robot">报表机器人</el-radio-button>
              <el-radio-button value="schedule">发送计划</el-radio-button>
            </el-radio-group>
            <template v-if="reportSection === 'robot'">
              <el-form-item label="钉钉 Webhook 地址" class="settings-field--mobile-wide">
                <el-input v-model="config.report_webhook_url" placeholder="报表机器人 Webhook URL" clearable />
              </el-form-item>
              <el-form-item label="加签密钥（选填）" class="settings-field--mobile-wide">
                <el-input v-model="config.report_webhook_secret" placeholder="机器人启用加签时填写" clearable />
              </el-form-item>
            </template>
            <template v-else>
              <el-form-item v-for="item in reportSchedules" :key="item.type" :label="item.label" class="settings-report-schedule">
                <div class="settings-value-control">
                  <el-switch v-model="config[item.enabled]" :aria-label="item.label" />
                  <el-time-select
                    v-model="config[item.time]"
                    start="00:00"
                    step="00:30"
                    end="23:30"
                    placeholder="发送时间"
                    class="settings-time-input"
                    :disabled="!config[item.enabled]"
                  />
                  <el-button
                    link
                    type="primary"
                    :loading="sendingReportType === item.type"
                    :disabled="!canSendDingTalkReport || busy"
                    @click="saveAndSendReport(item.type)"
                  >立即发送</el-button>
                </div>
              </el-form-item>
            </template>
          </el-form>

          <div v-if="basicSection !== 'domain-alert'" class="settings-section-actions admin-settings__actions">
            <el-button type="primary" :loading="saving" :disabled="busy" @click="saveConfig">保存本栏</el-button>
            <el-button :disabled="busy" @click="loadConfig()">重置本栏</el-button>
            <el-button
              v-if="basicSection === 'alert' && notificationPlatform !== 'none'"
              :loading="testingNotification"
              :disabled="!canTestNotification || busy"
              @click="saveAndTestHostNotification"
            >保存并测试</el-button>
          </div>
        </el-card>
      </div>
    </section>


    <!-- Ping日志 -->
    <div v-else-if="props.activeTab === 'settings-logs'" class="settings-logs-page viewport-page">
      <div v-if="isMobile" class="ping-logs-mobile">
        <el-card shadow="never" class="ping-logs-mobile__toolbar">
          <el-input
            v-model="hostSearchKeyword"
            placeholder="搜索主机名称或地址"
            clearable
            @clear="applyPingFilters"
            @keyup.enter="applyPingFilters"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <div class="ping-logs-mobile__filters">
            <el-select v-model="selectedStatus" placeholder="状态" @change="applyPingFilters">
              <el-option label="全部状态" value="" />
              <el-option label="正常" value="normal" />
              <el-option label="异常" value="abnormal" />
            </el-select>
            <el-button type="primary" :loading="loadingPingLogs" @click="applyPingFilters">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </el-card>

        <div class="ping-logs-mobile__list" data-page-rows-box v-loading="loadingPingLogs">
          <el-empty v-if="!loadingPingLogs && pingLogs.length === 0" description="暂无 Ping 日志" :image-size="48" />
          <div v-for="(row, index) in pingLogs" :key="row.id" class="ping-logs-mobile__item">
            <div class="ping-logs-mobile__head">
              <div>
                <div class="ping-logs-mobile__name" :title="row.host_name"><span class="list-number">{{ (currentPage - 1) * pageSize + index + 1 }}</span> {{ row.host_name }}</div>
                <button type="button" class="ping-logs-mobile__address" :title="row.host_address" @click="copyAddress(row.host_address)">{{ row.host_address }}</button>
              </div>
              <el-tag :type="row.status === '正常' ? 'success' : row.status === '异常' ? 'warning' : row.status === '离线' ? 'danger' : 'info'" effect="plain">
                {{ row.status }}
              </el-tag>
            </div>
            <div class="ping-logs-mobile__metrics">
              <span>发 {{ row.packet_sent }}</span>
              <span>收 {{ row.packet_received }}</span>
              <span>丢包 {{ row.packet_loss }}%</span>
              <span>平均 {{ row.avg_rtt == null ? '—' : row.avg_rtt + 'ms' }}</span>
            </div>
            <div class="ping-logs-mobile__time">{{ new Date(row.check_time).toLocaleString('zh-CN', { hour12: false }) }}</div>
          </div>
        </div>

        <div class="ping-logs-mobile__pager">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="totalLogs"
            layout="sizes, prev, pager, next"
            :small="true"
            :pager-count="5"
          />
        </div>
      </div>

      <el-card v-else shadow="never" class="viewport-list-card">
        <template #header>
          <div class="ping-logs-toolbar">
            <strong>主机 Ping 记录</strong>
            <div class="ping-logs-toolbar__controls">
              <el-input
                v-model="hostSearchKeyword"
                placeholder="搜索主机名称或地址"
                clearable
                @clear="applyPingFilters"
                @keyup.enter="applyPingFilters"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-select v-model="selectedStatus" placeholder="选择状态" @change="applyPingFilters">
                <el-option label="全部状态" value="" />
                <el-option label="正常" value="normal" />
                <el-option label="异常" value="abnormal" />
              </el-select>
              <el-button type="primary" :loading="loadingPingLogs" @click="applyPingFilters">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
            </div>
          </div>
        </template>

        <div class="ping-logs-table-area viewport-table-area" data-page-rows-box v-loading="loadingPingLogs">
        <el-table :data="pingLogs" height="100%" class="ping-logs-table" size="small" empty-text="暂无 Ping 日志">
          <el-table-column label="序号" width="48" align="center"><template #default="{ $index }">{{ (currentPage - 1) * pageSize + $index + 1 }}</template></el-table-column>
          <el-table-column :label="width < 900 ? '监控目标' : '主机'" min-width="110" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="table-identity">
                <strong>{{ row.host_name }}</strong>
                <small v-if="width < 900" @click="copyAddress(row.host_address)">{{ row.host_address }}</small>
              </div>
            </template>
          </el-table-column>
          <el-table-column v-if="width >= 900" label="地址" min-width="138" show-overflow-tooltip>
            <template #default="{ row }">
              <span
                @click="copyAddress(row.host_address)"
                style="cursor: pointer; color: #409eff; text-decoration: underline"
                :title="'点击复制: ' + row.host_address"
              >
                {{ row.host_address }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="状态" min-width="62" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === '正常' ? 'success' : row.status === '异常' ? 'warning' : row.status === '离线' ? 'danger' : 'info'">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="收／发" min-width="62" align="center">
            <template #default="{ row }">{{ row.packet_received }} / {{ row.packet_sent }}</template>
          </el-table-column>
          <el-table-column label="丢包率" min-width="70" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="row.packet_loss > 20 ? 'danger' : row.packet_loss > 0 ? 'warning' : 'success'">
                {{ row.packet_loss }}%
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="平均延迟" min-width="82" align="center">
            <template #default="{ row }">
              <el-tooltip :content="`最小 ${row.min_rtt ?? '—'} ms · 最大 ${row.max_rtt ?? '—'} ms`">
                <span>{{ row.avg_rtt == null ? '—' : `${row.avg_rtt} ms` }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="检测时间" :width="width < 900 ? 112 : 148" show-overflow-tooltip>
            <template #default="{ row }">
              {{ new Date(row.check_time).toLocaleString('zh-CN', { hour12: false }) }}
            </template>
          </el-table-column>
        </el-table>
        </div>

        <div class="ping-logs-pager">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="totalLogs"
            :page-sizes="[15, 20, 50, 100]" layout="total, sizes, prev, pager, next"
            :pager-count="5"
            small
            background
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Monitor, Connection, Bell, Message, FolderOpened, TrendCharts, ArrowDown } from '@element-plus/icons-vue'
import api from '../api'
import { useViewport } from '../lib/useViewport'
import { usePageRows } from '../lib/usePageRows'

const props = defineProps({
  activeTab: {
    type: String,
    default: 'settings-basic'
  }
})

const { isMobile, width } = useViewport()
const basicSections = [
  { key: 'monitor', label: '主机监控', description: 'Ping 检测频率、发包参数和位置更新。', icon: Monitor },
  { key: 'domain', label: '域名监控', description: 'DNS、注册局和域名到期提醒策略。', icon: Connection },
  { key: 'alert', label: '主机通知', description: '主机异常告警使用的通知渠道。', icon: Bell },
  { key: 'domain-alert', label: '域名通知', description: '配置钉钉群通知和阿里云短信。', icon: Message },
  { key: 'data', label: '数据维护', description: '原始记录保留、聚合和仪表盘趋势数据。', icon: FolderOpened },
  { key: 'report', label: '报表通知', description: '日报、周报和月报的专用机器人。', icon: TrendCharts }
]
const isAdmin = ref(false)
const visibleSections = computed(() => basicSections.filter(item => isAdmin.value || !item.key.startsWith('domain')))
const route = useRoute()
const router = useRouter()
const basicSection = computed({
  get: () => visibleSections.value.find(item => item.key === route.query.section)?.key || 'monitor',
  set: (key) => router.push({ name: 'AdminSettings', query: { ...route.query, section: key === 'monitor' ? undefined : key } }),
})
const reportSection = ref('robot')
const reportSchedules = [
  { type: 'daily', label: '日报 · 每天', enabled: 'daily_report_enabled', time: 'daily_report_time' },
  { type: 'weekly', label: '周报 · 每周一', enabled: 'weekly_report_enabled', time: 'weekly_report_time' },
  { type: 'monthly', label: '月报 · 每月 1 日', enabled: 'monthly_report_enabled', time: 'monthly_report_time' }
]
const activeSection = computed(() => basicSections.find(item => item.key === basicSection.value) || basicSections[0])
const saving = ref(false)
const loadingConfig = ref(false)
const testingNotification = ref(false)
const testingDomainNotification = ref('')
const testingSmsNotification = ref(false)
const sendingReportType = ref('')
const busy = computed(() => saving.value || loadingConfig.value || testingNotification.value || testingDomainNotification.value || testingSmsNotification.value || !!sendingReportType.value)
const notificationPlatform = ref('none')
const pingLogs = ref([])
const hostSearchKeyword = ref('')
const selectedStatus = ref('')
const currentPage = ref(1)
const { pageRoot, pageSize } = usePageRows({ initialPageSize: 15, rowHeight: 36, stretchTableRows: true })
const totalLogs = ref(0)
const loadingPingLogs = ref(false)
let pingLogRequest = 0
const domainConfig = reactive({
  dns_interval: 1,
  rdap_interval: 5,
  confirmation_count: 2,
  expiry_days: [60, 30, 15, 7, 1]
})
const smsFields = ['sms_access_key_id', 'sms_sign_name', 'sms_template_code', 'sms_phone_numbers']
const domainNotification = reactive({
  webhook_url: '', webhook_secret: '',
  sms_access_key_id: '', sms_access_key_secret: '', sms_sign_name: '', sms_template_code: '', sms_phone_numbers: ''
})
const domainNotificationLoaded = ref(false)
// The AccessKey Secret is write-only: the API only says whether one is saved.
const smsSecretSet = ref(false)
const savedSms = ref(Object.fromEntries(smsFields.map(key => [key, ''])))
const phoneList = (value) => String(value || '').split(/[\s,，;；、]+/).filter(Boolean)
const smsChanged = computed(() => !!domainNotification.sms_access_key_secret.trim() || smsFields.some(key => key === 'sms_phone_numbers'
  ? phoneList(domainNotification[key]).join(',') !== phoneList(savedSms.value[key]).join(',')
  : domainNotification[key].trim() !== savedSms.value[key]))
const smsSaved = computed(() => smsSecretSet.value && smsFields.every(key => savedSms.value[key]))
const smsReadyToTest = computed(() => smsSaved.value && !smsChanged.value)
// Phone numbers are edited as tags but stored as one newline-joined string, the format the API takes.
const MAX_PHONES = 1000
const PHONE_PATTERN = /^\+?\d{5,20}$/
const PHONE_DELIMITER = /[,，;；、]+/
const cleanPhone = (value) => String(value || '').replace(/[\s-]/g, '')
const phoneTags = computed({
  get: () => phoneList(domainNotification.sms_phone_numbers),
  set: (list) => {
    const next = []
    const invalid = []
    let repeated = false   // saved tags are already unique, so any repeat involves a newly added one
    for (const raw of list || []) {
      const phone = cleanPhone(raw)
      if (!phone) continue
      if (next.includes(phone)) repeated = true
      else if (PHONE_PATTERN.test(phone)) next.push(phone)
      else invalid.push(String(raw).trim())
    }
    if (invalid.length) ElMessage.warning(`手机号格式不对：${invalid.join('、')}`)
    else if (repeated) ElMessage.info('这个手机号已经添加过了')
    if (next.length > MAX_PHONES) ElMessage.warning(`接收手机号最多 ${MAX_PHONES} 个`)
    domainNotification.sms_phone_numbers = next.slice(0, MAX_PHONES).join('\n')
  }
})
// A text input drops line breaks on paste, so a pasted list is split here instead.
const pastePhones = (event) => {
  const items = (event.clipboardData?.getData('text') || '').split(/[\r\n,，;；、]+/).map(cleanPhone).filter(Boolean)
  if (items.length < 2) return
  event.preventDefault()
  phoneTags.value = [...phoneTags.value, ...items]
}
const canTestDingTalk = computed(() => domainNotificationLoaded.value && !busy.value && !!domainNotification.webhook_url.trim())
const dingTalkTestHint = computed(() => domainNotification.webhook_url.trim()
  ? '选择一种模板发到钉钉群；会先保存钉钉地址和加签密钥'
  : '先填写钉钉 Webhook 地址')
const canTestSms = computed(() => smsReadyToTest.value && !busy.value)
const smsTestHint = computed(() => {
  if (!smsSaved.value) return '先填写并保存完整的阿里云短信配置'
  if (smsChanged.value) return '短信配置有未保存的修改，先保存再测试'
  return `向已保存的 ${phoneList(savedSms.value.sms_phone_numbers).length} 个手机号各发一条真实短信，产生短信费用`
})
const applyDomainNotification = (data) => {
  const { sms_access_key_secret_set: secretSet, ...fields } = data
  Object.assign(domainNotification, fields, { sms_access_key_secret: '' })
  smsSecretSet.value = !!secretSet
  savedSms.value = Object.fromEntries(smsFields.map(key => [key, data[key] || '']))
}
const domainTestTypes = [
  { value: 'domain_warning', label: '警告提醒' },
  { value: 'domain_critical', label: '严重异常' },
  { value: 'domain_recovery', label: '恢复正常' },
  { value: 'domain_expiry', label: '到期提醒' }
]

const config = reactive({
  check_interval: 5,
  packet_count: 10,
  packet_timeout: 2,
  serverchan_key: '',
  webhook_url: '',
  webhook_secret: '',
  report_webhook_url: '',
  report_webhook_secret: '',
  notification_mode: 'status_change',
  data_retention_days: 30,
  cleanup_time: '03:00',
  aggregate_interval: 1,
  dashboard_chart_points: 5,
  auto_refresh_location: false,
  daily_report_enabled: false,
  daily_report_time: '09:00',
  weekly_report_enabled: false,
  weekly_report_time: '09:00',
  monthly_report_enabled: false,
  monthly_report_time: '09:00'
})

// 计算属性：是否可以测试通知
const canTestNotification = computed(() => {
  if (notificationPlatform.value === 'serverchan') {
    return !!config.serverchan_key
  } else if (notificationPlatform.value === 'dingtalk' || notificationPlatform.value === 'weixin') {
    return !!config.webhook_url
  }
  return false
})

const canSendDingTalkReport = computed(() => {
  return !!config.report_webhook_url
})

const sectionFields = {
  monitor: ['check_interval', 'packet_count', 'packet_timeout', 'auto_refresh_location'],
  data: ['data_retention_days', 'cleanup_time', 'aggregate_interval', 'dashboard_chart_points'],
  alert: ['notification_mode', 'serverchan_key', 'webhook_url', 'webhook_secret'],
  report: ['report_webhook_url', 'report_webhook_secret', 'daily_report_enabled', 'daily_report_time', 'weekly_report_enabled', 'weekly_report_time', 'monthly_report_enabled', 'monthly_report_time']
}

const errorDetail = (error) => {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail.map(item => `${item.loc?.slice(1).join('.')}: ${item.msg}`).join('；')
  // No detail on a 5xx usually means the backend itself was unreachable (e.g. restarting behind the dev proxy).
  if (!detail && error.response?.status >= 500) return `后端暂时没有响应（HTTP ${error.response.status}），可能正在重启，请稍后再试`
  return detail || error.message || '网络错误'
}

const loadConfig = async (all = false) => {
  const section = basicSection.value
  loadingConfig.value = true
  try {
    const tasks = []
    if (all === true || sectionFields[section]) {
      tasks.push(api.getConfig().then(data => {
        const fields = all === true ? Object.values(sectionFields).flat() : sectionFields[section]
        for (const key of fields) config[key] = data[key]
        if (all === true || section === 'alert') {
          notificationPlatform.value = data.serverchan_key ? 'serverchan'
            : data.webhook_url ? (data.webhook_url.includes('qyapi.weixin.qq.com') ? 'weixin' : 'dingtalk') : 'none'
        }
      }))
    }
    if (isAdmin.value && (all === true || section === 'domain')) {
      tasks.push(api.getDomainSettings().then(data => Object.assign(domainConfig, data)))
    }
    if (isAdmin.value && (all === true || section === 'domain-alert')) {
      domainNotificationLoaded.value = false
      tasks.push(api.getDomainNotification().then(data => {
        applyDomainNotification(data)
        domainNotificationLoaded.value = true
      }))
    }
    const results = await Promise.allSettled(tasks)
    const failed = results.find(result => result.status === 'rejected')
    if (failed) throw failed.reason
  } catch (error) {
    ElMessage.error(`加载配置失败: ${errorDetail(error)}`)
  } finally {
    loadingConfig.value = false
  }
}

const persistSection = async (section) => {
  if (section === 'domain') {
    const days = domainConfig.expiry_days.map(value => Number(String(value).trim()))
    if (days.length > 12 || days.some(day => !Number.isInteger(day) || day < 1 || day > 365)) {
      throw new Error('到期提醒节点请输入 1–365 的整数天数，最多 12 个节点')
    }
    const data = await api.updateDomainSettings({ ...domainConfig, expiry_days: days })
    Object.assign(domainConfig, data)
  } else if (section === 'domain-alert') {
    const payload = { ...domainNotification }
    if (!payload.sms_access_key_secret.trim()) delete payload.sms_access_key_secret   // keep the saved secret
    const data = await api.updateDomainNotification(payload)
    applyDomainNotification(data)
  } else {
    const payload = Object.fromEntries(sectionFields[section].map(key => [key, config[key]]))
    if (section === 'alert') {
      if (notificationPlatform.value === 'none') {
        payload.serverchan_key = payload.webhook_url = payload.webhook_secret = ''
      } else if (notificationPlatform.value === 'serverchan') {
        payload.webhook_url = payload.webhook_secret = ''
      } else {
        payload.serverchan_key = ''
      }
    }
    await api.updateConfig(payload)
  }
}

const saveConfig = async () => {
  const section = basicSection.value
  if (busy.value || (section === 'domain-alert' && !domainNotificationLoaded.value)) return
  saving.value = true
  try {
    await persistSection(section)
    ElMessage.success(`${basicSections.find(item => item.key === section).label}已保存`)
  } catch (error) {
    ElMessage.error(`保存失败: ${errorDetail(error)}`)
  } finally {
    saving.value = false
  }
}

const saveAndTestDomainNotification = async (alertType) => {
  if (!canTestDingTalk.value) return
  saving.value = true
  testingDomainNotification.value = alertType
  try {
    // Save only the DingTalk fields: unfinished SMS edits must not block a DingTalk test, and stay in the form unsaved.
    const data = await api.updateDomainNotification({
      webhook_url: domainNotification.webhook_url,
      webhook_secret: domainNotification.webhook_secret
    })
    domainNotification.webhook_url = data.webhook_url || ''
    domainNotification.webhook_secret = data.webhook_secret || ''
    const result = await api.testDomainNotification(alertType)
    ElMessage.success(result.message || '域名模板测试通知已发送，请检查对应的钉钉群')
  } catch (error) {
    ElMessage.error(`域名通知测试失败: ${errorDetail(error)}`)
  } finally {
    testingDomainNotification.value = ''
    saving.value = false
  }
}

const testSmsDomainNotification = async () => {
  if (!smsReadyToTest.value || busy.value) return
  const count = phoneList(savedSms.value.sms_phone_numbers).length
  try {
    await ElMessageBox.confirm(
      `将向已保存的 ${count} 个手机号各发送一条真实短信，会产生短信费用。`,
      '发送测试短信',
      { type: 'warning', confirmButtonText: '发送', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  testingSmsNotification.value = true
  try {
    const result = await api.testSmsDomainNotification()
    ElMessage.success(result.message || '阿里云已受理测试短信')
  } catch (error) {
    ElMessage.error('测试短信发送失败: ' + errorDetail(error))
  } finally {
    testingSmsNotification.value = false
  }
}

const saveAndTestHostNotification = async () => {
  testingNotification.value = true
  try {
    await persistSection('alert')
    await testNotification()
  } catch (error) {
    ElMessage.error(`主机通知测试失败: ${errorDetail(error)}`)
  } finally {
    testingNotification.value = false
  }
}

const saveAndSendReport = async (type) => {
  sendingReportType.value = type
  try {
    await persistSection('report')
    await sendReport(type)
  } catch (error) {
    ElMessage.error(`报表发送失败: ${errorDetail(error)}`)
  } finally {
    sendingReportType.value = ''
  }
}

const loadPingLogs = async () => {
  const request = ++pingLogRequest
  loadingPingLogs.value = true
  try {
    const status = selectedStatus.value || null
    const search = hostSearchKeyword.value.trim() || null
    const data = await api.getPingLogs(null, currentPage.value, pageSize.value, status, search)
    if (request !== pingLogRequest) return
    pingLogs.value = (data.items || []).slice(0, pageSize.value)
    totalLogs.value = data.total || 0
  } catch (error) {
    if (request === pingLogRequest) ElMessage.error('加载 Ping 日志失败')
  } finally {
    if (request === pingLogRequest) loadingPingLogs.value = false
  }
}

const applyPingFilters = () => {
  if (currentPage.value === 1) loadPingLogs()
  else currentPage.value = 1
}

const testNotification = async () => {
  if (notificationPlatform.value === 'none') {
    ElMessage.warning('请先选择通知平台')
    return
  }

  let type = 'webhook'
  if (notificationPlatform.value === 'serverchan') {
    if (!config.serverchan_key) {
      ElMessage.warning('请先输入Server酱密钥')
      return
    }
    type = 'serverchan'
  } else {
    if (!config.webhook_url) {
      ElMessage.warning('请先输入Webhook地址')
      return
    }
    type = 'webhook'
  }

  testingNotification.value = true
  try {
    await api.testNotification(type)
    ElMessage.success('测试通知已发送，请检查是否收到')
  } catch (error) {
    ElMessage.error(`测试通知失败: ${error.response?.data?.detail || error.message || '网络错误'}`)
  } finally {
    testingNotification.value = false
  }
}

const sendReport = async (type) => {
  if (!canSendDingTalkReport.value) {
    ElMessage.warning('请先配置报表专用钉钉机器人 Webhook 地址')
    return
  }

  sendingReportType.value = type
  try {
    const data = await api.sendReport(type)
    ElMessage.success(data.message || '报表发送成功')
  } catch (error) {
    ElMessage.error(`报表发送失败: ${error.response?.data?.detail || error.message || '网络错误'}`)
  } finally {
    sendingReportType.value = ''
  }
}

const copyAddress = async (address) => {
  try {
    await navigator.clipboard.writeText(address)
    ElMessage.success(`复制成功: ${address}`)
  } catch (error) {
    // 如果 clipboard API 不可用，使用备用方法
    const textarea = document.createElement('textarea')
    textarea.value = address
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      ElMessage.success(`复制成功: ${address}`)
    } catch (err) {
      ElMessage.error('复制失败，请手动复制')
    }
    document.body.removeChild(textarea)
  }
}

watch([() => props.activeTab, pageSize, currentPage], ([tab, size], [, previousSize]) => {
  if (tab !== 'settings-logs') return
  if (size !== previousSize && currentPage.value !== 1) {
    pingLogs.value = []
    currentPage.value = 1
    return
  }
  pingLogs.value = pingLogs.value.slice(0, size)
  loadPingLogs()
}, { immediate: true })

onMounted(() => {
  api.getCurrentUser().then(user => {
    isAdmin.value = !!user?.is_admin
    return loadConfig(true)
  }).catch(() => loadConfig(true))
})
</script>

<style scoped>
.settings-basic-page {
  width: 100%;
  height: 100%;
  min-height: 0;
}

.settings-section-card :deep(.el-card__body) {
  padding: 20px;
}

.settings-section-card :deep(.el-card__header) {
  padding: 14px 20px;
}

.settings-section-heading h3 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 17px;
  line-height: 1.3;
}

.settings-section-heading p {
  margin: 5px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.settings-section-form {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 26px;
}

.settings-section-form :deep(.el-form-item) {
  min-width: 0;
  margin: 0;
}

.settings-section-form :deep(.el-form-item__label) {
  margin-bottom: 4px;
  padding: 0;
  color: var(--el-text-color-primary);
  font-weight: 600;
  line-height: 1.4;
}

.settings-field--wide,
.settings-report-schedule {
  grid-column: 1 / -1;
}

.settings-value-field {
  width: 100%;
  min-width: 0;
}

.settings-value-control {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
}

.settings-value-control > span {
  color: var(--el-text-color-regular);
  font-size: 12px;
  line-height: 1.3;
  white-space: nowrap;
}

.settings-value-control :deep(.el-input-number),
.settings-time-input {
  width: 118px;
  min-width: 0;
  max-width: 100%;
}

.settings-value-field p,
.settings-section-note {
  margin: 5px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.45;
}

.settings-section-note {
  margin: 0;
  padding: 9px 12px;
  border-radius: 6px;
  background: var(--el-color-primary-light-9);
  color: var(--el-text-color-regular);
}

.settings-section-form.domain-notification-form { overflow-y: auto; gap: 16px; padding: 0 2px 8px; }
.domain-notification-panel {
  display: grid;
  align-content: start;
  gap: 12px;
  min-width: 0;
  padding: 16px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
}
.domain-notification-panel h4 { margin: 0; font-size: 14px; }
.domain-notification-panel__heading { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px 8px; min-height: 24px; }
.domain-notification-help { margin: 0; color: var(--el-text-color-regular); font-size: 12px; line-height: 1.5; }
.domain-notification-status { justify-self: start; }
.domain-notification-actions { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.domain-notification-actions__save, .domain-notification-actions__tests { display: flex; flex-wrap: wrap; gap: 8px; }
.domain-notification-actions .el-button + .el-button { margin-left: 0; }
/* A disabled button swallows hover, so the wrapper carries the tooltip that says why. */
.domain-notification-test { display: inline-flex; }
.domain-notification-test .el-button.is-disabled { pointer-events: none; }
.domain-sms-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.domain-sms-phones { display: grid; gap: 6px; width: 100%; }
@media (max-width: 768px) {
  .domain-notification-panel { grid-column: 1 / -1; padding: 12px; }
  .domain-sms-grid { grid-template-columns: minmax(0, 1fr); }
}

.settings-section-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.admin-settings__card { display: flex; flex: 1 1 0; flex-direction: column; min-height: 0; }
.admin-settings__card :deep(.el-card__body) { display: flex; flex: 1 1 0; flex-direction: column; min-height: 0; }
.settings-layout--basic > .admin-settings__card > :deep(.el-card__body) > .el-form { flex: 1 1 0; min-height: 0; }
.settings-layout--basic .settings-section-form { align-content: start; }
.settings-section-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

@media (min-width: 950px) {
  .settings-section-form--schedule {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .settings-report-schedule {
    grid-column: auto;
  }
}

.settings-root {
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
}

.settings-logs-page {
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
}

.settings-logs-page :deep(.viewport-list-card) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
}

.settings-logs-page :deep(.viewport-list-card > .el-card__body) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  padding: 10px 12px;
}

.ping-logs-toolbar,
.ping-logs-toolbar__controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ping-logs-toolbar { flex-wrap: wrap; }
.ping-logs-toolbar__controls { width: min(405px, 100%); }
.ping-logs-toolbar__controls :deep(.el-select) { flex: 0 0 100px; }

.ping-logs-table-area {
  position: relative;
  flex: 1 1 0;
  min-height: 0;
  min-width: 0;
}

.ping-logs-table {
  width: 100%;
}

.ping-logs-table :deep(.el-table__row td.el-table__cell) {
  height: 36px;
  padding-block: 0;
}


.ping-logs-pager {
  display: flex;
  flex: 0 0 auto;
  justify-content: center;
  padding-top: 8px;
}

@media (max-width: 768px) {
  .settings-layout {
    gap: 8px;
  }

  .settings-section-select {
    width: 100%;
  }

  .settings-section-card :deep(.el-card__body) {
    padding: 12px;
  }

  .settings-section-card :deep(.el-card__header) {
    padding: 10px 12px;
  }

  .settings-section-form {
    gap: 10px 12px;
  }

  .settings-section-form :deep(.el-form-item__label) {
    font-size: 13px;
  }

  .settings-value-control {
    gap: 5px;
  }

  .settings-value-control > span {
    white-space: normal;
  }

  .settings-value-control :deep(.el-input-number) {
    width: 100px;
    flex: 0 1 100px;
  }

  .settings-section-actions {
    margin-top: 12px;
    padding-top: 8px;
  }

  .settings-logs-page {
    display: flex;
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .ping-logs-mobile {
    display: flex;
    flex-direction: column;
    gap: 12px;
    height: 100%;
    width: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .ping-logs-mobile__toolbar {
    flex: 0 0 auto;
    border-radius: 14px;
  }

  .ping-logs-mobile__toolbar :deep(.el-card__body) { padding: 10px; }

  .ping-logs-mobile__filters {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    margin-top: 10px;
  }

  .ping-logs-mobile__list {
    position: relative;
    flex: 1 1 0;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .ping-logs-mobile__item {
    flex: 0 0 104px;
    box-sizing: border-box;
    height: 104px;
    padding: 8px 10px;
    border: 1px solid #edf2f7;
    border-radius: 14px;
    background: #fff;
  }

  .ping-logs-mobile__head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
  }

  .ping-logs-mobile__head > div { min-width: 0; }

  .ping-logs-mobile__name {
    font-size: 15px;
    font-weight: 700;
    color: #111827;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ping-logs-mobile__address {
    display: block;
    max-width: 100%;
    margin-top: 2px;
    padding: 0;
    border: 0;
    background: transparent;
    font-size: 12px;
    color: #2563eb;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ping-logs-mobile__metrics {
    display: grid;
    grid-template-columns: repeat(3, auto) minmax(0, 1fr);
    gap: 6px;
    margin-top: 8px;
    font-size: 12px;
    color: #4b5563;
  }

  .ping-logs-mobile__time {
    margin-top: 6px;
    font-size: 12px;
    color: #9ca3af;
  }

  .ping-logs-mobile__pager {
    flex: 0 0 auto;
    display: flex;
    justify-content: center;
  }
}

@media (min-width: 500px) and (max-width: 768px) and (max-height: 430px) {
  .ping-logs-mobile {
    gap: 6px;
  }

  .ping-logs-mobile__toolbar :deep(.el-card__body) {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 8px;
    padding-block: 6px;
  }

  .ping-logs-mobile__filters {
    grid-template-columns: 104px auto;
    gap: 8px;
    margin-top: 0;
  }

  .ping-logs-mobile__list :deep(.el-empty) {
    --el-empty-padding: 8px 0;
    --el-empty-description-margin-top: 6px;
  }
}

@media (max-width: 480px) {
  .settings-field--mobile-wide {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) and (max-height: 520px) {
  .settings-layout {
    gap: 6px;
  }

  .settings-section-card :deep(.el-card__header),
  .settings-section-card :deep(.el-card__body) {
    padding: 8px 10px;
  }

  .settings-section-heading p {
    display: none;
  }

  .settings-section-form {
    gap: 6px 10px;
  }

  .settings-section-actions {
    margin-top: 6px;
    padding-top: 6px;
  }
}

@media (min-width: 481px) and (max-width: 768px) and (max-height: 520px) {
  .settings-section-form--schedule {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .settings-report-schedule {
    grid-column: auto;
  }
}

@media (min-width: 560px) and (max-width: 768px) and (max-height: 400px) {
  .settings-section-card :deep(.el-card__header) {
    display: none;
  }

  .settings-section-form--landscape-row {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .settings-value-field p,
  .settings-section-note {
    font-size: 11px;
    line-height: 1.35;
  }

  .settings-section-note {
    padding: 5px 8px;
  }
}
</style>

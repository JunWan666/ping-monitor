<template>
  <div class="settings-root">
    <div v-if="props.activeTab === 'settings-basic' && isMobile" class="settings-mobile-page">
      <div class="settings-mobile-section-nav">
        <button
          v-for="item in mobileBasicSections"
          :key="item.key"
          type="button"
          class="settings-mobile-section-nav__item"
          :class="{ active: mobileBasicSection === item.key }"
          @click="mobileBasicSection = item.key"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="settings-mobile-scroll">
        <el-card v-if="mobileBasicSection === 'monitor'" shadow="never" class="settings-mobile-card">
          <template #header>
            <span>监控配置</span>
          </template>
          <el-form :model="config" label-position="top" label-width="auto" class="settings-mobile-form">
            <el-form-item label="检测间隔">
              <div class="settings-mobile-field">
                <el-input-number v-model="config.check_interval" :min="1" :max="1440" />
                <span>分钟</span>
              </div>
              <div class="settings-mobile-tip">建议 1-60 分钟，过小会增加系统负担。</div>
            </el-form-item>
            <el-form-item label="每次发送包数">
              <div class="settings-mobile-field">
                <el-input-number v-model="config.packet_count" :min="1" :max="100" />
                <span>个</span>
              </div>
              <div class="settings-mobile-tip">建议 10-20 个，包数越多结果越准确但耗时越长。</div>
            </el-form-item>
            <el-form-item label="超时时间">
              <div class="settings-mobile-field">
                <el-input-number v-model="config.packet_timeout" :min="1" :max="10" />
                <span>秒</span>
              </div>
              <div class="settings-mobile-tip">建议 2-5 秒，单个 Ping 包等待响应的最长时间。</div>
            </el-form-item>
            <el-form-item label="地理位置自动刷新">
              <div class="settings-mobile-switch">
                <el-switch v-model="config.auto_refresh_location" />
                <span>{{ config.auto_refresh_location ? '已开启：每次 Ping / 监控都尝试刷新位置' : '已关闭：仅在位置信息为空时自动补全' }}</span>
              </div>
              <div class="settings-mobile-tip">开启后，每次监控或手动 Ping 都会尝试刷新地理位置；关闭后保留已有位置，只对空白位置自动补全。</div>
            </el-form-item>
            </el-form>
          </el-card>

        <el-card v-else-if="mobileBasicSection === 'data'" shadow="never" class="settings-mobile-card">
          <template #header>
            <span>数据维护配置</span>
          </template>
          <el-form :model="config" label-position="top" label-width="auto" class="settings-mobile-form">
            <el-form-item label="原始数据保留">
              <div class="settings-mobile-field">
                <el-input-number v-model="config.data_retention_days" :min="7" :max="365" />
                <span>天</span>
              </div>
              <div class="settings-mobile-tip">原始 Ping 记录超过保留天数后自动清理，聚合数据会永久保留。</div>
            </el-form-item>
            <el-form-item label="数据清理时间">
              <el-time-select
                v-model="config.cleanup_time"
                start="00:00"
                step="01:00"
                end="23:00"
                placeholder="选择时间"
              />
              <div class="settings-mobile-tip">每天执行数据清理的时间，建议选择业务低峰时段。</div>
            </el-form-item>
            <el-form-item label="数据聚合间隔">
              <div class="settings-mobile-field">
                <el-input-number v-model="config.aggregate_interval" :min="1" :max="24" />
                <span>小时</span>
              </div>
              <div class="settings-mobile-tip">每隔多久执行一次小时级数据聚合，建议 1-6 小时。</div>
            </el-form-item>
            <el-form-item label="仪表盘数据点">
              <div class="settings-mobile-field">
                <el-input-number v-model="config.dashboard_chart_points" :min="3" :max="50" />
                <span>次检测</span>
              </div>
              <div class="settings-mobile-tip">仪表盘趋势图显示多少次检测的数据，建议 12 次。</div>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card v-else-if="mobileBasicSection === 'alert'" shadow="never" class="settings-mobile-card">
          <template #header>
            <span>告警通知配置</span>
          </template>
          <el-form :model="config" label-position="top" label-width="auto" class="settings-mobile-form">
            <el-form-item label="告警平台">
              <el-select v-model="notificationPlatform" placeholder="选择告警平台">
                <el-option label="不启用" value="none" />
                <el-option label="Server酱" value="serverchan" />
                <el-option label="钉钉机器人" value="dingtalk" />
                <el-option label="企业微信机器人" value="weixin" />
              </el-select>
            </el-form-item>
            <el-form-item label="通知模式">
              <el-radio-group v-model="config.notification_mode" class="settings-mobile-radio">
                <el-radio-button label="status_change">状态变化</el-radio-button>
                <el-radio-button label="every_time">每次异常</el-radio-button>
              </el-radio-group>
              <div class="settings-mobile-tip">状态变化：仅在正常↔异常转换时通知；每次异常：每次检测到异常都发送通知。</div>
            </el-form-item>
            <el-form-item v-if="notificationPlatform === 'serverchan'" label="Server酱密钥">
              <el-input v-model="config.serverchan_key" placeholder="请输入 Server酱 SendKey" clearable />
              <div class="settings-mobile-tip">
                获取地址：<a href="https://sct.ftqq.com" target="_blank">https://sct.ftqq.com</a>
              </div>
            </el-form-item>
            <el-form-item v-if="notificationPlatform === 'dingtalk'" label="Webhook 地址">
              <el-input v-model="config.webhook_url" placeholder="告警钉钉机器人 Webhook URL" clearable />
            </el-form-item>
            <el-form-item v-if="notificationPlatform === 'dingtalk'" label="加签密钥">
              <el-input v-model="config.webhook_secret" placeholder="告警机器人加签密钥，可选" clearable />
              <div class="settings-mobile-tip">安全设置为“加签”时填写，以 SEC 开头。</div>
            </el-form-item>
            <el-form-item v-if="notificationPlatform === 'weixin'" label="Webhook 地址">
              <el-input v-model="config.webhook_url" placeholder="企业微信机器人 Webhook URL" clearable />
            </el-form-item>
            <el-button
              v-if="notificationPlatform !== 'none'"
              type="success"
              plain
              class="settings-mobile-full-btn"
              :loading="testingNotification"
              :disabled="!canTestNotification"
              @click="testNotification"
            >
              <el-icon><Bell /></el-icon>
              测试告警通知
            </el-button>
          </el-form>
        </el-card>

        <el-card v-else shadow="never" class="settings-mobile-card">
          <template #header>
            <span>报表通知配置（钉钉）</span>
          </template>
          <div class="settings-mobile-intro">
            报表机器人与告警机器人完全分离，适合把日报、周报、月报发到单独群里。日报统计上一自然日并对比前一日，周报统计上一自然周，月报统计上一自然月。
          </div>
          <el-form :model="config" label-position="top" label-width="auto" class="settings-mobile-form">
            <el-form-item label="报表 Webhook 地址">
              <el-input v-model="config.report_webhook_url" placeholder="报表专用钉钉机器人 Webhook URL" clearable />
            </el-form-item>
            <el-form-item label="报表加签密钥">
              <el-input v-model="config.report_webhook_secret" placeholder="报表机器人加签密钥，可选" clearable />
              <div class="settings-mobile-tip">建议新建一个专门收报表的钉钉机器人，避免和实时告警混在一起。</div>
            </el-form-item>

            <div class="settings-mobile-report-card">
              <div class="settings-mobile-report-card__head">
                <div>
                  <strong>日报</strong>
                  <span>默认发送昨日数据，对比前一日</span>
                </div>
                <el-switch v-model="config.daily_report_enabled" />
              </div>
              <el-time-select
                v-model="config.daily_report_time"
                start="00:00"
                step="00:30"
                end="23:30"
                placeholder="发送时间"
                :disabled="!config.daily_report_enabled"
              />
              <el-button
                link
                type="primary"
                class="settings-mobile-report-card__send"
                @click="sendReport('daily')"
                :loading="sendingReportType === 'daily'"
                :disabled="!canSendDingTalkReport"
              >
                立即发送
              </el-button>
            </div>

            <div class="settings-mobile-report-card">
              <div class="settings-mobile-report-card__head">
                <div>
                  <strong>周报</strong>
                  <span>固定汇总上周数据，对比再前一周</span>
                </div>
                <el-switch v-model="config.weekly_report_enabled" />
              </div>
              <el-time-select
                v-model="config.weekly_report_time"
                start="00:00"
                step="00:30"
                end="23:30"
                placeholder="发送时间"
                :disabled="!config.weekly_report_enabled"
              />
              <el-button
                link
                type="primary"
                class="settings-mobile-report-card__send"
                @click="sendReport('weekly')"
                :loading="sendingReportType === 'weekly'"
                :disabled="!canSendDingTalkReport"
              >
                立即发送
              </el-button>
            </div>

            <div class="settings-mobile-report-card">
              <div class="settings-mobile-report-card__head">
                <div>
                  <strong>月报</strong>
                  <span>固定汇总上月数据，对比再前一月</span>
                </div>
                <el-switch v-model="config.monthly_report_enabled" />
              </div>
              <el-time-select
                v-model="config.monthly_report_time"
                start="00:00"
                step="00:30"
                end="23:30"
                placeholder="发送时间"
                :disabled="!config.monthly_report_enabled"
              />
              <el-button
                link
                type="primary"
                class="settings-mobile-report-card__send"
                @click="sendReport('monthly')"
                :loading="sendingReportType === 'monthly'"
                :disabled="!canSendDingTalkReport"
              >
                立即发送
              </el-button>
            </div>
          </el-form>
        </el-card>
      </div>

      <div class="settings-mobile-actions">
        <el-button type="primary" @click="saveConfig" :loading="saving">
          <el-icon><Select /></el-icon>
          保存
        </el-button>
        <el-button @click="loadConfig">
          <el-icon><Refresh /></el-icon>
          重置
        </el-button>
      </div>
    </div>

    <!-- 基本设置 -->
    <div v-else-if="props.activeTab === 'settings-basic'" class="settings-page">
      <!-- 监控配置和数据维护配置 - 左右布局 -->
      <el-row :gutter="20" style="margin-bottom: 20px">
        <!-- 左侧：监控配置 -->
        <el-col :span="12">
          <el-card shadow="hover" style="height: 100%">
            <template #header>
              <span style="font-weight: bold">监控配置</span>
            </template>
            <el-form :model="config" label-width="120px">
              <el-form-item label="检测间隔">
                <div style="display: flex; flex-direction: column; width: 100%">
                  <div style="display: flex; align-items: center">
                    <el-input-number v-model="config.check_interval" :min="1" :max="1440" style="width: 150px" />
                    <span style="margin-left: 10px">分钟</span>
                  </div>
                  <div style="color: #909399; font-size: 12px; margin-top: 8px">
                    建议：1-60分钟，过小会增加系统负担
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="每次发送包数">
                <div style="display: flex; flex-direction: column; width: 100%">
                  <div style="display: flex; align-items: center">
                    <el-input-number v-model="config.packet_count" :min="1" :max="100" style="width: 150px" />
                    <span style="margin-left: 10px">个</span>
                  </div>
                  <div style="color: #909399; font-size: 12px; margin-top: 8px">
                    建议：10-20个，包数越多结果越准确但耗时越长
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="超时时间">
                <div style="display: flex; flex-direction: column; width: 100%">
                  <div style="display: flex; align-items: center">
                    <el-input-number v-model="config.packet_timeout" :min="1" :max="10" style="width: 150px" />
                    <span style="margin-left: 10px">秒</span>
                  </div>
                  <div style="color: #909399; font-size: 12px; margin-top: 8px">
                    建议：2-5秒，单个Ping包等待响应的最长时间，超过则认为丢包
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="地理位置自动刷新">
                <div style="display: flex; flex-direction: column; width: 100%">
                  <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap">
                    <el-switch v-model="config.auto_refresh_location" />
                    <span style="color: #606266">
                      {{ config.auto_refresh_location ? '已开启：每次 Ping / 监控都尝试刷新位置' : '已关闭：仅在位置信息为空时自动补全' }}
                    </span>
                  </div>
                  <div style="color: #909399; font-size: 12px; margin-top: 8px">
                    开启后，每次监控或手动 Ping 都会尝试刷新地理位置；关闭后保留已有位置，只对空白位置自动补全。
                  </div>
                </div>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>

        <!-- 右侧：数据维护配置 -->
        <el-col :span="12">
          <el-card shadow="hover" style="height: 100%">
            <template #header>
              <span style="font-weight: bold">数据维护配置</span>
            </template>
            <el-form :model="config" label-width="120px">
              <el-form-item label="原始数据保留">
                <div style="display: flex; flex-direction: column; width: 100%">
                  <div style="display: flex; align-items: center">
                    <el-input-number v-model="config.data_retention_days" :min="7" :max="365" style="width: 150px" />
                    <span style="margin-left: 10px">天</span>
                  </div>
                  <div style="color: #909399; font-size: 12px; margin-top: 8px">
                    原始 Ping 记录保留天数，超过后自动清理（聚合数据会永久保留）
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="数据清理时间">
                <div style="display: flex; flex-direction: column; width: 100%">
                  <el-time-select
                    v-model="config.cleanup_time"
                    start="00:00"
                    step="01:00"
                    end="23:00"
                    placeholder="选择时间"
                    style="width: 150px"
                  />
                  <div style="color: #909399; font-size: 12px; margin-top: 8px">
                    每天执行数据清理的时间，建议选择业务低峰时段
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="数据聚合间隔">
                <div style="display: flex; flex-direction: column; width: 100%">
                  <div style="display: flex; align-items: center">
                    <el-input-number v-model="config.aggregate_interval" :min="1" :max="24" style="width: 150px" />
                    <span style="margin-left: 10px">小时</span>
                  </div>
                  <div style="color: #909399; font-size: 12px; margin-top: 8px">
                    每隔多久执行一次小时级数据聚合，建议 1-6 小时
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="仪表盘数据点">
                <div style="display: flex; flex-direction: column; width: 100%">
                  <div style="display: flex; align-items: center">
                    <el-input-number v-model="config.dashboard_chart_points" :min="3" :max="50" style="width: 150px" />
                    <span style="margin-left: 10px">次检测</span>
                  </div>
                  <div style="color: #909399; font-size: 12px; margin-top: 8px">
                    仪表盘趋势图显示多少次检测的数据，建议 12 次（1小时）
                  </div>
                </div>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" class="settings-dual-card-row">
        <el-col :xs="24" :lg="12">
          <el-card shadow="hover" class="settings-dual-card">
            <template #header>
              <span style="font-weight: bold">告警通知配置</span>
            </template>
            <el-form :model="config" label-width="150px" class="settings-dual-form">
              <el-form-item label="告警平台">
                <el-select v-model="notificationPlatform" placeholder="选择告警平台" style="width: 100%">
                  <el-option label="不启用" value="none" />
                  <el-option label="Server酱" value="serverchan" />
                  <el-option label="钉钉机器人" value="dingtalk" />
                  <el-option label="企业微信机器人" value="weixin" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="通知模式">
                <el-radio-group v-model="config.notification_mode">
                  <el-radio label="status_change">状态转换时通知</el-radio>
                  <el-radio label="every_time">每次异常都通知</el-radio>
                </el-radio-group>
                <div style="color: #909399; font-size: 12px; margin-top: 5px">
                  状态转换：仅在正常↔异常转换时通知；每次异常：每次检测到异常都发送通知
                </div>
              </el-form-item>

              <!-- Server酱配置 -->
              <template v-if="notificationPlatform === 'serverchan'">
                <el-form-item label="Server酱密钥">
                  <el-input 
                    v-model="config.serverchan_key" 
                    placeholder="请输入Server酱SendKey" 
                    clearable
                  />
                  <div style="color: #909399; font-size: 12px; margin-top: 5px">
                    获取地址: <a href="https://sct.ftqq.com" target="_blank">https://sct.ftqq.com</a>
                  </div>
                </el-form-item>
              </template>

              <!-- 钉钉配置 -->
              <template v-if="notificationPlatform === 'dingtalk'">
                <el-form-item label="Webhook地址">
                  <el-input 
                    v-model="config.webhook_url" 
                    placeholder="告警钉钉机器人 Webhook URL" 
                    clearable
                  />
                </el-form-item>
                <el-form-item label="加签密钥">
                  <el-input 
                    v-model="config.webhook_secret" 
                    placeholder="告警机器人加签密钥(可选)" 
                    clearable
                  />
                  <div style="color: #909399; font-size: 12px; margin-top: 5px">
                    安全设置为“加签”时填写，以SEC开头
                  </div>
                </el-form-item>
              </template>

              <!-- 企业微信配置 -->
              <template v-if="notificationPlatform === 'weixin'">
                <el-form-item label="Webhook地址">
                  <el-input 
                    v-model="config.webhook_url" 
                    placeholder="企业微信机器人 Webhook URL" 
                    clearable
                  />
                </el-form-item>
              </template>

              <!-- 测试按钮 -->
              <el-form-item v-if="notificationPlatform !== 'none'">
                <el-button 
                  type="success" 
                  @click="testNotification" 
                  :loading="testingNotification"
                  :disabled="!canTestNotification"
                >
                  <el-icon><Bell /></el-icon> 测试告警通知
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="12">
          <el-card shadow="hover" class="settings-dual-card">
            <template #header>
              <span style="font-weight: bold">报表通知配置（钉钉）</span>
            </template>
            <div class="report-config-intro">
              报表机器人与告警机器人完全分离，适合把日报、周报、月报发到单独群里。日报统计上一自然日并对比前一日，周报统计上一自然周并对比再前一周，月报统计上一自然月并对比再前一月。
            </div>
            <el-form :model="config" label-width="150px" class="settings-dual-form">
              <el-form-item label="报表Webhook地址">
                <el-input
                  v-model="config.report_webhook_url"
                  placeholder="报表专用钉钉机器人 Webhook URL"
                  clearable
                />
              </el-form-item>

              <el-form-item label="报表加签密钥">
                <el-input
                  v-model="config.report_webhook_secret"
                  placeholder="报表机器人加签密钥(可选)"
                  clearable
                />
                <div style="color: #909399; font-size: 12px; margin-top: 5px">
                  建议新建一个专门收报表的钉钉机器人，避免和实时告警混在一起
                </div>
              </el-form-item>

              <el-form-item label="日报">
                <div style="display: flex; flex-direction: column; width: 100%; gap: 8px">
                  <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap">
                    <el-switch v-model="config.daily_report_enabled" />
                    <span style="color: #606266">每日发送</span>
                    <el-time-select
                      v-model="config.daily_report_time"
                      start="00:00"
                      step="00:30"
                      end="23:30"
                      placeholder="发送时间"
                      style="width: 150px"
                      :disabled="!config.daily_report_enabled"
                    />
                    <el-button
                      link
                      type="primary"
                      @click="sendReport('daily')"
                      :loading="sendingReportType === 'daily'"
                      :disabled="!canSendDingTalkReport"
                    >
                      立即发送
                    </el-button>
                  </div>
                  <div style="color: #909399; font-size: 12px">默认发送昨日数据，对比前一日</div>
                </div>
              </el-form-item>

              <el-form-item label="周报">
                <div style="display: flex; flex-direction: column; width: 100%; gap: 8px">
                  <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap">
                    <el-switch v-model="config.weekly_report_enabled" />
                    <span style="color: #606266">每周一发送</span>
                    <el-time-select
                      v-model="config.weekly_report_time"
                      start="00:00"
                      step="00:30"
                      end="23:30"
                      placeholder="发送时间"
                      style="width: 150px"
                      :disabled="!config.weekly_report_enabled"
                    />
                    <el-button
                      link
                      type="primary"
                      @click="sendReport('weekly')"
                      :loading="sendingReportType === 'weekly'"
                      :disabled="!canSendDingTalkReport"
                    >
                      立即发送
                    </el-button>
                  </div>
                  <div style="color: #909399; font-size: 12px">固定汇总上周数据，对比再前一周</div>
                </div>
              </el-form-item>

              <el-form-item label="月报">
                <div style="display: flex; flex-direction: column; width: 100%; gap: 8px">
                  <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap">
                    <el-switch v-model="config.monthly_report_enabled" />
                    <span style="color: #606266">每月 1 日发送</span>
                    <el-time-select
                      v-model="config.monthly_report_time"
                      start="00:00"
                      step="00:30"
                      end="23:30"
                      placeholder="发送时间"
                      style="width: 150px"
                      :disabled="!config.monthly_report_enabled"
                    />
                    <el-button
                      link
                      type="primary"
                      @click="sendReport('monthly')"
                      :loading="sendingReportType === 'monthly'"
                      :disabled="!canSendDingTalkReport"
                    >
                      立即发送
                    </el-button>
                  </div>
                  <div style="color: #909399; font-size: 12px">固定汇总上月数据，对比再前一月</div>
                </div>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
      </el-row>

      <div class="settings-dual-actions">
        <el-button type="primary" @click="saveConfig" :loading="saving">
          <el-icon><Select /></el-icon> 保存配置
        </el-button>
        <el-button @click="loadConfig">
          <el-icon><Refresh /></el-icon> 重置
        </el-button>
      </div>
    </div>

    <!-- Ping日志 -->
    <div v-else-if="props.activeTab === 'settings-logs'" class="settings-logs-page">
      <div v-if="isMobile" class="ping-logs-mobile">
        <el-card shadow="never" class="ping-logs-mobile__toolbar">
          <el-input
            v-model="hostSearchKeyword"
            placeholder="搜索主机名称或地址"
            clearable
            @clear="loadPingLogs"
            @keyup.enter="loadPingLogs"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <div class="ping-logs-mobile__filters">
            <el-select v-model="selectedStatus" placeholder="状态" @change="loadPingLogs">
              <el-option label="全部状态" value="" />
              <el-option label="正常" value="normal" />
              <el-option label="异常" value="abnormal" />
            </el-select>
            <el-button type="primary" :loading="false" @click="loadPingLogs">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </el-card>

        <div class="ping-logs-mobile__list">
          <el-empty v-if="pingLogs.length === 0" description="暂无 Ping 日志" :image-size="72" />
          <div v-for="row in pingLogs" :key="row.id" class="ping-logs-mobile__item">
            <div class="ping-logs-mobile__head">
              <div>
                <div class="ping-logs-mobile__name">{{ row.host_name }}</div>
                <div class="ping-logs-mobile__address" @click="copyAddress(row.host_address)">{{ row.host_address }}</div>
              </div>
              <el-tag :type="row.status === '正常' ? 'success' : row.status === '异常' ? 'warning' : row.status === '离线' ? 'danger' : 'info'" effect="plain">
                {{ row.status }}
              </el-tag>
            </div>
            <div class="ping-logs-mobile__metrics">
              <span>发 {{ row.packet_sent }}</span>
              <span>收 {{ row.packet_received }}</span>
              <span>丢包 {{ row.packet_loss }}%</span>
              <span>平均 {{ row.avg_rtt || '-' }}ms</span>
            </div>
            <div class="ping-logs-mobile__time">{{ new Date(row.check_time).toLocaleString() }}</div>
          </div>
        </div>

        <div class="ping-logs-mobile__pager">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="totalLogs"
            layout="prev, pager, next"
            :small="true"
            @size-change="loadPingLogs"
            @current-change="loadPingLogs"
          />
        </div>
      </div>

      <el-card v-else shadow="hover">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-weight: bold">主机Ping记录</span>
            <div>
              <el-input
                v-model="hostSearchKeyword"
                placeholder="搜索主机名称或地址"
                clearable
                style="width: 250px; margin-right: 10px"
                @clear="loadPingLogs"
                @keyup.enter="loadPingLogs"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-select v-model="selectedStatus" placeholder="选择状态" style="width: 120px; margin-right: 10px" @change="loadPingLogs">
                <el-option label="全部状态" value="" />
                <el-option label="正常" value="normal" />
                <el-option label="异常" value="abnormal" />
              </el-select>
              <el-button type="primary" @click="loadPingLogs">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
            </div>
          </div>
        </template>

        <el-table :data="pingLogs" style="width: 100%" max-height="600">
          <el-table-column prop="id" label="ID" width="80" align="center" header-align="center" />
          <el-table-column label="主机" width="150" align="center" header-align="center">
            <template #default="{ row }">
              {{ row.host_name }}
            </template>
          </el-table-column>
          <el-table-column label="地址" width="200" align="center" header-align="center">
            <template #default="{ row }">
              <span 
                @click="copyAddress(row.host_address)" 
                style="cursor: pointer; color: #409eff; text-decoration: underline"
                :title="'点击复制: ' + row.host_address"
              >
                {{ row.host_address }}
              </span>
              <el-icon 
                @click="copyAddress(row.host_address)" 
                style="margin-left: 5px; cursor: pointer; color: #409eff"
                :title="'复制地址'"
              >
                <CopyDocument />
              </el-icon>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center" header-align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === '正常' ? 'success' : row.status === '异常' ? 'warning' : row.status === '离线' ? 'danger' : 'info'">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="packet_sent" label="发送" width="80" align="center" header-align="center" />
          <el-table-column prop="packet_received" label="接收" width="80" align="center" header-align="center" />
          <el-table-column label="丢包率" width="100" align="center" header-align="center">
            <template #default="{ row }">
              <el-tag :type="row.packet_loss > 20 ? 'danger' : row.packet_loss > 0 ? 'warning' : 'success'">
                {{ row.packet_loss }}%
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="延迟(ms)" width="180" align="center" header-align="center">
            <template #default="{ row }">
              最小: {{ row.min_rtt || '-' }} / 
              平均: {{ row.avg_rtt || '-' }} / 
              最大: {{ row.max_rtt || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="检测时间" width="180" align="center" header-align="center">
            <template #default="{ row }">
              {{ new Date(row.check_time).toLocaleString() }}
            </template>
          </el-table-column>
        </el-table>

        <div style="margin-top: 20px; text-align: right">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[20, 50, 100, 200]"
            :total="totalLogs"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="loadPingLogs"
            @current-change="loadPingLogs"
            background
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useViewport } from '../lib/useViewport'

const props = defineProps({
  activeTab: {
    type: String,
    default: 'settings-basic'
  }
})

const { isMobile } = useViewport()
const mobileBasicSections = [
  { key: 'monitor', label: '监控' },
  { key: 'data', label: '维护' },
  { key: 'alert', label: '告警' },
  { key: 'report', label: '报表' }
]
const mobileBasicSection = ref('monitor')

const saving = ref(false)
const testingNotification = ref(false)
const sendingReportType = ref('')
const notificationPlatform = ref('none')
const hosts = ref([])
const pingLogs = ref([])
const hostSearchKeyword = ref('')
const selectedStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalLogs = ref(0)

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
  dashboard_chart_points: 12,
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

const loadConfig = async () => {
  try {
    const data = await api.getConfig()
    Object.assign(config, data)
    
    // 根据配置自动选择平台
    if (data.serverchan_key) {
      notificationPlatform.value = 'serverchan'
    } else if (data.webhook_url) {
      // 根据URL判断是钉钉还是企业微信
      if (data.webhook_url.includes('oapi.dingtalk.com')) {
        notificationPlatform.value = 'dingtalk'
      } else if (data.webhook_url.includes('qyapi.weixin.qq.com')) {
        notificationPlatform.value = 'weixin'
      } else {
        notificationPlatform.value = 'dingtalk' // 默认钉钉
      }
    } else {
      notificationPlatform.value = 'none'
    }
  } catch (error) {
    ElMessage.error('加载配置失败')
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    // 根据选择的平台决定发送哪些配置
    let configData = {
      check_interval: config.check_interval,
      packet_count: config.packet_count,
      packet_timeout: config.packet_timeout,
      notification_mode: config.notification_mode,
      data_retention_days: config.data_retention_days,
      cleanup_time: config.cleanup_time,
      aggregate_interval: config.aggregate_interval,
      dashboard_chart_points: config.dashboard_chart_points,
      auto_refresh_location: config.auto_refresh_location,
      report_webhook_url: config.report_webhook_url,
      report_webhook_secret: config.report_webhook_secret,
      daily_report_enabled: config.daily_report_enabled,
      daily_report_time: config.daily_report_time,
      weekly_report_enabled: config.weekly_report_enabled,
      weekly_report_time: config.weekly_report_time,
      monthly_report_enabled: config.monthly_report_enabled,
      monthly_report_time: config.monthly_report_time
    }
    
    if (notificationPlatform.value === 'none') {
      // 不启用通知，发送空值给后端（但前端保留输入框的值）
      configData.serverchan_key = ''
      configData.webhook_url = ''
      configData.webhook_secret = ''
    } else if (notificationPlatform.value === 'serverchan') {
      // Server酱，只发送Server酱配置
      configData.serverchan_key = config.serverchan_key || ''
      configData.webhook_url = ''
      configData.webhook_secret = ''
    } else {
      // Webhook(钉钉/企业微信)，只发送Webhook配置
      configData.serverchan_key = ''
      configData.webhook_url = config.webhook_url || ''
      configData.webhook_secret = config.webhook_secret || ''
    }
    
    await api.updateConfig(configData)
    ElMessage.success('配置保存成功')
    
    // 保存成功后不重新加载，保持前端输入框的值
    // 这样切换平台时之前的配置还在
  } catch (error) {
    ElMessage.error('配置保存失败')
  } finally {
    saving.value = false
  }
}

const loadHosts = async () => {
  try {
    hosts.value = await api.getHosts()
  } catch (error) {
    ElMessage.error('加载主机列表失败')
  }
}

const loadPingLogs = async () => {
  try {
    const status = selectedStatus.value || null
    const search = hostSearchKeyword.value || null
    const data = await api.getPingLogs(null, currentPage.value, pageSize.value, status, search)
    pingLogs.value = data.items || []
    totalLogs.value = data.total || 0
  } catch (error) {
    ElMessage.error('加载Ping日志失败')
  }
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

// 监听 activeTab 变化，自动加载对应数据
watch(() => props.activeTab, (newTab) => {
  if (newTab === 'settings-logs') {
    loadPingLogs()
  }
  if (newTab === 'settings-basic' && isMobile.value) {
    mobileBasicSection.value = 'monitor'
  }
})

onMounted(() => {
  loadConfig()
  loadHosts()
  if (props.activeTab === 'settings-basic' && isMobile.value) {
    mobileBasicSection.value = 'monitor'
  }
  // 首次进入如果是 Ping 日志标签，立即加载数据
  if (props.activeTab === 'settings-logs') {
    loadPingLogs()
  }
})
</script>

<style scoped>
.settings-page {
  width: 100%;
  min-height: 0;
  min-width: 0;
}

.settings-root {
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow-x: hidden;
}

.settings-mobile-page {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  row-gap: 10px;
  width: 100%;
  max-width: 100%;
  height: 100%;
  min-height: 0;
  position: relative;
  overflow: hidden;
  box-sizing: border-box;
}

.settings-mobile-section-nav {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.settings-mobile-section-nav__item {
  height: 36px;
  border: 1px solid #dbeafe;
  border-radius: 999px;
  background: #fff;
  color: #4b5563;
  font-size: 12px;
  font-weight: 600;
}

.settings-mobile-section-nav__item.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #2563eb;
}

.settings-mobile-scroll {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  height: 100%;
  width: 100%;
  max-width: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding-bottom: 24px;
  box-sizing: border-box;
  -webkit-overflow-scrolling: touch;
}

.settings-mobile-card {
  flex: 0 0 auto;
  border-radius: 14px;
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
}

.settings-mobile-scroll > .settings-mobile-card {
  flex: 0 0 auto;
}

.settings-mobile-card :deep(.el-card__header) {
  padding: 14px 14px 0;
  border-bottom: none;
  font-weight: 700;
}

.settings-mobile-card :deep(.el-card__body) {
  padding: 14px;
}

.settings-mobile-form :deep(.el-form-item) {
  display: block;
  width: 100%;
  min-width: 0;
  margin-bottom: 16px;
}

.settings-mobile-form :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

.settings-mobile-form :deep(.el-form-item__label) {
  display: block;
  width: auto !important;
  height: auto;
  line-height: 1.4;
  padding-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.settings-mobile-form :deep(.el-form-item__content) {
  width: 100%;
  min-width: 0;
  margin-left: 0 !important;
}

.settings-mobile-form :deep(.el-input),
.settings-mobile-form :deep(.el-select),
.settings-mobile-form :deep(.el-input-number),
.settings-mobile-form :deep(.el-time-select) {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.settings-mobile-form :deep(.el-input__wrapper),
.settings-mobile-form :deep(.el-select__wrapper) {
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
}

.settings-mobile-form :deep(.el-input-number .el-input) {
  width: 100%;
}

.settings-mobile-field {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-width: 0;
}

.settings-mobile-field > span,
.settings-mobile-switch span,
.settings-mobile-tip {
  color: #6b7280;
  font-size: 12px;
}

.settings-mobile-tip {
  margin-top: 6px;
  line-height: 1.5;
}

.settings-mobile-tip a {
  color: #2563eb;
  word-break: break-all;
}

.settings-mobile-intro {
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f8fafc;
  color: #4b5563;
  font-size: 12px;
  line-height: 1.7;
}

.settings-mobile-switch {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.settings-mobile-switch span,
.settings-mobile-tip,
.settings-mobile-report-row span {
  overflow-wrap: anywhere;
}

.settings-mobile-radio {
  width: 100%;
}

.settings-mobile-radio :deep(.el-radio-button) {
  width: 50%;
}

.settings-mobile-radio :deep(.el-radio-button__inner) {
  width: 100%;
}

.settings-mobile-full-btn {
  width: 100%;
}

.settings-mobile-report-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 14px 0 8px;
  padding: 12px;
  border: 1px solid #edf2f7;
  border-radius: 12px;
  background: #f8fafc;
  min-width: 0;
}

.settings-mobile-report-row div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.settings-mobile-report-row strong {
  font-size: 14px;
  color: #111827;
}

.settings-mobile-report-row span {
  font-size: 12px;
  color: #6b7280;
}

.settings-mobile-report-card {
  flex: 0 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid #edf2f7;
  border-radius: 12px;
  background: #f8fafc;
  min-width: 0;
}

.settings-mobile-report-card:last-child {
  margin-bottom: 0;
}

.settings-mobile-report-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.settings-mobile-report-card__head > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.settings-mobile-report-card__head strong {
  font-size: 14px;
  color: #111827;
}

.settings-mobile-report-card__head span {
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
  overflow-wrap: anywhere;
}

.settings-mobile-report-card :deep(.el-select),
.settings-mobile-report-card :deep(.el-time-select) {
  width: 100%;
}

.settings-mobile-report-card__send {
  justify-self: start;
  padding-left: 0;
}

.settings-mobile-actions {
  z-index: 5;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  padding: 10px 0 0;
  background: #f5f7fb;
}

.settings-mobile-actions :deep(.el-button) {
  margin-left: 0;
  min-width: 0;
}

.settings-dual-card-row {
  margin-bottom: 20px;
}

.settings-dual-card {
  height: 100%;
}

.settings-dual-form {
  max-width: 100%;
}

.report-config-intro {
  margin-bottom: 20px;
  padding: 12px 14px;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  color: #606266;
  font-size: 12px;
  line-height: 1.7;
}

.settings-dual-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 1439px) {
  .settings-dual-card-row {
    margin-bottom: 16px;
  }
}

@media (max-width: 767px) {
  .settings-page {
    height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
    padding-bottom: 4px;
  }

  .settings-page :deep(.el-row) {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .settings-page :deep(.el-col-12) {
    flex: 0 0 100%;
    max-width: 100%;
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin-bottom: 12px;
  }

  .settings-page :deep(.el-card) {
    border-radius: 14px;
    box-shadow: none;
  }

  .settings-page :deep(.el-card__header) {
    padding: 14px 14px 0;
    border-bottom: none;
  }

  .settings-page :deep(.el-card__body) {
    padding: 14px;
  }

  .settings-page :deep(.el-form-item__label) {
    width: 100% !important;
    margin-bottom: 6px;
    text-align: left;
  }

  .settings-page :deep(.el-form-item__content) {
    margin-left: 0 !important;
    width: 100%;
  }

  .settings-page :deep(.el-input),
  .settings-page :deep(.el-select),
  .settings-page :deep(.el-time-select),
  .settings-page :deep(.el-input-number) {
    width: 100% !important;
  }

  .settings-dual-actions {
    justify-content: flex-start;
    width: 100%;
  }

  .settings-dual-actions :deep(.el-button) {
    flex: 1 1 auto;
    margin-left: 0;
  }

  .settings-logs-page {
    height: 100%;
    min-height: 0;
  }

  .ping-logs-mobile {
    display: flex;
    flex-direction: column;
    gap: 12px;
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .ping-logs-mobile__toolbar {
    flex: 0 0 auto;
    border-radius: 14px;
  }

  .ping-logs-mobile__filters {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    margin-top: 10px;
  }

  .ping-logs-mobile__list {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .ping-logs-mobile__item {
    flex: 0 0 auto;
    padding: 12px;
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

  .ping-logs-mobile__name {
    font-size: 15px;
    font-weight: 700;
    color: #111827;
  }

  .ping-logs-mobile__address {
    margin-top: 4px;
    font-size: 12px;
    color: #2563eb;
    word-break: break-all;
  }

  .ping-logs-mobile__metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    margin-top: 12px;
    font-size: 12px;
    color: #4b5563;
  }

  .ping-logs-mobile__time {
    margin-top: 10px;
    font-size: 12px;
    color: #9ca3af;
  }

  .ping-logs-mobile__pager {
    flex: 0 0 auto;
    display: flex;
    justify-content: center;
  }
}
</style>

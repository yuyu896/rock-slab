<script setup lang="ts">
defineProps<{
  task: any
}>()

const emit = defineEmits<{
  (e: 'back'): void
  (e: 'submit', task: any): void
}>()
</script>

<template>
  <div class="scanning-view">
    <div class="scanning-header">
      <button class="back-btn" @click="emit('back')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        返回列表
      </button>
      <div class="scanning-title">{{ task.name }}</div>
      <div class="scanning-progress">
        <span class="progress-num">{{ task.checkedItems }}</span>
        <span class="progress-total">/{{ task.totalItems }}</span>
      </div>
    </div>

    <div class="scanning-content">
      <!-- 扫码区域 -->
      <div class="scan-area">
        <div class="scan-input-wrapper">
          <input
            type="text"
            placeholder="扫描或输入资产编号..."
            class="scan-input"
            autofocus
          />
          <button class="scan-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
              <line x1="7" y1="12" x2="17" y2="12"/>
            </svg>
            扫码
          </button>
        </div>

        <!-- 最近盘点记录 -->
        <div class="recent-checks">
          <h4 class="recent-title">最近盘点</h4>
          <div class="check-list">
            <div class="check-item success">
              <div class="check-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
              <div class="check-info">
                <span class="check-code">A-a00001</span>
                <span class="check-name">Herman Miller办公椅</span>
              </div>
              <span class="check-time">刚刚</span>
            </div>
            <div class="check-item success">
              <div class="check-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
              <div class="check-info">
                <span class="check-code">A-b00015</span>
                <span class="check-name">MacBook Pro 14寸</span>
              </div>
              <span class="check-time">2分钟前</span>
            </div>
            <div class="check-item warning">
              <div class="check-icon warning">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
              </div>
              <div class="check-info">
                <span class="check-code">B-a00008</span>
                <span class="check-name">A4打印纸</span>
                <span class="check-alert">盘亏：账面100，实际85</span>
              </div>
              <span class="check-time">5分钟前</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧信息面板 -->
      <div class="info-panel">
        <div class="panel-card">
          <h4 class="panel-title">盘点进度</h4>
          <div class="progress-ring">
            <svg viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="54" fill="none" stroke="var(--color-bg-elevated)" stroke-width="8" />
              <circle
                cx="60" cy="60" r="54" fill="none" stroke="var(--color-primary)" stroke-width="8"
                stroke-dasharray="339.292" :stroke-dashoffset="339.292 - (339.292 * (task.progress || 0) / 100)"
                stroke-linecap="round" transform="rotate(-90 60 60)"
              />
            </svg>
            <div class="progress-text">{{ task.progress || 0 }}%</div>
          </div>
          <div class="progress-details">
            <div class="detail-row">
              <span>已盘点</span>
              <span class="detail-val">{{ task.checkedItems || 0 }}</span>
            </div>
            <div class="detail-row">
              <span>未盘点</span>
              <span class="detail-val">{{ task.uncheckedCount || 0 }}</span>
            </div>
            <div class="detail-row">
              <span>盘盈</span>
              <span class="detail-val text-success">{{ task.surplusCount || 0 }}</span>
            </div>
            <div class="detail-row">
              <span>盘亏</span>
              <span class="detail-val text-danger">{{ task.missingCount || 0 }}</span>
            </div>
          </div>
        </div>

        <div class="panel-card">
          <button class="btn-primary btn-block" @click="emit('submit', task)">提交审核</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scanning-view { display: flex; flex-direction: column; height: 100%; }
.scanning-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--color-border); }
.back-btn { display: flex; align-items: center; gap: 6px; background: none; border: none; cursor: pointer; color: var(--color-text-secondary); font-size: 14px; }
.back-btn svg { width: 18px; height: 18px; }
.scanning-title { font-size: 16px; font-weight: 600; }
.scanning-progress { font-size: 14px; color: var(--color-text-secondary); }
.progress-num { font-size: 20px; font-weight: 700; color: var(--color-primary); }
.scanning-content { display: flex; flex: 1; gap: 24px; padding: 24px; }
.scan-area { flex: 2; display: flex; flex-direction: column; gap: 24px; }
.scan-input-wrapper { display: flex; gap: 12px; }
.scan-input { flex: 1; padding: 12px 16px; border: 2px solid var(--color-border); border-radius: 8px; font-size: 16px; background: var(--color-bg); outline: none; }
.scan-input:focus { border-color: var(--color-primary); }
.scan-btn { display: flex; align-items: center; gap: 8px; padding: 12px 24px; background: var(--color-primary); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.scan-btn svg { width: 18px; height: 18px; }
.recent-checks { flex: 1; }
.recent-title { font-size: 14px; font-weight: 600; margin: 0 0 12px; }
.check-list { display: flex; flex-direction: column; gap: 8px; }
.check-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: var(--color-bg); border-radius: 8px; border-left: 3px solid var(--color-success); }
.check-item.warning { border-left-color: var(--color-warning); }
.check-icon { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: rgba(52,211,153,0.1); color: var(--color-success); }
.check-icon.warning { background: rgba(251,191,36,0.1); color: var(--color-warning); }
.check-icon svg { width: 16px; height: 16px; }
.check-info { flex: 1; display: flex; flex-direction: column; }
.check-code { font-size: 14px; font-weight: 600; }
.check-name { font-size: 12px; color: var(--color-text-secondary); }
.check-alert { font-size: 12px; color: var(--color-warning); }
.check-time { font-size: 12px; color: var(--color-text-secondary); }
.info-panel { flex: 1; display: flex; flex-direction: column; gap: 16px; max-width: 300px; }
.panel-card { background: var(--color-bg-elevated); border-radius: 12px; padding: 20px; border: 1px solid var(--color-border); }
.panel-title { font-size: 14px; font-weight: 600; margin: 0 0 16px; }
.progress-ring { position: relative; width: 120px; height: 120px; margin: 0 auto 16px; }
.progress-ring svg { width: 100%; height: 100%; }
.progress-text { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 700; color: var(--color-primary); }
.progress-details { display: flex; flex-direction: column; gap: 8px; }
.detail-row { display: flex; justify-content: space-between; font-size: 14px; }
.detail-val { font-weight: 600; }
.text-success { color: var(--color-success); }
.text-danger { color: var(--color-danger); }
.btn-primary { padding: 12px 24px; background: var(--color-primary); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; }
.btn-block { width: 100%; }
</style>

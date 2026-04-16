/* 磐盘 - 路由模块 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { TOKEN_KEY } from '@/utils/request'
import MainLayout from '@/layouts/MainLayout.vue'
import MobileLayout from '@/layouts/MobileLayout.vue'

const routes: RouteRecordRaw[] = [
  // PC端路由
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '工作台' } },
      { path: 'categories', component: () => import('@/views/Category.vue'), meta: { title: '资产类目' } },
      { path: 'assets/list', component: () => import('@/views/AssetList.vue'), meta: { title: '资产列表' } },
      { path: 'assets/purchase', component: () => import('@/views/Purchase.vue'), meta: { title: '采购入库' } },
      { path: 'assets/transfer', redirect: '/transfers/transfer' },
      { path: 'transfers/purchase', component: () => import('@/views/transfers/PurchaseList.vue'), meta: { title: '采购入库' } },
      { path: 'transfers/assign', component: () => import('@/views/transfers/AssignList.vue'), meta: { title: '领用出库' } },
      { path: 'transfers/transfer', component: () => import('@/views/transfers/TransferList.vue'), meta: { title: '调拨' } },
      { path: 'inventory', component: () => import('@/views/Inventory.vue'), meta: { title: '盘点管理' } },
      { path: 'organization', component: () => import('@/views/Organization.vue'), meta: { title: '组织架构' } },
      { path: 'reports', component: () => import('@/views/Reports.vue'), meta: { title: '报表统计' } },
      { path: 'audit', component: () => import('@/views/AuditLog.vue'), meta: { title: '审计日志' } },
    ],
  },
  // 移动端路由
  {
    path: '/mobile',
    component: MobileLayout,
    meta: { requiresAuth: true, isMobile: true },
    children: [
      { path: '', redirect: '/mobile/home' },
      { path: 'home', component: () => import('@/views/mobile/Home.vue'), meta: { title: '工作台' } },
      { path: 'assets', component: () => import('@/views/mobile/AssetSearch.vue'), meta: { title: '资产查询' } },
      { path: 'assets/:id', component: () => import('@/views/mobile/AssetDetail.vue'), meta: { title: '资产详情' } },
      { path: 'scan', component: () => import('@/views/mobile/ScanAsset.vue'), meta: { title: '扫码查询' } },
      { path: 'inventory', component: () => import('@/views/mobile/InventoryList.vue'), meta: { title: '盘点任务' } },
      { path: 'inventory/:taskId', component: () => import('@/views/MobileScan.vue'), meta: { title: '扫码盘点' } },
      { path: 'approval', component: () => import('@/views/mobile/ApprovalList.vue'), meta: { title: '审批中心' } },
      { path: 'approval/:id', component: () => import('@/views/mobile/ApprovalDetail.vue'), meta: { title: '审批详情' } },
      { path: 'notifications', component: () => import('@/views/mobile/NotificationList.vue'), meta: { title: '通知中心' } },
      { path: 'purchase', component: () => import('@/views/mobile/MobilePurchase.vue'), meta: { title: '提交入库' } },
      { path: 'submit/transfer', component: () => import('@/views/mobile/MobileTransfer.vue'), meta: { title: '提交调拨' } },
      { path: 'submit/assign', component: () => import('@/views/mobile/MobileAssign.vue'), meta: { title: '提交领用' } },
      { path: 'profile', component: () => import('@/views/mobile/Profile.vue'), meta: { title: '我的' } },
    ],
  },
  // 独立的扫码盘点页面（兼容旧路由）
  {
    path: '/mobile/scan/:taskId',
    component: () => import('@/views/MobileScan.vue'),
    meta: { title: '扫码盘点', requiresAuth: true },
  },
  {
    path: '/login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false, title: '登录' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }
  next()
})

export { routes }
export default router

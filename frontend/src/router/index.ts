/* 磐盘 - 路由模块 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { TOKEN_KEY } from '@/utils/request'
import { useUserStore } from '@/store/user'
import MainLayout from '@/layouts/MainLayout.vue'
import MobileLayout from '@/layouts/MobileLayout.vue'

declare module 'vue-router' {
  interface RouteMeta {
    permissionPage?: string
    operation?: string
    operationAny?: string[]
    operationAll?: string[]
    operationByQuery?: { query: string; present: string | string[]; absent: string | string[] }
  }
}

const landingOptions: { path: string; permissionPage?: string; operation?: string; operationAny?: string[]; operationAll?: string[] }[] = [
  { path: '/dashboard', permissionPage: 'dashboard' },
  { path: '/assets/summary', permissionPage: 'asset_ledger' },
  { path: '/fixed-assets', permissionPage: 'instances' },
  { path: '/categories', operation: 'view_categories' },
  { path: '/transfers/purchase', permissionPage: 'purchase' },
  { path: '/transfers/assign', permissionPage: 'assignment' },
  { path: '/transfers/transfer', permissionPage: 'transfer' },
  { path: '/transfers/recovery', permissionPage: 'recovery' },
  { path: '/transfers/recovery/ledger', permissionPage: 'recovery_ledger' },
  { path: '/inventory', permissionPage: 'inventory' },
  { path: '/organization', permissionPage: 'personnel' },
  { path: '/departments', operation: 'view_departments' },
  { path: '/suppliers', operation: 'view_suppliers' },
  { path: '/reports', permissionPage: 'reports' },
  { path: '/reconciliation', permissionPage: 'reconciliation' },
  { path: '/admin/permission-matrix', permissionPage: 'permission_matrix' },
  { path: '/mobile/approval', permissionPage: 'mobile_approvals' },
  { path: '/mobile/my-transfers', permissionPage: 'mobile_my_documents' },
  { path: '/mobile/notifications', permissionPage: 'mobile_notifications' },
  { path: '/categories/create', operationAll: ['view_categories', 'edit_categories'] },
  { path: '/inventory/create', operation: 'edit_inventory' },
  { path: '/transfers/purchase/create', operationAll: ['view_purchase', 'edit_purchase', 'view_categories'] },
  { path: '/transfers/assign/create', operationAll: ['view_assignment', 'edit_assignment', 'view_asset_ledger'] },
  { path: '/transfers/transfer/create', operationAll: ['view_transfer', 'edit_transfer', 'view_asset_ledger'] },
  { path: '/transfers/recovery/create', operationAll: ['view_recovery', 'edit_recovery', 'view_asset_ledger'] },
]

function firstAccessiblePath() {
  const userStore = useUserStore()
  if (userStore.isAdmin) return '/dashboard'
  return landingOptions.find(option =>
    (option.permissionPage && userStore.canAccessPage(option.permissionPage)) ||
    (option.operation && userStore.can(option.operation)) ||
    (option.operationAll?.length && option.operationAll.every(operation => userStore.can(operation))) ||
    option.operationAny?.some(operation => userStore.can(operation)),
  )?.path
}

const routes: RouteRecordRaw[] = [
  // PC端路由
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '工作台', operation: 'view_dashboard' } },
      { path: 'categories', component: () => import('@/views/Category.vue'), meta: { title: '资产类目', operation: 'view_categories' } },
      { path: 'departments', component: () => import('@/views/DepartmentManage.vue'), meta: { title: '部门字典', operation: 'view_departments' } },
      { path: 'suppliers', component: () => import('@/views/SupplierManage.vue'), meta: { title: '供应商字典', operation: 'view_suppliers' } },
      { path: 'categories/create', component: () => import('@/views/categories/CategoryCreate.vue'), meta: { title: '新增分类', operationAll: ['view_categories', 'edit_categories'] } },
      { path: 'categories/:id/edit', component: () => import('@/views/categories/CategoryCreate.vue'), meta: { title: '编辑分类', operationAll: ['view_categories', 'edit_categories'] } },
      { path: 'assets/summary', component: () => import('@/views/assets/AssetSummary.vue'), meta: { title: '资产台账', permissionPage: 'asset_ledger' } },
      { path: 'assets/list', redirect: '/assets/summary' },
      { path: 'assets/list/create', redirect: '/assets/summary' },
      { path: 'fixed-assets', component: () => import('@/views/FixedAssetList.vue'), meta: { title: '实例档案', permissionPage: 'instances' } },
      { path: 'fixed-assets/create', redirect: '/transfers/purchase' },
      { path: 'assets/purchase', redirect: '/transfers/purchase' },
      { path: 'assets/transfer', redirect: '/transfers/transfer' },
      { path: 'transfers/purchase', component: () => import('@/views/transfers/PurchaseList.vue'), meta: { title: '采购入库', permissionPage: 'purchase' } },
      { path: 'transfers/purchase/create', component: () => import('@/views/transfers/PurchaseCreate.vue'), meta: { title: '新建采购入库', operationAll: ['view_purchase', 'edit_purchase', 'view_categories'] } },
      { path: 'transfers/purchase/:id', component: () => import('@/views/transfers/PurchaseDetail.vue'), meta: { title: '采购入库详情', permissionPage: 'purchase_detail' } },
      { path: 'transfers/assign', component: () => import('@/views/transfers/AssignList.vue'), meta: { title: '领用出库', permissionPage: 'assignment' } },
      { path: 'transfers/assign/create', component: () => import('@/views/transfers/AssignCreate.vue'), meta: { title: '新建领用出库', operationAll: ['view_assignment', 'edit_assignment', 'view_asset_ledger'] } },
      { path: 'transfers/assign/:id', component: () => import('@/views/transfers/AssignDetail.vue'), meta: { title: '领用详情', permissionPage: 'assignment_detail' } },
      { path: 'transfers/transfer', component: () => import('@/views/transfers/TransferList.vue'), meta: { title: '调拨', permissionPage: 'transfer' } },
      { path: 'transfers/transfer/create', component: () => import('@/views/transfers/TransferCreate.vue'), meta: { title: '新建调拨', operationAll: ['view_transfer', 'edit_transfer', 'view_asset_ledger'] } },
      { path: 'transfers/transfer/:id', component: () => import('@/views/transfers/TransferDetail.vue'), meta: { title: '调拨详情', permissionPage: 'transfer_detail' } },
      { path: 'transfers/recovery', component: () => import('@/views/transfers/RecoveryList.vue'), meta: { title: '回收', permissionPage: 'recovery' } },
      { path: 'transfers/recovery/ledger', component: () => import('@/views/transfers/RecoveryLedger.vue'), meta: { title: '物资处置台账', permissionPage: 'recovery_ledger' } },
      { path: 'transfers/recovery/create', component: () => import('@/views/transfers/RecoveryCreate.vue'), meta: { title: '新建回收', operationAll: ['view_recovery', 'edit_recovery', 'view_asset_ledger'] } },
      { path: 'transfers/recovery/:id', component: () => import('@/views/transfers/RecoveryDetail.vue'), meta: { title: '回收详情', permissionPage: 'recovery_detail' } },
      { path: 'inventory', component: () => import('@/views/Inventory.vue'), meta: { title: '盘点管理', permissionPage: 'inventory' } },
      { path: 'inventory/create', component: () => import('@/views/inventory/InventoryTaskCreate.vue'), meta: { title: '创建盘点任务', operation: 'edit_inventory' } },
      { path: 'reconciliation', component: () => import('@/views/Reconciliation.vue'), meta: { title: '对账', permissionPage: 'reconciliation' } },
      { path: 'organization', component: () => import('@/views/Organization.vue'), meta: { title: '组织架构', permissionPage: 'personnel' } },
      { path: 'admin/permissions', component: () => import('@/views/admin/PermissionAssign.vue'), meta: { title: '权限分配', requiresAdmin: true } },
      { path: 'admin/permission-matrix', component: () => import('@/views/admin/PermissionMatrix.vue'), meta: { title: '权限矩阵', permissionPage: 'permission_matrix' } },
      { path: 'reports', component: () => import('@/views/Reports.vue'), meta: { title: '报表统计', permissionPage: 'reports' } },
      { path: 'audit', component: () => import('@/views/AuditLog.vue'), meta: { title: '审计日志', requiresAdmin: true } },
    ],
  },
  // 移动端路由
  {
    path: '/mobile',
    component: MobileLayout,
    meta: { requiresAuth: true, isMobile: true },
    children: [
      { path: '', redirect: '/mobile/scan' },
      { path: 'home', redirect: '/mobile/scan' },
      { path: 'my-assets', component: () => import('@/views/mobile/AssetSearch.vue'), meta: { title: '资产查询', permissionPage: 'mobile_assets' } },
      { path: 'assets', component: () => import('@/views/mobile/AssetSearch.vue'), meta: { title: '资产查询', permissionPage: 'mobile_assets' } },
      { path: 'assets/:id', component: () => import('@/views/mobile/AssetDetail.vue'), meta: { title: '资产详情', permissionPage: 'mobile_assets' } },
      { path: 'scan', component: () => import('@/views/mobile/ScanAsset.vue'), meta: { title: '扫码查询', permissionPage: 'mobile_scan' } },
      { path: 'inventory', component: () => import('@/views/mobile/InventoryList.vue'), meta: { title: '盘点任务', permissionPage: 'mobile_inventory' } },
      { path: 'inventory/:taskId', component: () => import('@/views/MobileScan.vue'), meta: { title: '扫码盘点', operation: 'edit_inventory' } },
      { path: 'approval', component: () => import('@/views/mobile/ApprovalList.vue'), meta: { title: '审批中心', permissionPage: 'mobile_approvals' } },
      { path: 'approval/:id', component: () => import('@/views/mobile/ApprovalDetail.vue'), meta: { title: '审批详情', permissionPage: 'mobile_approval_detail' } },
      { path: 'my-transfers', component: () => import('@/views/mobile/MyTransfers.vue'), meta: { title: '我的申请', permissionPage: 'mobile_my_documents' } },
      { path: 'notifications', component: () => import('@/views/mobile/NotificationList.vue'), meta: { title: '通知中心', permissionPage: 'mobile_notifications' } },
      { path: 'purchase', component: () => import('@/views/mobile/MobilePurchase.vue'), meta: { title: '提交入库', operationAll: ['view_purchase', 'edit_purchase', 'view_categories'] } },
      { path: 'submit/transfer', component: () => import('@/views/mobile/MobileTransfer.vue'), meta: { title: '提交调拨', operationAll: ['view_transfer', 'edit_transfer', 'view_asset_ledger'] } },
      { path: 'submit/assign', component: () => import('@/views/mobile/MobileAssign.vue'), meta: { title: '提交领用', operationAll: ['view_assignment', 'edit_assignment', 'view_asset_ledger'] } },
      { path: 'profile', component: () => import('@/views/mobile/Profile.vue'), meta: { title: '我的' } },
    ],
  },
  // 独立的扫码盘点页面（兼容旧路由）
  {
    path: '/mobile/scan/:taskId',
    component: () => import('@/views/MobileScan.vue'),
    meta: { title: '扫码盘点', requiresAuth: true, operation: 'edit_inventory' },
  },
  {
    path: '/login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false, title: '登录' },
  },
  {
    path: '/install',
    component: () => import('@/views/InstallGuide.vue'),
    meta: { requiresAuth: false, title: '安装磐盘' },
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

router.beforeEach(async (to, _from, next) => {
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }
  // 权限判定前等待用户信息就绪（frontend-interaction-integrity）：
  // 直接刷新管理类路由时 profile 尚未返回，同步判定会误弹回 dashboard。
  // 一次性等待——profileLoaded 后后续导航零开销；失败按无凭证路径走既有逻辑。
  if (to.meta.requiresAdmin || to.meta.permissionPage || to.meta.operation || to.meta.operationAny || to.meta.operationAll || to.meta.operationByQuery) {
    const userStore = useUserStore()
    if (!userStore.profileLoaded) {
      try {
        await userStore.fetchProfile()
      } catch {
        next({ path: '/login', query: { redirect: to.fullPath } })
        return
      }
    }
  }
  // 仅超级管理员可访问的路由
  if (to.meta.requiresAdmin) {
    if (!useUserStore().isAdmin) {
      const fallback = firstAccessiblePath()
      if (fallback) next({ path: fallback })
      else next(false)
      return
    }
  }
  if (to.meta.permissionPage && !useUserStore().canAccessPage(to.meta.permissionPage)) {
    const fallback = firstAccessiblePath()
    if (fallback) next({ path: fallback })
    else next(false)
    return
  }
  // 需业务操作码的路由（按钮隐藏外的 URL 直达兜底；后端 API 仍持 required_operations 二重校验）
  if (to.meta.operation) {
    if (!useUserStore().can(to.meta.operation as string)) {
      const fallback = firstAccessiblePath()
      if (fallback) next({ path: fallback })
      else next(false)
      return
    }
  }
  if (to.meta.operationAny?.length) {
    if (!to.meta.operationAny.some(operation => useUserStore().can(operation))) {
      const fallback = firstAccessiblePath()
      if (fallback) next({ path: fallback })
      else next(false)
      return
    }
  }
  if (to.meta.operationAll?.length) {
    if (!to.meta.operationAll.every(operation => useUserStore().can(operation))) {
      const fallback = firstAccessiblePath()
      if (fallback) next({ path: fallback })
      else next(false)
      return
    }
  }
  if (to.meta.operationByQuery) {
    const { query, present, absent } = to.meta.operationByQuery
    const value = to.query[query]
    const requiredOperations = value !== undefined && value !== null && value !== '' ? present : absent
    const allowed = Array.isArray(requiredOperations)
      ? requiredOperations.every(operation => useUserStore().can(operation))
      : useUserStore().can(requiredOperations)
    if (!allowed) {
      const fallback = firstAccessiblePath()
      if (fallback) next({ path: fallback })
      else next(false)
      return
    }
  }
  next()
})

export { routes }
/* 权限变更免手动刷新：路由切换时节流重拉（见 store/user.ts refreshOperationsIfStale） */
router.afterEach(() => { void useUserStore().refreshOperationsIfStale() })

export default router

# deploy-20260917-mobile-release Specification

## Purpose
将已本地验收的移动端扫码终端系列功能发布到生产（qhpanpan.top），全程数据零变更、带备份与回滚点。

## ADDED Requirements

### Requirement: 生产发布流程带备份与验收
部署 SHALL 在备份 PostgreSQL 后执行标准发布，并以线上功能验收与数据隔离核验收口。

#### Scenario: 部署前全量备份
- **WHEN** 执行部署
- **THEN** 先在生产生成 PostgreSQL 全量备份文件（/root/rock_slab_full_backup_20260917_*.sql），失败则中止部署

#### Scenario: 对账门禁通过才继续
- **WHEN** deploy.sh 运行 check_ledger_consistency
- **THEN** 退出码为 0 才继续后续步骤，非 0 立即中止并排查

#### Scenario: 部署后线上验收
- **WHEN** 部署完成
- **THEN** /install 公开可达、移动端扫码终端可用、工作台安装二维码解码为生产 /install 地址、打印标签 V3 版式正常

#### Scenario: 生产数据零混入
- **WHEN** 部署完成核验生产实例数据
- **THEN** 不存在本地测试数据（A-a00008-BJ001-3 至 -22、小熊供应商、标签扫码盘库验证任务），既有生产业务数据原样

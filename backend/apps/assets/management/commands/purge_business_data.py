"""清空业务数据（测试数据下线）：留品目字典/组织架构/用户，删全部单据与台账。

用法：
    python manage.py purge_business_data           # 预演：只统计各表行数
    python manage.py purge_business_data --apply   # 实际删除

说明：铁律 2 约束的是业务运行期的数量变动（必须走单据）；整库测试数据
下线属于一次性数据清理，按外键依赖序在单事务内删除，不构成台账漂移。
删除后品目无存量无档案，管理方式可自由切换。
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assets.models import AssetStock, FixedAsset, InstanceSequence, LedgerAdjustment
from apps.audit.models import AuditLog
from apps.inventories.models import (
    InventoryCheck, InventoryInstanceItem, InventoryItem, InventoryTask,
)
from apps.notifications.models import ApprovalCC, Notification
from apps.transfers.models import (
    DocumentSequence, Transfer, TransferLine, TransferLineInstance,
)

# 删除顺序 = 外键依赖序（引用方先删），全部为整表清空
PURGE_TARGETS = [
    ('通知', Notification),
    ('审批抄送', ApprovalCC),
    ('审计日志', AuditLog),
    ('盘点记录', InventoryCheck),
    ('实例盘项', InventoryInstanceItem),
    ('盘点项', InventoryItem),
    ('盘点任务', InventoryTask),
    ('明细行实例关联', TransferLineInstance),
    ('固定资产实例', FixedAsset),
    ('流转单明细行', TransferLine),
    ('流转单', Transfer),
    ('台账调整单', LedgerAdjustment),
    ('资产台账', AssetStock),
    ('实例编号序列', InstanceSequence),
    ('单据编号序列', DocumentSequence),
]


class Command(BaseCommand):
    help = (
        '清空业务数据（测试数据下线）：删除流转单/台账/实例/盘点/调整单/通知/审计日志，'
        '并重置单据与实例编号序列；保留品目字典、组织架构、用户与登录令牌。'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='实际执行删除（缺省仅预演统计）',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write('清空范围：单据/台账/实例/盘点/调整单/通知/审计 + 编号序列')
        self.stdout.write('保留范围：品目字典、组织架构、用户、登录令牌')
        if not apply:
            self.stdout.write(self.style.WARNING('预演模式（仅统计），加 --apply 实际删除'))

        with transaction.atomic():
            for label, model in PURGE_TARGETS:
                count = model.objects.count()
                if apply and count:
                    model.objects.all().delete()
                verb = '已删除' if apply else '现存'
                self.stdout.write(f'  {label}：{verb} {count} 行')

        if apply:
            self.stdout.write(
                self.style.SUCCESS(
                    '业务数据已清空。验收：python manage.py check_ledger_consistency'
                )
            )

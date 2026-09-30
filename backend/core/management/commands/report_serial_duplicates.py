from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = ('报告同分公司内非空序列号的重复组：分组输出分公司/内部编号/状态/使用人。'
            '存在重复时以非零退出码结束——用于存量清理验收与巡检；'
            '数据库唯一约束（阶段二）引入前必须清理至本命令零退出。'
            '跨分公司同号合法（手机自编编号体系），不计入重复')

    def handle(self, *args, **options):
        from django.db.models import Count
        from apps.assets.models import FixedAsset
        groups = (
            FixedAsset.objects.exclude(序列号='')
            .values('branch__name', '序列号')
            .annotate(n=Count('id')).filter(n__gt=1)
            .order_by('序列号')
        )
        total = 0
        for g in groups:
            self.stdout.write(f"[{g['n']} 台] {g['branch__name'] or '-'} | 序列号 {g['序列号']}")
            for inst in (
                FixedAsset.objects.filter(序列号=g['序列号'], branch__name=g['branch__name'])
                .select_related('branch', 'item')
                .order_by('内部编号')
            ):
                total += 1
                self.stdout.write(
                    f"    {inst.branch.name if inst.branch else '-'} | "
                    f"{inst.内部编号} | {inst.当前状态} | 使用人={inst.使用人 or '-'}"
                )
        if groups.exists():
            self.stdout.write(self.style.WARNING(
                f'共 {groups.count()} 组 / {total} 台实例存在同分公司重复序列号'
                '——须清理后才可引入数据库唯一约束'))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS('无同分公司重复序列号（可引入数据库唯一约束）'))

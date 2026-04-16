from django.core.management.base import BaseCommand
from apps.users.models import User
from apps.organizations.models import Region, Branch
from apps.categories.models import Category


class Command(BaseCommand):
    help = 'Seed database with sample data'

    def handle(self, *args, **options):
        regions_data = [
            ('HD', '华东区域'),
            ('HN', '华南区域'),
        ]
        regions = {}
        for code, name in regions_data:
            regions[code], _ = Region.objects.get_or_create(
                code=code, defaults={'name': name, 'status': 'active'}
            )

        branches_data = [
            ('SH001', '上海分公司', 'HD', '上海市浦东新区', '021-12345678'),
            ('HZ001', '杭州分公司', 'HD', '杭州市西湖区', '0571-12345678'),
            ('GZ001', '广州分公司', 'HN', '广州市天河区', '020-12345678'),
        ]
        for code, name, region_code, address, phone in branches_data:
            Branch.objects.get_or_create(
                code=code,
                defaults={
                    'name': name, 'region': regions[region_code],
                    'address': address, 'phone': phone,
                }
            )

        users_data = [
            ('13800000001', '行政经理', 'manager', None, None),
            ('13800000002', '华东主管', 'supervisor', None, regions['HD'].pk),
            ('13800000003', '上海组长', 'leader', Branch.objects.get(code='SH001').pk, None),
            ('13800000004', '上海专员', 'staff', Branch.objects.get(code='SH001').pk, None),
            ('13800000005', '杭州专员', 'staff', Branch.objects.get(code='HZ001').pk, None),
        ]
        for phone, name, role, branch_id, region_id in users_data:
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'name': name, 'role': role,
                    'branch_id': branch_id, 'region_id': region_id,
                }
            )
            if created:
                user.set_password('123456')
                user.save()

        categories_data = [
            ('固定资产类', '办公设备', '办公桌', 'A-a00001', '张'),
            ('固定资产类', '电子设备', '笔记本电脑', 'A-b00001', '台'),
            ('固定资产类', '家具设施', '办公椅', 'A-c00001', '把'),
            ('低值易耗品类', '办公耗材', 'A4打印纸', 'B-a00001', '包'),
            ('低值易耗品类', '清洁用品', '垃圾袋', 'B-b00001', '卷'),
            ('无形资产类', '软件与数据', 'Office 365', 'C-a00001', '套'),
        ]
        for cat, item, name, code, unit in categories_data:
            Category.objects.get_or_create(
                asset_code=code,
                defaults={
                    'asset_category': cat, 'item_category': item,
                    'asset_name': name, 'unit': unit,
                }
            )

        self.stdout.write(self.style.SUCCESS('Seed data created successfully'))

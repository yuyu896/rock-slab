from rest_framework import serializers
from apps.categories.models import Category
from .models import AssetStock, FixedAsset, LedgerAdjustment


class AssetStockSerializer(serializers.ModelSerializer):
    """台账行输出：品目信息联字典，数量维度为三存储列 + 计算总量/充足（只读）。"""

    branch_name = serializers.CharField(source='branch.name', read_only=True)
    资产编号 = serializers.CharField(source='item.asset_code', read_only=True)
    资产名称 = serializers.CharField(source='item.asset_name', read_only=True)
    规格 = serializers.CharField(source='item.specification', read_only=True)
    资产类目 = serializers.CharField(source='item.asset_category', read_only=True)
    物品分类 = serializers.CharField(source='item.item_category', read_only=True)
    计量单位 = serializers.CharField(source='item.unit', read_only=True)
    管理方式 = serializers.ChoiceField(
        source='item.management_type',
        choices=Category.MANAGEMENT_CHOICES,
        read_only=True,
    )
    总量 = serializers.IntegerField(read_only=True)
    生效警戒线 = serializers.IntegerField(read_only=True, allow_null=True)
    是否充足 = serializers.BooleanField(read_only=True)

    class Meta:
        model = AssetStock
        fields = [
            'id', 'branch', 'branch_name', 'item',
            '资产编号', '资产名称', '规格', '资产类目', '物品分类', '计量单位', '管理方式',
            '在库数量', '在用数量', '回收库数量', '总量',
            '警戒线', '生效警戒线', '是否充足',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class LedgerAdjustmentSerializer(serializers.ModelSerializer):
    """调整单输出；创建由 view 调 ledger service（唯一写入口）执行。"""

    branch_name = serializers.CharField(source='branch.name', read_only=True)
    资产编号 = serializers.CharField(source='item.asset_code', read_only=True)
    资产名称 = serializers.CharField(source='item.asset_name', read_only=True)
    经办人姓名 = serializers.CharField(source='经办人.name', read_only=True, default=None)
    来源任务 = serializers.CharField(source='source_task.name', read_only=True, default=None)

    class Meta:
        model = LedgerAdjustment
        fields = [
            'id', '单据编号', 'branch', 'branch_name', 'item', '资产编号', '资产名称',
            '目标列', '变动量', '事由', '经办人', '经办人姓名', 'is_initial',
            'source_task', '来源任务', 'created_at',
        ]
        read_only_fields = fields


class FixedAssetSerializer(serializers.ModelSerializer):
    """实例档案输出：品目信息联字典、供应商/单价/采购日期经出生明细行派生（决策 #8）。"""

    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    item = serializers.PrimaryKeyRelatedField(read_only=True)
    item_code = serializers.CharField(source='item.asset_code', read_only=True)
    item_name = serializers.CharField(source='item.asset_name', read_only=True)
    item_spec = serializers.CharField(source='item.specification', read_only=True, default='')
    asset_category = serializers.CharField(source='item.asset_category', read_only=True, default='')
    item_category = serializers.CharField(source='item.item_category', read_only=True, default='')
    management_type = serializers.ChoiceField(
        source='item.management_type',
        choices=Category.MANAGEMENT_CHOICES,
        read_only=True,
    )
    待补录 = serializers.SerializerMethodField()
    供应商 = serializers.SerializerMethodField()
    单价 = serializers.SerializerMethodField()
    采购日期 = serializers.SerializerMethodField()

    class Meta:
        model = FixedAsset
        fields = [
            'id', '内部编号', '序列号', '待补录', '当前状态',
            '使用人', 'department', 'department_name', 'branch', 'branch_name',
            'item', 'item_code', 'item_name', 'item_spec',
            'asset_category', 'item_category', 'management_type',
            '入库日期', '供应商', '单价', '采购日期',
            '备注', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_待补录(self, obj):
        return not (obj.序列号 or '').strip()

    def get_供应商(self, obj):
        if obj.birth_line is None:
            return ''
        return obj.birth_line.transfer.供应商 or ''

    def get_单价(self, obj):
        if obj.birth_line is None:
            return None
        return obj.birth_line.单价

    def get_采购日期(self, obj):
        if obj.birth_line is None:
            return None
        return obj.birth_line.transfer.调拨日期


class FixedAssetSupplementSerializer(serializers.Serializer):
    """序列号补录入参：仅 序列号/备注 两字段（状态等经流转单变动）。"""

    序列号 = serializers.CharField(required=False, allow_blank=True, default='')
    备注 = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        unknown = set(self.initial_data) - {'序列号', '备注'}
        if unknown:
            raise serializers.ValidationError(
                {'detail': f'补录仅支持 序列号/备注，多余字段：{"、".join(sorted(unknown))}'}
            )
        return attrs

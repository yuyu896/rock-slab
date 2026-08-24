from rest_framework import serializers
from apps.categories.models import Category
from .models import Asset, AssetStock, FixedAsset, LedgerAdjustment


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

    class Meta:
        model = LedgerAdjustment
        fields = [
            'id', 'branch', 'branch_name', 'item', '资产编号', '资产名称',
            '目标列', '变动量', '事由', '经办人', '经办人姓名', 'is_initial',
            'created_at',
        ]
        read_only_fields = fields


class AssetSerializer(serializers.ModelSerializer):
    """Serializer for Asset model with Chinese field names used directly."""
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)

    class Meta:
        model = Asset
        fields = [
            'id',
            '序号', '分公司', '分公司编号', '资产编号',
            '资产类目', '物品分类', '资产名称', '规格',
            '供应商', '图片', '入库日期', '是否租用',
            '数量', '单价', '购入金额', '出库日期',
            '所属部门', '使用人', '当前状态', '警戒线',
            '是否充足', '电脑序列号', '备注',
            'branch', 'branch_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', '分公司', '分公司编号']
        extra_kwargs = {
            # 序号由后端在 create() 中自增，前端新增无需提交
            '序号': {'required': False},
        }

    def validate(self, attrs):
        """资产编号必须已在资产分类（Category）登记，否则拒绝创建/修改。"""
        code = attrs.get('资产编号')
        if code is not None:
            from apps.categories.models import Category
            if not Category.objects.filter(asset_code=code).exists():
                raise serializers.ValidationError(
                    {'资产编号': ['该资产编号未在资产分类登记，请先在资产分类中添加']}
                )
        return attrs

    def create(self, validated_data):
        # 序号未提交时取当前最大序号 + 1（空表取 1）
        if validated_data.get('序号') is None:
            last = Asset.objects.order_by('-序号').first()
            validated_data['序号'] = (last.序号 + 1) if last else 1
        # 按提交的分公司名称解析 branch 并回填冗余字段
        # （分公司/分公司编号 为 read_only，名称从 initial_data 读取）
        branch = validated_data.get('branch')
        if branch is None:
            company = self.initial_data.get('分公司')
            if company:
                from apps.organizations.models import Branch
                branch = Branch.objects.filter(name=company).first()
                if branch:
                    validated_data['branch'] = branch
        if branch is not None:
            validated_data['分公司'] = branch.name
            validated_data['分公司编号'] = branch.code
        return super().create(validated_data)

    def update(self, instance, validated_data):
        branch = validated_data.get('branch')
        if branch is not None:
            validated_data['分公司'] = branch.name
            validated_data['分公司编号'] = branch.code
        return super().update(instance, validated_data)


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

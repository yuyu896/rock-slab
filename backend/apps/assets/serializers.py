from rest_framework import serializers
from .models import Asset, FixedAsset


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
    """Serializer for FixedAsset instances."""
    # 前端新增只传资产编号，asset 由 validate() 按编号反查补全，故非必填
    asset = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects.all(), required=False, allow_null=True,
    )
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)
    asset_name = serializers.CharField(source='asset.资产名称', read_only=True, default='')
    序号 = serializers.IntegerField(source='asset.序号', read_only=True, default=None)
    资产类目 = serializers.CharField(source='asset.资产类目', read_only=True, default='')
    物品分类 = serializers.CharField(source='asset.物品分类', read_only=True, default='')
    是否租用 = serializers.BooleanField(source='asset.是否租用', read_only=True, default=False)
    数量 = serializers.IntegerField(source='asset.数量', read_only=True, default=None)
    规格 = serializers.CharField(source='asset.规格', read_only=True, default='')
    单价 = serializers.DecimalField(source='asset.单价', max_digits=12, decimal_places=2, read_only=True, default=None)
    购入金额 = serializers.DecimalField(source='asset.购入金额', max_digits=14, decimal_places=2, read_only=True, default=None)
    出库日期 = serializers.DateField(source='asset.出库日期', read_only=True, default=None)

    class Meta:
        model = FixedAsset
        fields = [
            'id', 'asset', '内部编号', '资产编号', '资产名称', 'asset_name',
            '序列号', '供应商', '使用人', '所属部门', '当前状态',
            '分公司', '分公司编号', 'branch', 'branch_name',
            '入库日期', '备注', 'created_at', 'updated_at',
            '序号', '资产类目', '物品分类', '是否租用', '数量',
            '规格', '单价', '购入金额', '出库日期',
        ]
        read_only_fields = ['created_at', 'updated_at', '内部编号', '资产名称']

    def validate(self, attrs):
        """未提交 asset 时，按资产编号反查父级品目；查不到则拒绝录入。"""
        if not attrs.get('asset'):
            code = attrs.get('资产编号')
            if code:
                asset = Asset.objects.filter(资产编号=code).first()
                if asset:
                    attrs['asset'] = asset
                else:
                    raise serializers.ValidationError(
                        {'资产编号': ['资产编号不存在']}
                    )
        return attrs

    def create(self, validated_data):
        validated_data['内部编号'] = FixedAsset.generate_internal_code(
            validated_data['资产编号']
        )
        asset = validated_data.get('asset')
        # 前端新增只传资产编号，按编号解析关联品目 FK
        if not asset and validated_data.get('资产编号'):
            asset = Asset.objects.filter(资产编号=validated_data['资产编号']).first()
            if asset:
                validated_data['asset'] = asset
        if asset:
            validated_data['资产名称'] = asset.资产名称
            if not validated_data.get('分公司'):
                validated_data['分公司'] = asset.分公司
            if not validated_data.get('分公司编号'):
                validated_data['分公司编号'] = asset.分公司编号
            if not validated_data.get('branch'):
                validated_data['branch'] = asset.branch
        return super().create(validated_data)

    def update(self, instance, validated_data):
        branch = validated_data.get('branch')
        if branch is not None:
            validated_data['分公司'] = branch.name
            validated_data['分公司编号'] = branch.code
        return super().update(instance, validated_data)

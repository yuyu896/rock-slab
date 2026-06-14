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

    def update(self, instance, validated_data):
        branch = validated_data.get('branch')
        if branch is not None:
            validated_data['分公司'] = branch.name
            validated_data['分公司编号'] = branch.code
        return super().update(instance, validated_data)


class FixedAssetSerializer(serializers.ModelSerializer):
    """Serializer for FixedAsset instances."""
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

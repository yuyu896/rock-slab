from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    """Serializer that maps English model fields to Chinese JSON field names.

    Accepts both English field names (from frontend) and Chinese field names.
    Always outputs Chinese field names for consistency.
    """

    # 输出字段（中文名）
    资产类目 = serializers.CharField(source='asset_category', read_only=True)
    物品分类 = serializers.CharField(source='item_category', read_only=True)
    资产名称 = serializers.CharField(source='asset_name', read_only=True)
    资产编号 = serializers.CharField(source='asset_code', read_only=True)
    规格 = serializers.CharField(source='specification', read_only=True)
    管理方式 = serializers.ChoiceField(source='management_type', choices=Category.MANAGEMENT_CHOICES, read_only=True)
    图片 = serializers.ImageField(source='image', read_only=True)
    是否租用 = serializers.BooleanField(source='is_rental', read_only=True)
    默认供应商 = serializers.CharField(source='default_supplier', read_only=True)
    计量单位 = serializers.CharField(source='unit', read_only=True)
    警戒线 = serializers.IntegerField(source='warning_line', read_only=True, allow_null=True)
    备注 = serializers.CharField(source='remarks', read_only=True)
    属性模板 = serializers.JSONField(source='attribute_template', read_only=True)

    class Meta:
        model = Category
        fields = [
            'id',
            # 写入字段（英文名）
            'asset_category', 'item_category', 'asset_name', 'asset_code', 'unit',
            'specification', 'management_type', 'image', 'is_rental', 'default_supplier',
            'warning_line', 'remarks', 'attribute_template',
            # 输出字段（中文名）
            '资产类目', '物品分类', '资产名称', '资产编号',
            '规格', '管理方式', '图片', '是否租用', '默认供应商',
            '计量单位', '警戒线', '备注', '属性模板',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'asset_category': {'write_only': True},
            'item_category': {'write_only': True},
            'asset_name': {'write_only': True},
            'asset_code': {'write_only': True},
            'unit': {'write_only': True},
            'specification': {'write_only': True, 'required': False, 'allow_blank': True},
            'management_type': {'write_only': True, 'required': False},
            'image': {'write_only': True, 'required': False, 'allow_null': True},
            'is_rental': {'write_only': True, 'required': False},
            'default_supplier': {'write_only': True, 'required': False, 'allow_blank': True},
            'warning_line': {'write_only': True, 'required': False, 'allow_null': True},
            'remarks': {'write_only': True, 'required': False},
            'attribute_template': {'write_only': True, 'required': False},
        }

    def validate_asset_code(self, value):
        """验证资产编号唯一性"""
        instance = self.instance
        queryset = Category.objects.filter(asset_code=value)
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('资产编号已存在，请使用其他编号')
        return value

    def validate_management_type(self, value):
        """管理方式缺省为数量管理"""
        return value or Category.MANAGEMENT_QUANTITY

    def validate_attribute_template(self, value):
        """验证属性模板格式"""
        if value is None:
            return {}
        if isinstance(value, (list, dict)):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and ('name' not in item or 'type' not in item):
                        raise serializers.ValidationError('每个属性必须包含 name 和 type 字段')
            return value
        raise serializers.ValidationError('属性模板必须是数组或对象格式')

    def create(self, validated_data):
        """创建时验证资产编号"""
        asset_code = validated_data.get('asset_code')
        if asset_code and Category.objects.filter(asset_code=asset_code).exists():
            raise serializers.ValidationError({'asset_code': ['资产编号已存在，请使用其他编号']})
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新时验证资产编号"""
        asset_code = validated_data.get('asset_code', instance.asset_code)
        if Category.objects.filter(asset_code=asset_code).exclude(pk=instance.pk).exists():
            raise serializers.ValidationError({'asset_code': ['资产编号已存在，请使用其他编号']})
        return super().update(instance, validated_data)

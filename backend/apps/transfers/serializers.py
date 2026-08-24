from rest_framework import serializers
from .models import Transfer, TransferLine
from apps.assets.models import FixedAsset
from apps.categories.models import Category
from apps.organizations.models import Branch, Department


class TransferLineSerializer(serializers.ModelSerializer):
    """明细行输出：品目信息联字典回显，前端无需二次查询。"""

    item_code = serializers.CharField(source='item.asset_code', read_only=True)
    item_name = serializers.CharField(source='item.asset_name', read_only=True)
    item_spec = serializers.CharField(source='item.specification', read_only=True)
    unit = serializers.CharField(source='item.unit', read_only=True)
    asset_category = serializers.CharField(source='item.asset_category', read_only=True)
    item_category = serializers.CharField(source='item.item_category', read_only=True)
    management_type = serializers.CharField(source='item.management_type', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, default='')
    instances = serializers.SerializerMethodField()

    class Meta:
        model = TransferLine
        fields = [
            'id', '行号', 'item', 'item_code', 'item_name', 'item_spec', 'unit',
            'asset_category', 'item_category', 'management_type',
            '数量', '本批规格', '单价', '金额', '使用人',
            'department', 'department_name', '存放位置', 'instances',
        ]
        read_only_fields = ['id', '行号']

    def get_instances(self, obj):
        return [
            {'id': inst.pk, 'code': inst.内部编号}
            for inst in obj.instances.all()
        ]


class TransferSerializer(serializers.ModelSerializer):
    """单头 + 嵌套明细行（读）。"""

    from_branch_name = serializers.CharField(source='from_branch.name', read_only=True, default=None)
    to_branch_name = serializers.CharField(source='to_branch.name', read_only=True, default=None)
    lines = TransferLineSerializer(many=True, read_only=True)
    品项数 = serializers.SerializerMethodField()
    总数量 = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = [
            'id', '单据编号',
            '调拨日期', '调出分公司', '调出部门', '调入分公司', '调入部门',
            '调拨原因', '调出负责人', '调入负责人', '备注', '审批状态', '审批人',
            '审批时间', '创建人', 'action_type',
            '供应商', '需求部门', '采购经办人', '用途',
            '回收分类', '回收去向', '处置方式', '处置金额', '出库日期', '领用来源',
            'from_branch', 'to_branch', 'from_branch_name', 'to_branch_name',
            'lines', '品项数', '总数量',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', '单据编号']

    def get_品项数(self, obj):
        return obj.lines.count()

    def get_总数量(self, obj):
        return sum(line.数量 for line in obj.lines.all())


class TransferLineInputSerializer(serializers.Serializer):
    """明细行输入：品目一律字典 FK 引用（uuid），禁手抄编号；实例引用见 instances。"""

    item = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    数量 = serializers.IntegerField(min_value=1)
    本批规格 = serializers.CharField(required=False, default='', allow_blank=True)
    单价 = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True,
    )
    金额 = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True,
    )
    使用人 = serializers.CharField(required=False, default='', allow_blank=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True,
    )
    存放位置 = serializers.CharField(required=False, default='', allow_blank=True)
    instances = serializers.PrimaryKeyRelatedField(
        queryset=FixedAsset.objects.all(), many=True, required=False, default=[],
    )


class TransferActionSerializer(serializers.Serializer):
    """单据创建/编辑入参：单头字段 + items 明细行数组。"""

    def __init__(self, *args, for_update=False, **kwargs):
        self.for_update = for_update
        super().__init__(*args, **kwargs)

    调拨日期 = serializers.DateField()
    items = TransferLineInputSerializer(many=True)
    调拨原因 = serializers.CharField(required=False, default='', allow_blank=True)
    调出分公司 = serializers.CharField(required=False, default='', allow_blank=True)
    调出部门 = serializers.CharField(required=False, default='', allow_blank=True)
    调入分公司 = serializers.CharField(required=False, default='', allow_blank=True)
    调入部门 = serializers.CharField(required=False, default='', allow_blank=True)
    调出负责人 = serializers.CharField(required=False, default='', allow_blank=True)
    调入负责人 = serializers.CharField(required=False, default='', allow_blank=True)
    备注 = serializers.CharField(required=False, default='', allow_blank=True)
    创建人 = serializers.CharField(required=False, default='', allow_blank=True)
    # Purchase fields
    供应商 = serializers.CharField(required=False, default='', allow_blank=True)
    需求部门 = serializers.CharField(required=False, default='', allow_blank=True)
    采购经办人 = serializers.CharField(required=False, default='', allow_blank=True)
    用途 = serializers.CharField(required=False, default='', allow_blank=True)
    # Recovery fields
    回收分类 = serializers.CharField(required=False, default='', allow_blank=True)
    回收去向 = serializers.ChoiceField(choices=['recycle_bin', 'dispose'], required=False, default='recycle_bin')
    领用来源 = serializers.ChoiceField(choices=['stock', 'recycle_bin'], required=False, default='stock')
    处置方式 = serializers.ChoiceField(choices=['', '出售', '报废', '捐赠'], required=False, default='', allow_blank=True)
    处置金额 = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True,
    )
    出库日期 = serializers.DateField(required=False, allow_null=True)
    # FK fields
    from_branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all(), required=False, allow_null=True)
    to_branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all(), required=False, allow_null=True)

    def validate(self, attrs):
        # 编辑（partial）：items 可缺省=保留原明细行；分公司维度沿单据现状，逐字段校验即可
        if self.for_update:
            if 'items' in attrs and not attrs['items']:
                raise serializers.ValidationError({'items': ['至少需要一条明细行']})
            return attrs
        if not attrs.get('items'):
            raise serializers.ValidationError({'items': ['至少需要一条明细行']})
        # 分公司必填：调出/调入至少一个非空（文字或外键均可）
        has_text = str(attrs.get('调出分公司', '')).strip() or str(attrs.get('调入分公司', '')).strip()
        has_fk = attrs.get('from_branch') or attrs.get('to_branch')
        if not has_text and not has_fk:
            raise serializers.ValidationError({'调出分公司': ['请填写分公司']})
        return attrs


class ApproveSerializer(serializers.Serializer):
    """Serializer for the approve action."""

    approved = serializers.BooleanField()
    reason = serializers.CharField(required=False, default='')

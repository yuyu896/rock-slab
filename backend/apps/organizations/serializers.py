from rest_framework import serializers
from django.core.validators import RegexValidator
from .models import Region, Branch, Team, BRANCH_CODE_REGEX


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = [
            'id', 'name', 'code', 'manager', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'code', 'region', 'address',
            'manager', 'phone', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'code': {'validators': []},
        }

    def validate_code(self, value):
        value = value.strip().upper()
        validator = RegexValidator(
            regex=BRANCH_CODE_REGEX,
            message='编号格式为2-4位大写字母(城市缩写)+3位数字，如 SH001',
        )
        validator(value)
        return value


class TeamSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)
    leader_name = serializers.CharField(source='leader.name', read_only=True, default=None)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            'id', 'name', 'region', 'region_name',
            'leader', 'leader_name', 'member_count',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.members.count()

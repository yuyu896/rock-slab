from rest_framework import serializers
from .models import Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', '联系人', '电话', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_name(self, value):
        qs = Supplier.objects.filter(name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f'已存在供应商「{value}」')
        return value

from rest_framework import serializers


class ReportOverviewSerializer(serializers.Serializer):
    totalAssets = serializers.IntegerField()
    totalValue = serializers.DecimalField(max_digits=14, decimal_places=2)
    activeRate = serializers.FloatField()
    growthRate = serializers.FloatField()


class BranchStatSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.IntegerField()
    percentage = serializers.FloatField()


class StatusStatSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class TransferReportItemSerializer(serializers.Serializer):
    """Single transfer record in the transfers report."""
    id = serializers.CharField()
    date = serializers.CharField()
    assetCode = serializers.CharField()
    assetName = serializers.CharField()
    fromBranch = serializers.CharField()
    toBranch = serializers.CharField()
    quantity = serializers.IntegerField()
    status = serializers.CharField()
    actionType = serializers.CharField()

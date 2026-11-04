from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.db.models import ProtectedError
from apps.permissions.permissions import OperationPermission
from apps.permissions.scope import resolve_user_scope
from core.permissions import IsAdmin
from apps.audit.utils import create_audit_log
from apps.permissions.models import ManagementScope, OperationGrant
from apps.users.models import User
from .models import Region, Branch, Team, Company
from .serializers import (
    RegionSerializer, RegionWriteOptionSerializer,
    BranchSerializer, BranchOptionSerializer, BranchTreeOptionSerializer,
    BranchEditOptionSerializer, TeamSerializer, TeamWriteOptionSerializer,
    CompanySerializer,
)
from .filters import RegionFilterSet, BranchFilterSet


_WRITE_ACTIONS = {'create', 'update', 'partial_update', 'destroy'}


def _scope_for(user):
    return resolve_user_scope(user)


def _can_manage_region(user, region_id):
    scope = _scope_for(user)
    return scope.all or region_id in scope.regions


def _can_manage_team_parent(user, team):
    scope = _scope_for(user)
    return scope.all or team.id in scope.teams or team.region_id in scope.regions


def _scoped_region_queryset(user, *, write=False):
    queryset = Region.objects.select_related('manager').all()
    scope = _scope_for(user)
    if scope.all:
        return queryset

    visible = Q(pk__in=scope.regions)
    if not write:
        visible |= Q(teams__pk__in=scope.teams)
        visible |= Q(teams__branches__pk__in=scope.branches)
    return queryset.filter(visible).distinct()


def _scoped_team_queryset(user, *, write=False):
    queryset = Team.objects.select_related('region', 'leader').all()
    scope = _scope_for(user)
    if scope.all:
        return queryset

    visible = Q(pk__in=scope.teams) | Q(region_id__in=scope.regions)
    if not write:
        visible |= Q(branches__pk__in=scope.branches)
    return queryset.filter(visible).distinct()


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.select_related('manager').all()
    serializer_class = RegionSerializer
    filterset_class = RegionFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = None
    # Organization visibility and maintenance are separately granted.
    required_operations = {
        'list': 'view_organizations',
        'retrieve': 'view_organizations',
        'create': ('view_organizations', 'edit_organizations'),
        'update': ('view_organizations', 'edit_organizations'),
        'partial_update': ('view_organizations', 'edit_organizations'),
        'destroy': ('view_organizations', 'delete_organizations'),
    }

    def get_required_operations_any(self, request):
        if self.action == 'list' and request.query_params.get('scope') == 'tree':
            return ('view_organizations',)
        return None

    def get_serializer_class(self):
        if self.action == 'list' and self.request.query_params.get('scope') == 'tree':
            return RegionWriteOptionSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return _scoped_region_queryset(
            self.request.user,
            write=self.action in _WRITE_ACTIONS,
        )

    def perform_create(self, serializer):
        if not _scope_for(self.request.user).all:
            raise PermissionDenied('只有全组织数据范围可以新增区域')
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
        except ProtectedError:
            return Response(
                {'detail': '该区域下存在关联数据，无法删除。请先处理关联分公司。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.select_related('team', 'team__region', 'manager').all()
    serializer_class = BranchSerializer
    filterset_class = BranchFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = None
    required_operations = {
        'list': 'view_organizations',
        'retrieve': 'view_organizations',
        'create': ('view_organizations', 'edit_organizations'),
        'update': ('view_organizations', 'edit_organizations'),
        'partial_update': ('view_organizations', 'edit_organizations'),
        'destroy': ('view_organizations', 'delete_organizations'),
    }

    _WRITE_OPTION_OPERATIONS = (
        'edit_purchase',
        'edit_assignment',
        'edit_transfer',
        'edit_recovery',
        'edit_inventory',
    )

    def get_required_operations_any(self, request):
        if self.action == 'list':
            if request.query_params.get('scope') == 'write':
                if request.user.can('view_users') and request.user.can('edit_users'):
                    return ('view_users',)
                return self._WRITE_OPTION_OPERATIONS
            if request.query_params.get('scope') == 'tree':
                return ('view_organizations',)
        return None

    def get_serializer_class(self):
        if self.action == 'list':
            scope = self.request.query_params.get('scope')
            if scope == 'write':
                return BranchOptionSerializer
            if scope == 'tree':
                if self.request.user.can('edit_organizations'):
                    return BranchEditOptionSerializer
                return BranchTreeOptionSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        qs = super().get_queryset()
        scope = _scope_for(self.request.user)
        if not scope.all:
            qs = qs.filter(id__in=scope.branches)
        return qs

    def perform_create(self, serializer):
        team = serializer.validated_data['team']
        if not _can_manage_team_parent(self.request.user, team):
            raise PermissionDenied('数据范围不包含目标行政组')
        serializer.save()

    def perform_update(self, serializer):
        team = serializer.validated_data.get('team')
        current_team_id = serializer.instance.team_id
        if team is not None and team.id != current_team_id and not _can_manage_team_parent(self.request.user, team):
            raise PermissionDenied('数据范围不包含目标行政组')
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            with transaction.atomic():
                branch = Branch.objects.select_for_update().get(pk=instance.pk)
                employees = list(
                    User.objects.select_for_update().filter(branch=branch).order_by('pk')
                )
                before_by_user = {}
                for employee in employees:
                    before_by_user[employee.pk] = {
                        'branch': {'id': str(branch.pk), 'name': branch.name},
                        'operations': sorted(employee.operation_grants.values_list('code', flat=True)),
                        'scopes': [
                            {
                                'all': scope.is_all_data,
                                'region': str(scope.region_id) if scope.region_id else None,
                                'branch': str(scope.branch_id) if scope.branch_id else None,
                                'team': str(scope.team_id) if scope.team_id else None,
                            }
                            for scope in employee.management_scopes.all()
                        ],
                    }

                branch.delete()
                employee_ids = [employee.pk for employee in employees]
                OperationGrant.objects.filter(user_id__in=employee_ids).delete()
                ManagementScope.objects.filter(user_id__in=employee_ids).delete()
                for employee in employees:
                    employee._mgmt_scope_cache = None
                    create_audit_log(
                        request,
                        action='update',
                        resource_type='user_authorization',
                        resource_id=employee.pk,
                        resource_name=employee.name,
                        description='所属分公司删除，员工归属已清除并重置业务权限和自定义数据范围',
                        before_data=before_by_user[employee.pk],
                        after_data={'branch': None, 'operations': [], 'scopes': []},
                    )
        except ProtectedError:
            return Response(
                {'detail': '该分公司下存在关联资产，无法删除。请先将资产转移至其他分公司。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related('region', 'leader').all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = None
    filterset_fields = ['region']
    required_operations = {
        'list': 'view_organizations',
        'retrieve': 'view_organizations',
        'create': ('view_organizations', 'edit_organizations'),
        'update': ('view_organizations', 'edit_organizations'),
        'partial_update': ('view_organizations', 'edit_organizations'),
        'destroy': ('view_organizations', 'delete_organizations'),
    }

    def get_required_operations_any(self, request):
        if self.action == 'list' and request.query_params.get('scope') == 'tree':
            return ('view_organizations',)
        return None

    def get_serializer_class(self):
        if self.action == 'list' and self.request.query_params.get('scope') == 'tree':
            return TeamWriteOptionSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return _scoped_team_queryset(
            self.request.user,
            write=self.action in _WRITE_ACTIONS,
        )

    def perform_create(self, serializer):
        region = serializer.validated_data['region']
        if not _can_manage_region(self.request.user, region.id):
            raise PermissionDenied('数据范围不包含目标区域')
        serializer.save()

    def perform_update(self, serializer):
        region = serializer.validated_data.get('region')
        current_region_id = serializer.instance.region_id
        if region is not None and region.id != current_region_id and not _can_manage_region(self.request.user, region.id):
            raise PermissionDenied('数据范围不包含目标区域')
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
        except ProtectedError:
            return Response(
                {'detail': '该行政组下存在分公司，无法删除。请先转移旗下分公司。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompanyView(APIView):
    """集团（单例）：查看和维护受组织架构权限控制。"""
    permission_classes = [IsAuthenticated, OperationPermission]

    def get_required_operations(self, request):
        if request.method == 'PATCH' or (
            request.method == 'GET' and request.query_params.get('scope') == 'write'
        ):
            return ('view_organizations', 'edit_organizations')
        if request.method == 'GET' and request.query_params.get('scope') == 'tree':
            return None
        return ('view_organizations',)

    def get_required_operations_any(self, request):
        if request.method == 'GET':
            if request.query_params.get('scope') == 'tree':
                return ('view_organizations',)
        return None

    def get(self, request):
        company = Company.get_singleton()
        if request.query_params.get('scope') in {'write', 'tree'}:
            scope = _scope_for(request.user)
            return Response({
                'id': str(company.id),
                'name': company.name,
                'can_create_region': scope.all,
            })
        return Response(CompanySerializer(company).data)

    def patch(self, request):
        if not _scope_for(request.user).all:
            raise PermissionDenied('修改集团名称需要全组织数据范围')
        company = Company.get_singleton()
        serializer = CompanySerializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CompanyWechatQrView(APIView):
    """集团联系二维码：登录员工可查看，只有系统管理员可替换。"""
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        from core.upload_validation import UploadValidationError, validate_image_upload

        upload = request.FILES.get('wechat_qr_code')
        if upload is None:
            return Response({'detail': '请上传微信二维码图片'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_image_upload(upload)
        except UploadValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        company = Company.get_singleton()
        old_name = company.wechat_qr_code.name if company.wechat_qr_code else None
        storage = company.wechat_qr_code.storage
        upload.name = {
            'image/jpeg': 'wechat.jpg',
            'image/png': 'wechat.png',
            'image/webp': 'wechat.webp',
        }[upload.content_type]
        company.wechat_qr_code = upload
        company.save(update_fields=['wechat_qr_code', 'updated_at'])
        if old_name and old_name != company.wechat_qr_code.name:
            storage.delete(old_name)
        return Response(CompanySerializer(company).data)

from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.utils import create_audit_log
from apps.organizations.models import Branch, Region, Team
from apps.permissions.permissions import OperationPermission
from apps.users.models import User

from .models import ManagementScope, OperationGrant
from .operations import (
    LEGACY_OPERATIONS,
    OPERATION_CATALOG,
    OPERATION_PREREQUISITES,
    PAGE_ACCESS_OPERATIONS,
    missing_operation_prerequisites,
)
from .serializers import ManagementScopeSerializer, OperationGrantSerializer


class IsAdmin(OperationPermission):
    """Only system administrators may change account authorizations."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == 'admin')


class ManagementScopeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only compatibility endpoint; writes use the atomic authorization API."""

    queryset = ManagementScope.objects.select_related('user', 'region', 'branch', 'team').all()
    serializer_class = ManagementScopeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = None
    filterset_fields = ['user']
    search_fields = ['user__name', 'user__phone']


class OperationGrantViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only compatibility endpoint; writes use the atomic authorization API."""

    queryset = OperationGrant.objects.select_related('user').all()
    serializer_class = OperationGrantSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = None
    filterset_fields = ['user', 'code']
    search_fields = ['user__name', 'user__phone']


def _scope_payload(user):
    if user.role == 'admin':
        return {'mode': 'all', 'nodes': []}

    scopes = list(user.management_scopes.all())
    if any(scope.is_all_data for scope in scopes):
        return {'mode': 'all', 'nodes': []}
    if not scopes:
        return {'mode': 'default', 'nodes': []}

    nodes = []
    for scope in scopes:
        if scope.region_id:
            nodes.append({'type': 'region', 'id': str(scope.region_id), 'name': scope.region.name})
        elif scope.branch_id:
            nodes.append({'type': 'branch', 'id': str(scope.branch_id), 'name': scope.branch.name})
        elif scope.team_id:
            nodes.append({'type': 'team', 'id': str(scope.team_id), 'name': scope.team.name})
    return {'mode': 'custom', 'nodes': nodes}


def _authorization_user(user):
    branch = user.branch
    team = branch.team if branch else None
    region = team.region if team else None
    return {
        'id': str(user.id),
        'name': user.name,
        'phone': user.phone,
        'role': user.role,
        'status': user.status,
        'region': str(region.id) if region else None,
        'branch': str(branch.id) if branch else None,
        'region_name': region.name if region else None,
        'branch_name': branch.name if branch else None,
    }


def _grant_codes(user):
    if user.role == 'admin':
        return [item['code'] for item in OPERATION_CATALOG]
    return sorted(user.operation_grants.values_list('code', flat=True))


def _authorization_payload(user):
    codes = _grant_codes(user)
    catalog_codes = {item['code'] for item in OPERATION_CATALOG}
    return {
        'user': _authorization_user(user),
        'scope': _scope_payload(user),
        'operations': [code for code in codes if code in catalog_codes],
        'legacy_operations': [code for code in codes if code not in catalog_codes],
        'legacy_operation_details': [
            {
                'code': code,
                'label': LEGACY_OPERATIONS.get(code, '未登记的旧权限'),
            }
            for code in codes if code not in catalog_codes
        ],
    }


def _is_admin(request):
    return request.user.is_authenticated and request.user.role == 'admin'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def operation_catalog(request):
    """Return the versioned operation catalog used by APIs and the frontend."""
    return Response(OPERATION_CATALOG)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def position_templates(request):
    """Return the active, versioned position baselines for administrative forms."""
    from .position_baselines import get_active_baseline_config

    config = get_active_baseline_config()
    labels = dict(User.ROLE_CHOICES)
    return Response([
        {
            'role': role,
            'role_label': labels.get(role, role),
            'version': config['version'],
            'operations': sorted(codes),
        }
        for role, codes in sorted(config['roles'].items())
    ])


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_authorization(request, user_id):
    """Read or atomically replace one employee's explicit grants and scope."""
    if not _is_admin(request):
        return Response({'detail': '无权操作'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        user = get_object_or_404(
            User.objects.select_related('branch__team__region').prefetch_related(
                'management_scopes__region', 'management_scopes__branch',
                'management_scopes__team', 'operation_grants',
            ),
            pk=user_id,
        )
        return Response(_authorization_payload(user))

    try:
        return _save_user_authorization(request, user_id)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def _parse_scope(scope_data):
    if not isinstance(scope_data, dict):
        raise ValueError('必须提供数据范围配置')

    mode = scope_data.get('mode')
    nodes = scope_data.get('nodes', [])
    if mode not in {'default', 'custom', 'all'} or not isinstance(nodes, list):
        raise ValueError('数据范围配置无效')
    if mode in {'default', 'all'} and nodes:
        raise ValueError('跟随归属或全部组织模式不能包含组织节点')
    if mode == 'custom' and not nodes:
        raise ValueError('自定义范围至少选择一个组织节点')

    node_models = {'region': Region, 'branch': Branch, 'team': Team}
    resolved = []
    seen = set()
    for item in nodes:
        if not isinstance(item, dict) or item.get('type') not in node_models:
            raise ValueError('组织范围节点无效')
        node_type = item['type']
        try:
            node_id = UUID(str(item.get('id', '')))
        except (TypeError, ValueError, AttributeError):
            raise ValueError('组织范围节点无效')
        key = (node_type, node_id)
        if key in seen:
            raise ValueError('组织范围节点不能重复')
        seen.add(key)
        node = node_models[node_type].objects.filter(pk=node_id).first()
        if node is None:
            raise ValueError('组织范围包含不存在的节点')
        resolved.append((node_type, node))
    return mode, resolved


def _save_user_authorization(request, user_id):
    operation_codes = request.data.get('operations')
    if not isinstance(operation_codes, list) or any(not isinstance(code, str) for code in operation_codes):
        return Response({'detail': '业务权限配置无效'}, status=status.HTTP_400_BAD_REQUEST)
    valid_codes = {item['code'] for item in OPERATION_CATALOG}
    if len(operation_codes) != len(set(operation_codes)) or set(operation_codes) - valid_codes:
        return Response({'detail': '业务权限包含重复项或无效操作'}, status=status.HTTP_400_BAD_REQUEST)
    missing_prerequisites = missing_operation_prerequisites(operation_codes)
    if missing_prerequisites:
        labels = {item['code']: item['label'] for item in OPERATION_CATALOG}
        details = [
            f'“{labels.get(code, code)}”需要同时具备'
            + '、'.join(f'“{labels.get(prerequisite, prerequisite)}”' for prerequisite in prerequisites)
            for code, prerequisites in missing_prerequisites.items()
        ]
        return Response({'detail': '；'.join(details)}, status=status.HTTP_400_BAD_REQUEST)

    reason = request.data.get('reason', '')
    if not isinstance(reason, str) or len(reason) > 500:
        return Response({'detail': '变更原因最多填写 500 个字符'}, status=status.HTTP_400_BAD_REQUEST)
    remove_legacy = request.data.get('remove_legacy_operations', [])
    if not isinstance(remove_legacy, list) or any(not isinstance(code, str) for code in remove_legacy):
        return Response({'detail': '旧权限撤销配置无效'}, status=status.HTTP_400_BAD_REQUEST)
    if len(remove_legacy) != len(set(remove_legacy)):
        return Response({'detail': '旧权限撤销配置不能包含重复项'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        scope_mode, scope_nodes = _parse_scope(request.data.get('scope'))
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        user = get_object_or_404(
            User.objects.select_for_update().select_related('branch__team__region').prefetch_related(
                'management_scopes__region', 'management_scopes__branch',
                'management_scopes__team', 'operation_grants',
            ),
            pk=user_id,
        )
        if user.role == 'admin':
            return Response({'detail': '系统管理员的内置权限不能在此修改'}, status=status.HTTP_400_BAD_REQUEST)

        current_codes = set(user.operation_grants.values_list('code', flat=True))
        legacy_codes = current_codes - valid_codes
        unknown_legacy_to_remove = set(remove_legacy) - legacy_codes
        if unknown_legacy_to_remove:
            return Response({
                'detail': '撤销列表包含该账号当前没有的旧权限码，请刷新后重试。',
            }, status=status.HTTP_400_BAD_REQUEST)
        before = {
            'operations': sorted(current_codes),
            'legacy_operations': sorted(legacy_codes),
            'scope': _scope_payload(user),
        }

        after = {
            'operations': sorted((set(operation_codes) | legacy_codes) - set(remove_legacy)),
            'legacy_operations': sorted(legacy_codes - set(remove_legacy)),
            'scope': {'mode': scope_mode, 'nodes': [
                {'type': node_type, 'id': str(node.id), 'name': node.name}
                for node_type, node in scope_nodes
            ] if scope_mode == 'custom' else []},
        }

        def scope_key(scope):
            return scope['mode'], tuple(sorted(
                (node['type'], node['id']) for node in scope['nodes']
            ))

        changed = (
            before['operations'] != after['operations']
            or before['legacy_operations'] != after['legacy_operations']
            or scope_key(before['scope']) != scope_key(after['scope'])
        )
        if not changed:
            return Response(_authorization_payload(user))

        current_valid_codes = current_codes & valid_codes
        operation_codes_changed = current_valid_codes != set(operation_codes)
        user.operation_grants.filter(code__in=valid_codes).delete()
        if remove_legacy:
            user.operation_grants.filter(code__in=remove_legacy).delete()
        OperationGrant.objects.bulk_create([
            OperationGrant(user=user, code=code)
            for code in operation_codes
        ])
        if operation_codes_changed:
            from .position_baselines import record_user_permission_overrides
            record_user_permission_overrides(user, operation_codes)
        user.management_scopes.all().delete()
        new_scopes = []
        if scope_mode == 'all':
            new_scopes.append(ManagementScope(user=user, is_all_data=True))
        elif scope_mode == 'custom':
            for node_type, node in scope_nodes:
                field = {'region': 'region', 'branch': 'branch', 'team': 'team'}[node_type]
                new_scopes.append(ManagementScope(user=user, **{field: node}))
        ManagementScope.objects.bulk_create(new_scopes)

        description = '账号权限与数据范围已更新'
        if reason.strip():
            description = f'{description}；原因：{reason.strip()}'
        create_audit_log(
            request,
            action='update',
            resource_type='user_authorization',
            resource_id=user.id,
            resource_name=user.name,
            description=description,
            before_data=before,
            after_data=after,
        )

        user = User.objects.select_related('branch__team__region').prefetch_related(
            'management_scopes__region', 'management_scopes__branch',
            'management_scopes__team', 'operation_grants',
        ).get(pk=user.pk)
        return Response(_authorization_payload(user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def effective_permissions(request):
    """Return employee-level effective grants for the permission matrix."""
    if not _is_admin(request) and not request.user.can('view_permission_matrix'):
        return Response({'detail': '无权查看权限矩阵'}, status=status.HTTP_403_FORBIDDEN)

    users = User.objects.select_related('branch__team__region').prefetch_related(
        'management_scopes__region', 'management_scopes__branch',
        'management_scopes__team', 'operation_grants',
    ).all().order_by('name', 'phone')
    keyword = request.query_params.get('keyword', '').strip()
    region_id = request.query_params.get('region')
    branch_id = request.query_params.get('branch')
    if keyword:
        users = users.filter(Q(name__icontains=keyword) | Q(phone__icontains=keyword))
    if region_id:
        try:
            users = users.filter(branch__team__region_id=UUID(region_id))
        except (TypeError, ValueError, AttributeError):
            return Response({'detail': '大区筛选无效'}, status=status.HTTP_400_BAD_REQUEST)
    if branch_id:
        try:
            users = users.filter(branch_id=UUID(branch_id))
        except (TypeError, ValueError, AttributeError):
            return Response({'detail': '分公司筛选无效'}, status=status.HTTP_400_BAD_REQUEST)

    operation_filter = request.query_params.get('operation')
    module_filter = request.query_params.get('module')
    module_codes = {
        item['code'] for item in OPERATION_CATALOG
        if not module_filter or item['module'] == module_filter
    }
    result = []
    for user in users:
        payload = _authorization_payload(user)
        codes = payload['operations']
        if operation_filter and codes is not None and operation_filter not in codes:
            continue
        if module_filter and codes is not None and not (set(codes) & module_codes):
            continue
        scope_mode = payload['scope']['mode']
        scope_branches = resolve_scope_branch_count(user)
        branch = user.branch
        team = branch.team if branch else None
        region = team.region if team else None
        result.append({
            'user': str(user.id),
            'id': str(user.id),
            'name': user.name,
            'phone': user.phone,
            'role': user.role,
            'status': user.status,
            'region': str(region.id) if region else None,
            'branch': str(branch.id) if branch else None,
            'region_name': region.name if region else None,
            'branch_name': branch.name if branch else None,
            'scope': payload['scope'],
            'scope_summary': {
                'all': scope_mode == 'all',
                'branch_count': None if scope_mode == 'all' else scope_branches,
            },
            'operations': None if user.role == 'admin' else codes,
            'legacy_operations': payload['legacy_operations'],
        })
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permission_matrix_organizations(request):
    """Return organization filters for users allowed to view the permission matrix."""
    if not _is_admin(request) and not request.user.can('view_permission_matrix'):
        return Response({'detail': '无权查看权限矩阵'}, status=status.HTTP_403_FORBIDDEN)

    regions = [
        {'id': str(region_id), 'name': name}
        for region_id, name in Region.objects.order_by('name').values_list('id', 'name')
    ]
    branches = [
        {
            'id': str(branch_id),
            'name': name,
            'region': str(region_id) if region_id else None,
        }
        for branch_id, name, region_id in Branch.objects.order_by('name').values_list(
            'id', 'name', 'team__region_id',
        )
    ]
    return Response({'regions': regions, 'branches': branches})


def resolve_scope_branch_count(user):
    from .scope import resolve_user_scope
    scope = resolve_user_scope(user)
    return None if scope.all else len(scope.branches)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_permissions(request):
    """Return this account's current operation grants and effective data scope."""
    user = User.objects.select_related('branch__team__region').prefetch_related(
        'management_scopes__region', 'management_scopes__branch',
        'management_scopes__team', 'operation_grants',
    ).get(pk=request.user.pk)
    from .serializers import UserPermissionSummarySerializer
    data = UserPermissionSummarySerializer(user).data
    data['scope'] = _scope_payload(user)
    data['authorization'] = _authorization_user(user)
    data['scope_summary'] = {
        'all': data['scope']['mode'] == 'all',
        'branch_count': resolve_scope_branch_count(user),
    }
    data['page_operations'] = PAGE_ACCESS_OPERATIONS
    data['operation_prerequisites'] = {
        code: list(prerequisites)
        for code, prerequisites in OPERATION_PREREQUISITES.items()
    }
    return Response(data)

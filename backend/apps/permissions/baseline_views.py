"""Administrator preview and confirmation API for position permission baselines."""

import hashlib
import json

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.utils import create_audit_log
from apps.users.models import User

from .models import (
    OperationGrant,
    PositionBaselineAssignment,
    PositionBaselineState,
    PositionPermissionOverride,
)
from .operations import OPERATION_CATALOG
from .position_baselines import (
    POSITION_BASELINE_CONFIG,
    apply_user_baseline_plan,
    plan_user_baseline,
    validate_baseline_config,
)


def _admin_only(request):
    return bool(request.user.is_authenticated and request.user.role == 'admin')


def _config_from_state(state):
    if state and state.version and state.baseline_config:
        return state.baseline_config
    return {'version': '', 'roles': {}}


def _operation_details(codes):
    labels = {item['code']: item['label'] for item in OPERATION_CATALOG}
    return [{'code': code, 'label': labels.get(code, code)} for code in sorted(codes)]


def _user_input_snapshot(user):
    assignment = PositionBaselineAssignment.objects.filter(user=user).first()
    overrides = list(PositionPermissionOverride.objects.filter(user=user)
                     .order_by('code').values_list('code', 'effect'))
    grants = sorted(OperationGrant.objects.filter(user=user).values_list('code', flat=True))
    return {
        'id': str(user.id),
        'role': user.role,
        'status': user.status,
        'is_active': user.is_active,
        'branch': str(user.branch_id) if user.branch_id else None,
        'grants': grants,
        'assignment': {
            'version': assignment.version,
            'role': assignment.role,
            'baseline_codes': sorted(assignment.baseline_codes),
        } if assignment else None,
        'overrides': overrides,
    }


def _preview_payload(state, users):
    current_config = _config_from_state(state)
    target_config = validate_baseline_config(POSITION_BASELINE_CONFIG)
    labels = {item['code']: item['label'] for item in OPERATION_CATALOG}
    rows = []
    digest_inputs = []
    add_count = remove_count = legacy_count = 0

    for user in users:
        plan = plan_user_baseline(user, target_config)
        digest_inputs.append(_user_input_snapshot(user))
        if not (plan['added'] or plan['removed'] or plan['legacy']):
            continue
        branch = user.branch
        rows.append({
            'user': str(user.id),
            'name': user.name,
            'phone': user.phone,
            'role': user.role,
            'role_label': dict(User.ROLE_CHOICES).get(user.role, user.role),
            'branch_name': branch.name if branch else None,
            'added': _operation_details(plan['added']),
            'removed': _operation_details(plan['removed']),
            'legacy_codes': sorted(plan['legacy']),
            'scope_preserved': True,
        })
        add_count += len(plan['added'])
        remove_count += len(plan['removed'])
        legacy_count += len(plan['legacy'])

    current_roles = current_config.get('roles', {})
    target_roles = target_config['roles']
    role_changes = []
    for role in sorted(set(current_roles) | set(target_roles)):
        old_codes = set(current_roles.get(role, ()))
        new_codes = set(target_roles.get(role, ()))
        if old_codes != new_codes:
            role_changes.append({
                'role': role,
                'role_label': dict(User.ROLE_CHOICES).get(role, role),
                'added': _operation_details(new_codes - old_codes),
                'removed': _operation_details(old_codes - new_codes),
            })

    target_matches = bool(
        state
        and state.version == target_config['version']
        and state.baseline_config == target_config
    )
    token_source = {
        'from_version': state.version if state and state.version else None,
        'target_config': target_config,
        'users': digest_inputs,
    }
    token = hashlib.sha256(json.dumps(
        token_source, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
    ).encode('utf-8')).hexdigest()
    inactive_count = User.objects.filter(
        role__in=target_roles.keys(),
    ).exclude(status='active', is_active=True).count()

    return {
        'from_version': state.version if state and state.version else None,
        'to_version': target_config['version'],
        'has_changes': not target_matches,
        'active_employee_count': len(users),
        'changed_employee_count': len(rows),
        'added_permission_count': add_count,
        'removed_permission_count': remove_count,
        'legacy_permission_count': legacy_count,
        'inactive_employee_count': inactive_count,
        'role_changes': role_changes,
        'employees': rows,
        'preview_token': token,
    }


def _preview_for_state(state=None, users=None):
    if state is None:
        state = PositionBaselineState.objects.filter(pk=1).first()
    if users is None:
        users = list(
            User.objects.filter(
                status='active', is_active=True,
                role__in=POSITION_BASELINE_CONFIG['roles'].keys(),
            )
            .select_related('branch')
            .order_by('name', 'phone')
        )
    return _preview_payload(state, users)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def position_baseline_preview(request):
    if not _admin_only(request):
        return Response({'detail': '仅系统管理员可预览岗位权限基线'}, status=status.HTTP_403_FORBIDDEN)
    return Response(_preview_for_state())


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def position_baseline_apply(request):
    if not _admin_only(request):
        return Response({'detail': '仅系统管理员可确认岗位权限基线'}, status=status.HTTP_403_FORBIDDEN)

    if 'expected_from_version' not in request.data or not isinstance(request.data.get('preview_token'), str):
        return Response({'detail': '请先预览基线变更，再确认应用'}, status=status.HTTP_400_BAD_REQUEST)

    expected_from_version = request.data.get('expected_from_version') or ''
    preview_token = request.data['preview_token']
    target_config = validate_baseline_config(POSITION_BASELINE_CONFIG)

    with transaction.atomic():
        state, _ = PositionBaselineState.objects.select_for_update().get_or_create(
            pk=1, defaults={'version': '', 'baseline_config': {}},
        )
        if state.version != expected_from_version:
            return Response(
                {'detail': '岗位基线版本已变化，请重新预览后再确认'},
                status=status.HTTP_409_CONFLICT,
            )

        users = list(
            User.objects.filter(
                status='active', is_active=True,
                role__in=target_config['roles'].keys(),
            )
            .select_related('branch')
            .select_for_update(of=('self',))
            .order_by('name', 'phone')
        )
        preview = _preview_payload(state, users)
        if preview['preview_token'] != preview_token:
            return Response(
                {'detail': '员工授权已变化，请重新预览后再确认'},
                status=status.HTTP_409_CONFLICT,
            )
        if not preview['has_changes']:
            return Response({'detail': '当前岗位基线已是最新版本'}, status=status.HTTP_400_BAD_REQUEST)

        plans = [(user, plan_user_baseline(user, target_config)) for user in users]
        before = {
            'version': state.version or None,
            'baseline_config': state.baseline_config,
        }
        for user, plan in plans:
            apply_user_baseline_plan(user, plan, target_config)

        state.version = target_config['version']
        state.baseline_config = target_config
        state.updated_by = request.user
        state.save(update_fields=['version', 'baseline_config', 'updated_by', 'updated_at'])
        create_audit_log(
            request,
            action='update',
            resource_type='position_permission_baseline',
            resource_id=state.pk,
            resource_name='岗位权限基线',
            description=(
                f"岗位权限基线由 {before['version'] or '未初始化'} 更新为 {target_config['version']}，"
                f"同步在职普通员工 {len(users)} 人"
            ),
            before_data=before,
            after_data={
                'version': target_config['version'],
                'synchronized_users': len(users),
                'added_permission_count': preview['added_permission_count'],
                'removed_permission_count': preview['removed_permission_count'],
                'legacy_permission_count_retained_for_review': preview['legacy_permission_count'],
                'data_scope_changed': False,
            },
        )

    return Response({
        'detail': '岗位权限基线已确认并应用',
        'version': target_config['version'],
        'synchronized_users': len(users),
        'added_permission_count': preview['added_permission_count'],
        'removed_permission_count': preview['removed_permission_count'],
        'legacy_permission_count_retained_for_review': preview['legacy_permission_count'],
    })

from django.db.models import Q
from django.db import transaction
from django.core.files.storage import default_storage
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.permissions.permissions import OperationPermission
from apps.permissions.models import ManagementScope, OperationGrant
from apps.audit.decorators import audit_log
from apps.audit.utils import create_audit_log
from apps.organizations.models import Branch, Region, Team
from .models import User
from .serializers import UserSerializer, UserWriteOptionSerializer, UserDeleteOptionSerializer
from .filters import UserFilterSet


class SetSystemAvatarSerializer(serializers.Serializer):
    system_avatar = serializers.CharField(required=True)


# 岗位分配权线：各级岗位可分配的岗位（supervisor/staff 已退役）
# manager 可建同岗（分公司行政互建账号，原"manager 建 staff"语义的合并后等价；
# 新号无任何授权/范围，扩岗风险由权限分配页(admin)把关）
MANAGEABLE_ROLES = {
    'admin': ['admin', 'director', 'manager', 'leader'],
    'director': ['manager', 'leader'],
    'manager': ['manager', 'leader'],
    'leader': [],
}

# 退役岗位按 migrate_positions 的换岗目标（manager）计权线：
# 存量 supervisor/staff 的管理关系不因退役冻结，也不放开对在职高岗位的越权
_RETIRED_ROLE_LINE = {'supervisor': 'manager', 'staff': 'manager'}


def _get_user_queryset(user):
    """Return the queryset of users that the requesting user can see/manage.

    范围由管理授权决定：admin 或「全部数据」授权为全部（管理权线由
    _validate_in_scope 把关）；其余为授权组织节点（沿树展开为分公司）内 + 自己。
    """
    qs = User.objects.select_related('branch', 'branch__team', 'branch__team__region', 'team', 'team__region', 'created_by')

    if user.role == 'admin':
        return qs  # Admin sees everyone

    from apps.permissions.scope import resolve_user_scope
    scope = resolve_user_scope(user)
    if scope.all:
        return qs  # 「全部数据」授权：全部用户（须先于 is_empty 判断；权线闸在 _validate_in_scope）
    if scope.is_empty:
        return qs.filter(id=user.id)  # 无授权仅见自己

    q = Q(id=user.id)  # 总是包含自己
    if scope.branches:
        q |= Q(branch__in=scope.branches)
    if scope.teams:
        q |= Q(team__in=scope.teams)
    return qs.filter(q).distinct()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('branch', 'branch__team', 'branch__team__region', 'team', 'team__region', 'created_by').all()
    serializer_class = UserSerializer
    filterset_class = UserFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = None
    # Avatar has its own self/admin check and bypasses these directory permissions.
    required_operations = {
        'list': 'view_users',
        'retrieve': 'view_users',
        'create': ('view_users', 'edit_users'),
        'update': ('view_users', 'edit_users'),
        'partial_update': ('view_users', 'edit_users'),
        'destroy': ('view_users', 'edit_users'),
        'delete_preview': ('view_users', 'edit_users'),
    }

    def get_queryset(self):
        # 员工目录与账号维护共用数据范围；管理员仍通过 _get_user_queryset 返回全员。
        user = self.request.user
        queryset = _get_user_queryset(user)
        if self.action != 'list' or self.request.query_params.get('scope') != 'write':
            return queryset
        if user.role == 'admin':
            return queryset

        from apps.permissions.scope import resolve_user_scope
        scope = resolve_user_scope(user)
        role_line = _RETIRED_ROLE_LINE.get(user.role, user.role)
        manageable_lines = MANAGEABLE_ROLES.get(role_line, [])
        manageable_roles = [
            role for role, _ in User.ROLE_CHOICES
            if _RETIRED_ROLE_LINE.get(role, role) in manageable_lines
        ]
        writable_targets = Q(id=user.id)
        if scope.all:
            writable_targets |= Q(role__in=manageable_roles)
        elif scope.branches:
            writable_targets |= Q(role__in=manageable_roles, branch_id__in=scope.branches)
        return queryset.filter(writable_targets).distinct()

    def get_required_operations(self, request):
        if self.action == 'list' and request.query_params.get('scope') == 'write':
            return ('view_users', 'edit_users')
        return self.required_operations.get(self.action)

    def get_serializer_class(self):
        if self.action == 'list' and self.request.query_params.get('scope') == 'write':
            if self.request.user.can('edit_users'):
                return UserWriteOptionSerializer
            return UserDeleteOptionSerializer
        return super().get_serializer_class()

    @audit_log(action='create', resource_type='User', description_template='创建用户')
    def perform_create(self, serializer):
        """Validate that the creator can assign the given role."""
        creator = self.request.user
        data = serializer.validated_data
        target_role = data.get('role', 'manager')

        self._validate_role_assignment(creator, target_role)
        self._validate_target_branch_in_scope(creator, data.get('branch'))

        from apps.permissions.position_baselines import (
            get_active_baseline_config,
            reset_user_to_position_baseline,
        )

        with transaction.atomic():
            baseline_config = get_active_baseline_config(lock=True)
            created_user = serializer.save(created_by=creator)
            reset_user_to_position_baseline(created_user, config=baseline_config)

    @audit_log(action='update', resource_type='User', description_template='更新用户')
    def perform_update(self, serializer):
        """Validate that the updater can modify the target user's role."""
        updater = self.request.user
        instance = serializer.instance
        with transaction.atomic():
            from apps.permissions.position_baselines import get_active_baseline_config
            # Match baseline application lock order: singleton baseline row first, then users.
            baseline_config = get_active_baseline_config(lock=True)
            instance = User.objects.select_for_update().get(pk=serializer.instance.pk)
            serializer.instance = instance
            data = serializer.validated_data
            target_role = data.get('role', instance.role)

            self._validate_in_scope(updater, instance)
            if 'role' in data:
                self._validate_role_assignment(updater, target_role)
            self._validate_target_branch_in_scope(updater, data.get('branch'))

            role_changed = target_role != instance.role
            branch_changed = (
                'branch' in data
                and (data['branch'].id if data['branch'] else None) != instance.branch_id
            )
            status_changed = data.get('status', instance.status) != instance.status
            previous_status = instance.status
            before_permissions = None
            previous_role = instance.role
            previous_branch = instance.branch
            if role_changed or branch_changed:
                before_permissions = {
                    'employee': {
                        'role': previous_role,
                        'role_label': dict(User.ROLE_CHOICES).get(previous_role, previous_role),
                        'branch_id': str(instance.branch_id) if instance.branch_id else None,
                        'branch_name': previous_branch.name if previous_branch else None,
                    },
                    'operations': sorted(instance.operation_grants.values_list('code', flat=True)),
                    'scopes': [
                        {
                            'all': scope.is_all_data,
                            'region': str(scope.region_id) if scope.region_id else None,
                            'branch': str(scope.branch_id) if scope.branch_id else None,
                            'team': str(scope.team_id) if scope.team_id else None,
                        }
                        for scope in instance.management_scopes.all()
                    ],
                }

            from apps.permissions.position_baselines import (
                reset_user_to_position_baseline,
                synchronize_user_baseline,
            )

            serializer.save()

            if role_changed:
                reset_user_to_position_baseline(instance, config=baseline_config)
            elif previous_status != 'active' and instance.status == 'active':
                synchronize_user_baseline(instance, config=baseline_config)

            if role_changed or branch_changed:
                instance.management_scopes.all().delete()
                instance._mgmt_scope_cache = None

            if before_permissions is not None:
                current_branch = instance.branch
                create_audit_log(
                    self.request,
                    action='update',
                    resource_type='user_authorization',
                    resource_id=instance.id,
                    resource_name=instance.name,
                    description=(
                        '员工岗位变更，业务权限已重置为新岗位基线；数据范围已重置为所属分公司默认范围'
                        if role_changed else
                        '员工所属分公司变更，保留业务权限并重置为所属分公司默认数据范围'
                    ),
                    before_data=before_permissions,
                    after_data={
                        'employee': {
                            'role': instance.role,
                            'role_label': dict(User.ROLE_CHOICES).get(instance.role, instance.role),
                            'branch_id': str(instance.branch_id) if instance.branch_id else None,
                            'branch_name': current_branch.name if current_branch else None,
                        },
                        'operations': sorted(instance.operation_grants.values_list('code', flat=True)),
                        'scopes': [],
                    },
                )

    @audit_log(action='delete', resource_type='User', description_template='删除用户')
    def perform_destroy(self, instance):
        """Delete an account while preserving business history and appointments."""
        from apps.transfers.models import Transfer

        operator = self.request.user
        with transaction.atomic():
            # Share the account lifecycle lock with creates and role/status changes so
            # concurrent deletions cannot remove the last active administrator.
            from apps.permissions.position_baselines import get_active_baseline_config
            get_active_baseline_config(lock=True)
            instance = User.objects.select_for_update().get(pk=instance.pk)
            self._validate_in_scope(operator, instance)
            self._validate_delete_scope(operator, instance)
            self._validate_last_active_admin(instance)

            responsibilities = self._deletion_responsibilities(instance, lock=True)
            self._validate_responsibility_scope(operator, responsibilities)
            self._replace_responsibilities(instance, responsibilities, self.request.data.get('successors', []))

            Transfer.objects.filter(
                created_by=instance,
                action_type__in=[
                    Transfer.ACTION_PURCHASE,
                    Transfer.ACTION_ASSIGN,
                    Transfer.ACTION_TRANSFER,
                    Transfer.ACTION_RECOVERY,
                ],
                审批状态='草稿',
            ).delete()
            reviewed_legacy_draft_ids = self._validated_legacy_draft_ids(
                instance,
                self.request.data.get('legacy_draft_reviewed_ids'),
                self.request.data.get('legacy_draft_ids'),
                lock=True,
            )
            if reviewed_legacy_draft_ids:
                Transfer.objects.filter(pk__in=reviewed_legacy_draft_ids).delete()
            from apps.audit.utils import clear_user_phone_snapshots
            clear_user_phone_snapshots(instance)
            avatar_name = instance.avatar.name if instance.avatar else None
            instance.delete()
            if avatar_name:
                transaction.on_commit(lambda: default_storage.delete(avatar_name))

    @action(detail=True, methods=['get'], url_path='delete-preview')
    def delete_preview(self, request, pk=None):
        target = self.get_object()
        self._validate_in_scope(request.user, target)
        self._validate_delete_scope(request.user, target)
        self._validate_last_active_admin(target)
        responsibilities = self._deletion_responsibilities(target)
        self._validate_responsibility_scope(request.user, responsibilities)
        legacy_drafts = self._legacy_draft_candidates(target)
        return Response({
            'user': {'id': str(target.pk), 'name': target.name},
            'legacy_draft_candidates': [
                {
                    'id': str(row.pk),
                    'document_number': row.单据编号 or str(row.pk),
                    'action_type': row.action_type,
                    'creator_snapshot': row.创建人,
                    'date': row.调拨日期.isoformat() if row.调拨日期 else None,
                }
                for row in legacy_drafts
            ],
            'responsibilities': [
                {
                    'key': row['key'],
                    'node_type': row['node_type'],
                    'type': row['type'],
                    'id': str(row['node'].pk),
                    'name': row['node'].name,
                    'role': row['role'],
                    'candidates': [
                        {'id': str(candidate.pk), 'name': candidate.name}
                        for candidate in self._successor_candidates(target, row)
                    ],
                }
                for row in responsibilities
            ],
        })

    @staticmethod
    def _legacy_draft_candidates(target, *, lock=False):
        from apps.transfers.models import Transfer

        creator_snapshots = {value for value in (target.name, target.phone) if value}
        if not creator_snapshots:
            return Transfer.objects.none()
        queryset = Transfer.objects.filter(
            created_by__isnull=True,
            action_type__in=[
                Transfer.ACTION_PURCHASE,
                Transfer.ACTION_ASSIGN,
                Transfer.ACTION_TRANSFER,
                Transfer.ACTION_RECOVERY,
            ],
            审批状态='草稿',
            创建人__in=creator_snapshots,
        ).order_by('pk')
        return queryset.select_for_update() if lock else queryset

    @classmethod
    def _validated_legacy_draft_ids(cls, target, reviewed_ids, delete_ids, *, lock=False):
        candidates = list(cls._legacy_draft_candidates(target, lock=lock))
        candidate_ids = {str(row.pk) for row in candidates}
        if not candidate_ids:
            if reviewed_ids or delete_ids:
                raise serializers.ValidationError({'legacy_draft_ids': '待核对旧草稿已变化，请重新预览后重试'})
            return set()
        if not isinstance(reviewed_ids, list) or set(reviewed_ids) != candidate_ids:
            raise serializers.ValidationError({
                'legacy_draft_reviewed_ids': '请先逐条核对创建人无法确认的旧草稿，并刷新删除预览',
            })
        if not isinstance(delete_ids, list) or len(delete_ids) != len(set(delete_ids)):
            raise serializers.ValidationError({'legacy_draft_ids': '请选择有效的旧草稿删除清单'})
        if set(delete_ids) - candidate_ids:
            raise serializers.ValidationError({'legacy_draft_ids': '删除清单包含未列入本次预览的旧草稿'})
        return set(delete_ids)

    @staticmethod
    def _validate_last_active_admin(target):
        if target.role != 'admin' or target.status != 'active' or not target.is_active:
            return
        active_admins = User.objects.filter(role='admin', status='active', is_active=True).count()
        if active_admins <= 1:
            raise serializers.ValidationError({'detail': '不能删除最后一名在职系统管理员'})

    @staticmethod
    def _deletion_responsibilities(target, lock=False):
        def locked(queryset):
            return queryset.select_for_update() if lock else queryset

        rows = []
        for node in locked(Region.objects.filter(manager=target).order_by('id')):
            branch_ids = list(Branch.objects.filter(team__region=node).values_list('id', flat=True))
            rows.append({
                'key': f'region:{node.pk}', 'node_type': 'region',
                'type': '区域负责人', 'node': node,
                'role': 'director', 'branch_ids': branch_ids, 'field': 'manager',
            })
        for node in locked(Team.objects.filter(leader=target).order_by('id')):
            branch_ids = list(Branch.objects.filter(team=node).values_list('id', flat=True))
            rows.append({
                'key': f'team:{node.pk}', 'node_type': 'team',
                'type': '行政组长', 'node': node,
                'role': 'leader', 'branch_ids': branch_ids, 'field': 'leader',
            })
        for node in locked(Branch.objects.filter(manager=target).order_by('id')):
            rows.append({
                'key': f'branch:{node.pk}', 'node_type': 'branch',
                'type': '分公司负责人', 'node': node,
                'role': 'manager', 'branch_ids': [node.pk], 'field': 'manager',
            })
        return rows

    @staticmethod
    def _validate_responsibility_scope(operator, responsibilities):
        if operator.role == 'admin':
            return
        from apps.permissions.scope import resolve_user_scope

        scope = resolve_user_scope(operator)
        if scope.all:
            return
        allowed_branches = set(scope.branches)
        for row in responsibilities:
            if not row['branch_ids'] or not set(row['branch_ids']).issubset(allowed_branches):
                raise serializers.ValidationError({
                    'detail': f'您无权为范围外的{row["type"]}办理负责人交接',
                })

    @staticmethod
    def _validate_delete_scope(operator, target):
        if operator.role == 'admin':
            return
        from apps.permissions.scope import resolve_user_scope

        scope = resolve_user_scope(operator)
        if scope.all:
            return
        in_branch = bool(target.branch_id and target.branch_id in scope.branches)
        in_team = bool(target.team_id and target.team_id in scope.teams)
        if not (in_branch or in_team):
            raise serializers.ValidationError({'detail': '删除目标员工必须位于当前数据范围内'})

    @staticmethod
    def _successor_candidates(target, responsibility):
        if not responsibility['branch_ids']:
            return User.objects.none()
        return User.objects.filter(
            role=responsibility['role'], status='active', is_active=True,
            branch_id__in=responsibility['branch_ids'],
        ).exclude(pk=target.pk).order_by('name', 'id')

    def _replace_responsibilities(self, target, responsibilities, supplied):
        if not isinstance(supplied, list):
            raise serializers.ValidationError({'successors': '负责人接任信息格式无效'})
        required_keys = {(row['node_type'], str(row['node'].pk)) for row in responsibilities}
        supplied_by_node = {}
        for item in supplied:
            if not isinstance(item, dict):
                raise serializers.ValidationError({'successors': '负责人接任信息格式无效'})
            node_key = (item.get('node_type'), str(item.get('node_id') or ''))
            if node_key in supplied_by_node:
                raise serializers.ValidationError({'successors': '同一组织节点不能重复指定接任人'})
            supplied_by_node[node_key] = item.get('user_id')
        if set(supplied_by_node) != required_keys:
            if required_keys:
                raise serializers.ValidationError({'successors': '请为该员工负责的每个组织节点指定新负责人'})
            if supplied_by_node:
                raise serializers.ValidationError({'successors': '该员工没有需要交接的组织负责人节点'})
            return

        candidates_by_id = {}
        for row in responsibilities:
            try:
                successor_id = supplied_by_node[(row['node_type'], str(row['node'].pk))]
                successor = User.objects.select_for_update().get(pk=successor_id)
            except (User.DoesNotExist, TypeError, ValueError):
                raise serializers.ValidationError({
                    'successors': f'「{row["node"].name}」的接任人无效或已不存在',
                })
            allowed = self._successor_candidates(target, row).filter(pk=successor.pk).exists()
            if not allowed:
                raise serializers.ValidationError({
                    'successors': f'「{row["node"].name}」的接任人必须是在该组织节点内的在职{dict(User.ROLE_CHOICES).get(row["role"], row["role"])}',
                })
            candidates_by_id[row['key']] = successor

        for row in responsibilities:
            node = row['node']
            setattr(node, row['field'], candidates_by_id[row['key']])
            node.save(update_fields=[row['field']])

    def _validate_role_assignment(self, creator, target_role):
        """Check if creator is allowed to assign the target role."""
        manageable = MANAGEABLE_ROLES.get(creator.role, [])
        if target_role not in manageable:
            role_display = dict(User.ROLE_CHOICES).get(target_role, target_role)
            raise serializers.ValidationError(
                {'role': f'您没有权限分配「{role_display}」角色'}
            )

    def _validate_target_branch_in_scope(self, operator, branch_value):
        """改挂目标分公司也须在操作者范围（防把用户改挂到范围外；admin 豁免）。"""
        if operator.role == 'admin' or branch_value is None:
            return
        from core.permissions import validate_branches_in_scope
        validate_branches_in_scope(operator, branch_value)

    def _validate_in_scope(self, operator, target_user):
        """Check if the target user is within the operator's granted scope."""
        if operator.role == 'admin':
            return
        if target_user.id == operator.id:
            return
        # 权线闸：目标当前岗位须在操作者可分配岗位内（先于 scope.all 执行；
        # 不带 role 字段的改/删与把高岗位用户降级的请求都在此拦截）
        op_line = _RETIRED_ROLE_LINE.get(operator.role, operator.role)
        target_line = _RETIRED_ROLE_LINE.get(target_user.role, target_user.role)
        if target_line not in MANAGEABLE_ROLES.get(op_line, []):
            role_display = dict(User.ROLE_CHOICES).get(target_user.role, target_user.role)
            raise serializers.ValidationError(
                {'detail': f'您没有权限管理「{role_display}」用户'}
            )
        from apps.permissions.scope import resolve_user_scope
        scope = resolve_user_scope(operator)
        if scope.all:
            return  # 「全部数据」授权可管理权线内的任何用户
        in_branch = bool(target_user.branch_id and target_user.branch_id in scope.branches)
        in_team = bool(target_user.team_id and target_user.team_id in scope.teams)
        if not (in_branch or in_team):
            raise serializers.ValidationError(
                {'detail': '您只能管理授权范围内的用户'}
            )

    # 同 url_path 双 action 会被 DRF 按方法名排序注册成两条 pattern，先注册者遮蔽
    # 后者的方法（POST 405 即此坑，见 assets image action 先例），故合一个 action 分流。
    @action(detail=True, methods=['post', 'delete'], url_path='avatar', permission_classes=[IsAuthenticated])
    def avatar(self, request, pk=None):
        """头像维护：POST 上传/覆盖（仅本人或管理员），DELETE 清除自定义头像。"""
        user = self.get_object()
        if request.user != user and request.user.role != 'admin':
            return Response({'detail': '无权操作'}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save(update_fields=['avatar', 'updated_at'])
            serializer = UserSerializer(user, context={'request': request})
            return Response(serializer.data)

        if 'avatar' not in request.FILES:
            return Response({'detail': '请上传头像文件'}, status=status.HTTP_400_BAD_REQUEST)

        avatar_file = request.FILES['avatar']
        # 验证文件类型
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if avatar_file.content_type not in allowed_types:
            return Response({'detail': '仅支持 JPG、PNG、WebP 格式的图片'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证文件大小（2MB）
        if avatar_file.size > 2 * 1024 * 1024:
            return Response({'detail': '图片大小不能超过 2MB'}, status=status.HTTP_400_BAD_REQUEST)

        user.avatar = avatar_file
        user.system_avatar = None
        user.save(update_fields=['avatar', 'system_avatar', 'updated_at'])
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='system-avatar', permission_classes=[IsAuthenticated])
    def set_system_avatar(self, request, pk=None):
        user = self.get_object()
        if request.user != user and request.user.role != 'admin':
            return Response({'detail': '无权操作'}, status=status.HTTP_403_FORBIDDEN)

        input_serializer = SetSystemAvatarSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        avatar_key = input_serializer.validated_data['system_avatar']

        if avatar_key not in User.SYSTEM_AVATAR_CHOICES:
            return Response({'detail': '无效的预设头像标识'}, status=status.HTTP_400_BAD_REQUEST)

        # 清除自定义头像文件
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None

        user.system_avatar = avatar_key
        user.save(update_fields=['avatar', 'system_avatar', 'updated_at'])
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

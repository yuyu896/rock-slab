from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.permissions import IsRoleMin, ROLE_LEVELS
from .models import User
from .serializers import UserSerializer
from .filters import UserFilterSet


class SetSystemAvatarSerializer(serializers.Serializer):
    system_avatar = serializers.CharField(required=True)


# Roles that each level can manage (lower level number = higher authority)
MANAGEABLE_ROLES = {
    'admin': ['admin', 'manager', 'supervisor', 'leader', 'staff'],
    'manager': ['supervisor', 'leader', 'staff'],
    'supervisor': ['leader', 'staff'],
    'leader': ['staff'],
}


def _get_user_queryset(user):
    """Return the queryset of users that the requesting user can see/manage."""
    qs = User.objects.select_related('branch', 'region', 'leader', 'created_by')

    if user.role == 'admin':
        return qs  # Admin sees everyone

    if user.role == 'manager':
        # Manager can see all users (view reports), but management is limited
        return qs

    if user.role == 'supervisor' and getattr(user, 'region', None):
        # Supervisor: users within their region
        return qs.filter(region=user.region)

    if user.role == 'leader' and getattr(user, 'branch', None):
        # Leader: staff within their branch
        return qs.filter(
            branch=user.branch,
            role__in=['staff'],
        )

    # Staff: can only see themselves
    return qs.filter(id=user.id)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('branch', 'region', 'leader', 'created_by').all()
    serializer_class = UserSerializer
    filterset_class = UserFilterSet
    permission_classes = [IsAuthenticated, IsRoleMin]
    min_role = 'supervisor'  # Minimum supervisor to access user management
    pagination_class = None

    def get_queryset(self):
        if self.action in ('list', 'retrieve'):
            return User.objects.select_related('branch', 'region', 'leader', 'created_by').all()
        return _get_user_queryset(self.request.user)

    def get_permissions(self):
        """Dynamically adjust permissions based on action."""
        if self.action == 'list' or self.action == 'retrieve':
            # List/retrieve: all authenticated users can view
            self.min_role = 'staff'
        elif self.action in ('create', 'update', 'partial_update', 'destroy'):
            # Write operations: supervisor and above
            self.min_role = 'supervisor'
        else:
            # Avatar actions: any authenticated user (self-check in method)
            self.min_role = 'staff'
        return super().get_permissions()

    def perform_create(self, serializer):
        """Validate that the creator can assign the given role."""
        creator = self.request.user
        data = serializer.validated_data
        target_role = data.get('role', 'staff')

        self._validate_role_assignment(creator, target_role)

        # Supervisor: auto-set region to their own region
        if creator.role == 'supervisor' and not data.get('region'):
            data['region'] = creator.region

        # Leader: auto-set branch to their own branch
        if creator.role == 'leader':
            if not data.get('branch'):
                data['branch'] = creator.branch
            # Leader can only create staff
            if target_role != 'staff':
                raise serializers.ValidationError(
                    {'role': '行政组长只能创建行政专员账号'}
                )

        serializer.save(created_by=creator)

    def perform_update(self, serializer):
        """Validate that the updater can modify the target user's role."""
        updater = self.request.user
        instance = serializer.instance
        data = serializer.validated_data
        target_role = data.get('role', instance.role)

        # Cannot modify users outside your scope
        self._validate_in_scope(updater, instance)

        # Validate role change
        if 'role' in data:
            self._validate_role_assignment(updater, target_role)

        serializer.save()

    def perform_destroy(self, instance):
        """Only allow deleting users within your management scope."""
        self._validate_in_scope(self.request.user, instance)
        # Soft-delete: set status to inactive instead of actual delete
        instance.status = 'inactive'
        instance.save(update_fields=['status', 'updated_at'])

    def _validate_role_assignment(self, creator, target_role):
        """Check if creator is allowed to assign the target role."""
        manageable = MANAGEABLE_ROLES.get(creator.role, [])
        if target_role not in manageable:
            role_display = dict(User.ROLE_CHOICES).get(target_role, target_role)
            raise serializers.ValidationError(
                {'role': f'您没有权限分配「{role_display}」角色'}
            )

    def _validate_in_scope(self, operator, target_user):
        """Check if the target user is within the operator's scope."""
        if operator.role == 'admin':
            return
        if operator.role == 'manager':
            return
        if operator.role == 'supervisor':
            if target_user.region_id != operator.region_id:
                raise serializers.ValidationError(
                    {'detail': '您只能管理本区域内的用户'}
                )
        elif operator.role == 'leader':
            if target_user.branch_id != operator.branch_id:
                raise serializers.ValidationError(
                    {'detail': '您只能管理本分公司内的用户'}
                )
        else:
            raise serializers.ValidationError(
                {'detail': '您没有权限执行此操作'}
            )

    @action(detail=True, methods=['post'], url_path='avatar', permission_classes=[IsAuthenticated])
    def upload_avatar(self, request, pk=None):
        user = self.get_object()
        # 权限：仅本人或管理员可上传
        if request.user != user and request.user.role != 'admin':
            return Response({'detail': '无权操作'}, status=status.HTTP_403_FORBIDDEN)

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

    @action(detail=True, methods=['delete'], url_path='avatar', permission_classes=[IsAuthenticated])
    def delete_avatar(self, request, pk=None):
        user = self.get_object()
        if request.user != user and request.user.role != 'admin':
            return Response({'detail': '无权操作'}, status=status.HTTP_403_FORBIDDEN)

        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save(update_fields=['avatar', 'updated_at'])
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

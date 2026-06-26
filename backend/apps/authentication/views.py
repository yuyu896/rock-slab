from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from rest_framework.authtoken.models import Token as BaseToken
from rest_framework.decorators import api_view, permission_classes, throttle_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from apps.users.serializers import UserSerializer
from apps.authentication.serializers import LoginSerializer
from apps.authentication.models import ExpiringToken
from apps.authentication.throttling import LoginRateThrottle
from apps.authentication.account_lockout import (
    check_account_locked, record_login_failure, clear_login_failures,
)
from apps.audit.decorators import audit_log


def get_or_create_token(user):
    """获取或刷新 ExpiringToken。

    - 已存在且未过期：直接复用。
    - 不存在或已过期：删除该用户所有 token（子表 + 基础表孤儿），再创建全新的。
      用"删除+创建"而非原地 save，规避多表继承下原地改 key 再 save 的异常。
    - 并发登录兜底 IntegrityError。
    """
    token = None
    try:
        token = ExpiringToken.objects.get(user=user)
    except ExpiringToken.DoesNotExist:
        pass

    if token is None or token.is_expired:
        ExpiringToken.objects.filter(user=user).delete()
        BaseToken.objects.filter(user=user).delete()
        try:
            token = ExpiringToken.objects.create(user=user)
        except IntegrityError:
            token = ExpiringToken.objects.get(user=user)
    return token


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    phone = serializer.validated_data['phone']
    password = serializer.validated_data['password']

    # 账号锁定检查（防止单账号被暴力破解）
    locked = check_account_locked(phone)
    if locked:
        return locked

    user = authenticate(request, phone=phone, password=password)
    if user is None:
        record_login_failure(phone)
        return Response({'detail': '手机号或密码错误'}, status=401)
    if user.status != 'active':
        return Response({'detail': '账号已停用'}, status=403)
    # 成功登录清零失败计数
    clear_login_failures(phone)
    token = get_or_create_token(user)
    user_serializer = UserSerializer(user)
    return Response({
        'token': token.key,
        'user': user_serializer.data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        request.user.auth_token.delete()
    except ObjectDoesNotExist:
        pass
    return Response({'detail': 'ok'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@audit_log(action='change_password', resource_type='User', description_template='修改密码')
def change_password_view(request):
    user = request.user
    # CamelCaseJSONParser 会把前端发送的 oldPassword/newPassword 转成 snake_case
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    if not old_password or not new_password:
        return Response({'detail': '请填写旧密码和新密码'}, status=400)
    if not user.check_password(old_password):
        return Response({'detail': '原密码错误'}, status=400)
    try:
        password_validation.validate_password(new_password, user=user)
    except Exception as e:
        messages = getattr(e, 'messages', None) or [str(e)]
        return Response(
            {'detail': '；'.join(str(m) for m in messages)},
            status=400,
        )

    user.set_password(new_password)
    user.save()

    # Rotate token: delete old, create new
    try:
        user.auth_token.delete()
    except ObjectDoesNotExist:
        pass
    token = ExpiringToken.objects.create(user=user)

    return Response({
        'detail': 'ok',
        'token': token.key,
    })

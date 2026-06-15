from django.contrib.auth import authenticate
from django.db import IntegrityError
from rest_framework.authtoken.models import Token as BaseToken
from rest_framework.decorators import api_view, permission_classes, throttle_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from apps.users.serializers import UserSerializer
from apps.authentication.serializers import LoginSerializer
from apps.authentication.models import ExpiringToken
from apps.authentication.throttling import LoginRateThrottle
from apps.audit.decorators import audit_log


def get_or_create_token(user):
    """获取或刷新 ExpiringToken。

    - 多表继承下，旧代码可能在基础表 authtoken_token 留下没有子表行的孤儿 token，
      导致 ExpiringToken.get_or_create 撞唯一约束；这里先取子表，取不到则清理孤儿再创建。
    - 已存在但过期的 token 必须刷新（换新 key + 重置过期时间），否则登录秒退。
    - 并发登录兜底 IntegrityError。
    """
    try:
        token = ExpiringToken.objects.get(user=user)
    except ExpiringToken.DoesNotExist:
        BaseToken.objects.filter(user=user).delete()
        try:
            return ExpiringToken.objects.create(user=user)
        except IntegrityError:
            token = ExpiringToken.objects.get(user=user)

    if token.is_expired:
        token.key = token.generate_key()
        token.expires_at = None  # save() 会重置为 now + TOKEN_EXPIRATION_DAYS
        token.save()
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

    user = authenticate(request, phone=phone, password=password)
    if user is None:
        return Response({'detail': '手机号或密码错误'}, status=401)
    if user.status != 'active':
        return Response({'detail': '账号已停用'}, status=403)
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
    except Exception:
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
    old_password = request.data.get('oldPassword')
    new_password = request.data.get('newPassword')
    if not old_password or not new_password:
        return Response({'detail': '请填写旧密码和新密码'}, status=400)
    if not user.check_password(old_password):
        return Response({'detail': '原密码错误'}, status=400)
    user.set_password(new_password)
    user.save()

    # Rotate token: delete old, create new
    try:
        user.auth_token.delete()
    except Exception:
        pass
    token = ExpiringToken.objects.create(user=user)

    return Response({
        'detail': 'ok',
        'token': token.key,
    })

from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from apps.users.serializers import UserSerializer
from apps.authentication.serializers import LoginSerializer
from apps.authentication.models import ExpiringToken
from apps.authentication.throttling import LoginRateThrottle
from apps.audit.decorators import audit_log


@api_view(['POST'])
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
    token, _ = ExpiringToken.objects.get_or_create(user=user)
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

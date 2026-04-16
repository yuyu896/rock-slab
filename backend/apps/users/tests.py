from django.test import TestCase
from rest_framework.test import APIClient
from .models import User


class SystemAvatarTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone='13800000001', name='管理员', password='test123', role='admin'
        )
        self.staff = User.objects.create_user(
            phone='13800000002', name='普通员工', password='test123', role='staff'
        )
        self.client = APIClient()

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_set_system_avatar_success(self):
        """正常设置系统预设头像"""
        self._login(self.staff)
        resp = self.client.post(
            f'/api/users/{self.staff.id}/system-avatar',
            {'system_avatar': 'geo-1'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.system_avatar, 'geo-1')

    def test_set_system_avatar_invalid_key(self):
        """无效标识符应返回 400"""
        self._login(self.staff)
        resp = self.client.post(
            f'/api/users/{self.staff.id}/system-avatar',
            {'system_avatar': 'invalid-key'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_set_system_avatar_clears_custom(self):
        """设置预设头像应清除自定义头像文件"""
        self._login(self.staff)
        # 模拟已有自定义头像（通过数据库直接设置，不测试上传逻辑）
        # 创建一个假的头像文件
        from django.core.files.base import ContentFile
        self.staff.avatar.save('test_avatar.jpg', ContentFile(b'\xff\xd8\xff\xe0'), save=True)
        self.assertIsNotNone(self.staff.avatar)

        # 设置系统头像时应清除自定义头像
        resp = self.client.post(
            f'/api/users/{self.staff.id}/system-avatar',
            {'system_avatar': 'geo-1'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.staff.refresh_from_db()
        # 检查 avatar 是否被清除（ImageFieldFile 可能不是 None，检查 name 属性）
        self.assertFalse(self.staff.avatar.name)
        self.assertEqual(self.staff.system_avatar, 'geo-1')

    def test_set_system_avatar_forbidden(self):
        """非本人非管理员无权操作"""
        self._login(self.staff)
        resp = self.client.post(
            f'/api/users/{self.admin.id}/system-avatar',
            {'system_avatar': 'geo-1'},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_system_avatar_choices_constant(self):
        """验证 SYSTEM_AVATAR_CHOICES 生成正确的值"""
        expected = [f'geo-{i}' for i in range(1, 11)]
        self.assertEqual(User.SYSTEM_AVATAR_CHOICES, expected)

    def test_set_system_avatar_boundary_values(self):
        """测试边界值 geo-1 和 geo-10"""
        self._login(self.staff)
        for key in ('geo-1', 'geo-10'):
            resp = self.client.post(
                f'/api/users/{self.staff.id}/system-avatar',
                {'system_avatar': key},
                format='json',
            )
            self.assertEqual(resp.status_code, 200)

    def test_set_system_avatar_out_of_range(self):
        """测试超出范围的值 geo-0 和 geo-11"""
        self._login(self.staff)
        for key in ('geo-0', 'geo-11'):
            resp = self.client.post(
                f'/api/users/{self.staff.id}/system-avatar',
                {'system_avatar': key},
                format='json',
            )
            self.assertEqual(resp.status_code, 400)

    def test_admin_can_set_others_system_avatar(self):
        """管理员可以为他人设置预设头像"""
        self._login(self.admin)
        resp = self.client.post(
            f'/api/users/{self.staff.id}/system-avatar',
            {'system_avatar': 'geo-5'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.system_avatar, 'geo-5')

    def test_serializer_includes_system_avatar(self):
        """序列化器应包含 system_avatar 字段"""
        self._login(self.admin)
        self.staff.system_avatar = 'geo-7'
        self.staff.save()
        resp = self.client.get(f'/api/users/{self.staff.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['system_avatar'], 'geo-7')

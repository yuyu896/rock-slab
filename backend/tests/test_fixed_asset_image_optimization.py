from io import BytesIO, StringIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from conftest import _client_for
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory, override_settings
from PIL import Image

from apps.assets.models import FixedAsset
from apps.assets.serializers import FixedAssetSerializer
from apps.categories.models import Category
from apps.permissions.models import OperationGrant


@pytest.fixture
def image_instance(branch):
    item = Category.objects.create(
        asset_category='固定',
        item_category='办公',
        asset_name=f'缩略图测试-{uuid4().hex[:8]}',
        asset_code=f'IMG-{uuid4().hex[:8]}',
        unit='台',
        management_type='instance',
    )
    return FixedAsset.objects.create(
        item=item,
        内部编号=f'IMG-{uuid4().hex}',
        当前状态='在库',
        branch=branch,
    )


def _grant_image_edit(user):
    OperationGrant.objects.get_or_create(user=user, code='manage_instances')


def _image_upload(width=3000, height=1500, name='photo.jpg'):
    output = BytesIO()
    Image.new('RGB', (width, height), (35, 90, 145)).save(output, format='JPEG')
    return SimpleUploadedFile(name, output.getvalue(), content_type='image/jpeg')


class TestFixedAssetImageOptimization:
    @pytest.fixture(autouse=True)
    def isolate_media_root(self, tmp_path):
        with override_settings(MEDIA_ROOT=tmp_path):
            yield

    def test_upload_creates_versioned_webp_main_and_thumbnail(
        self, supervisor_user, image_instance,
    ):
        _grant_image_edit(supervisor_user)
        response = _client_for(supervisor_user).post(
            f'/api/assets/fixed-assets/{image_instance.pk}/image',
            {'image': _image_upload()},
        )

        assert response.status_code == 200
        assert response.data['图片'].endswith('?v=1')
        assert response.data['缩略图'].endswith('?v=1')
        image_instance.refresh_from_db()
        assert image_instance.image_version == 1
        assert image_instance.image.name.endswith('.webp')
        assert image_instance.thumbnail.name.endswith('.webp')
        with default_storage.open(image_instance.image.name, 'rb') as stored:
            with Image.open(stored) as main:
                assert main.format == 'WEBP'
                assert main.size == (2048, 1024)
        with default_storage.open(image_instance.thumbnail.name, 'rb') as stored:
            with Image.open(stored) as thumbnail:
                assert thumbnail.format == 'WEBP'
                assert thumbnail.size == (240, 120)

    @pytest.mark.django_db(transaction=True)
    def test_replacement_and_delete_keep_the_pair_and_advance_version(
        self, supervisor_user, image_instance,
    ):
        _grant_image_edit(supervisor_user)
        client = _client_for(supervisor_user)
        endpoint = f'/api/assets/fixed-assets/{image_instance.pk}/image'

        first = client.post(endpoint, {'image': _image_upload(name='same.jpg')})
        assert first.status_code == 200
        image_instance.refresh_from_db()
        old_names = (image_instance.image.name, image_instance.thumbnail.name)

        second = client.post(endpoint, {'image': _image_upload(name='same.jpg')})
        assert second.status_code == 200
        image_instance.refresh_from_db()
        assert image_instance.image_version == 2
        assert all(not default_storage.exists(name) for name in old_names)
        assert second.data['图片'].endswith('?v=2')
        assert second.data['缩略图'].endswith('?v=2')
        image_instance.refresh_from_db()
        latest_names = (image_instance.image.name, image_instance.thumbnail.name)

        deleted = client.delete(endpoint)
        assert deleted.status_code == 200
        image_instance.refresh_from_db()
        assert image_instance.image_version == 3
        assert not image_instance.image
        assert not image_instance.thumbnail
        assert all(not default_storage.exists(name) for name in latest_names)

    def test_database_failure_preserves_old_pair_and_removes_new_files(
        self, supervisor_user, image_instance, monkeypatch,
    ):
        _grant_image_edit(supervisor_user)
        client = _client_for(supervisor_user)
        endpoint = f'/api/assets/fixed-assets/{image_instance.pk}/image'
        assert client.post(endpoint, {'image': _image_upload(name='old.jpg')}).status_code == 200
        image_instance.refresh_from_db()
        old_names = (image_instance.image.name, image_instance.thumbnail.name)
        old_version = image_instance.image_version

        storage = image_instance._meta.get_field('image').storage
        original_storage_save = storage.save
        new_names = []

        def track_save(name, content, max_length=None):
            saved_name = original_storage_save(name, content, max_length=max_length)
            new_names.append(saved_name)
            return saved_name

        original_model_save = FixedAsset.save

        def fail_pair_update(self, *args, **kwargs):
            if 'image_version' in (kwargs.get('update_fields') or ()):
                raise RuntimeError('simulated database failure')
            return original_model_save(self, *args, **kwargs)

        monkeypatch.setattr(storage, 'save', track_save)
        monkeypatch.setattr(FixedAsset, 'save', fail_pair_update)
        client.raise_request_exception = False
        response = client.post(endpoint, {'image': _image_upload(name='new.jpg')})

        assert response.status_code == 500
        image_instance.refresh_from_db()
        assert (image_instance.image.name, image_instance.thumbnail.name) == old_names
        assert image_instance.image_version == old_version
        assert all(default_storage.exists(name) for name in old_names)
        assert len(new_names) == 2
        assert all(not default_storage.exists(name) for name in new_names)

    def test_backfill_preview_is_read_only_and_execute_is_idempotent(self, image_instance):
        image = _image_upload(width=640, height=480)
        original_bytes = image.read()
        image_name = default_storage.save(
            f'fixed_assets/{image_instance.pk}/legacy.jpg',
            ContentFile(original_bytes, name='legacy.jpg'),
        )
        image_instance.image = image_name
        image_instance.image_version = 7
        image_instance.save(update_fields=['image', 'image_version'])

        preview = StringIO()
        call_command('backfill_fixed_asset_thumbnails', stdout=preview)
        image_instance.refresh_from_db()
        assert not image_instance.thumbnail
        assert image_instance.image.name == image_name
        assert image_instance.image_version == 7
        with default_storage.open(image_name, 'rb') as stored:
            assert stored.read() == original_bytes

        call_command('backfill_fixed_asset_thumbnails', execute=True, stdout=StringIO())
        image_instance.refresh_from_db()
        thumbnail_name = image_instance.thumbnail.name
        assert thumbnail_name.endswith('.webp')
        assert image_instance.image.name == image_name
        assert image_instance.image_version == 7

        call_command('backfill_fixed_asset_thumbnails', execute=True, stdout=StringIO())
        image_instance.refresh_from_db()
        assert image_instance.thumbnail.name == thumbnail_name
        assert len(default_storage.listdir(f'fixed_assets/{image_instance.pk}')[1]) == 2


@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
def test_main_and_thumbnail_absolute_urls_use_forwarded_https_scheme():
    request = RequestFactory().get(
        '/api/assets/fixed-assets/',
        HTTP_HOST='qhpanpan.top',
        HTTP_X_FORWARDED_PROTO='https',
    )
    instance = SimpleNamespace(
        image=SimpleNamespace(url='/media/fixed_assets/main.webp'),
        thumbnail=SimpleNamespace(url='/media/fixed_assets/thumb.webp'),
        image_version=7,
    )
    serializer = FixedAssetSerializer(context={'request': request})

    assert serializer.get_图片(instance) == (
        'https://qhpanpan.top/media/fixed_assets/main.webp?v=7'
    )
    assert serializer.get_缩略图(instance) == (
        'https://qhpanpan.top/media/fixed_assets/thumb.webp?v=7'
    )

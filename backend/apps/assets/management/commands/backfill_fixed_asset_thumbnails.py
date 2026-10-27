from uuid import UUID

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import FixedAsset
from apps.assets.services.image_processing import create_thumbnail


class Command(BaseCommand):
    help = 'Preview or generate missing fixed-asset image thumbnails.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute', action='store_true',
            help='Write generated thumbnails. Without this flag the command is read-only.',
        )
        parser.add_argument(
            '--batch-size', type=int, default=200,
            help='Number of asset records fetched per query batch.',
        )
        parser.add_argument(
            '--limit', type=int, default=None,
            help='Maximum records to scan in this invocation.',
        )
        parser.add_argument(
            '--after-id', default=None,
            help='Resume after this asset UUID when processing another batch.',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        limit = options['limit']
        if batch_size < 1:
            raise CommandError('--batch-size must be greater than zero')
        if limit is not None and limit < 1:
            raise CommandError('--limit must be greater than zero')

        after_id = options['after_id']
        if after_id:
            try:
                after_id = UUID(after_id)
            except (ValueError, TypeError, AttributeError) as exc:
                raise CommandError('--after-id must be a valid asset UUID') from exc

        queryset = FixedAsset.objects.only('pk', 'image', 'thumbnail').order_by('pk')

        preview = not options['execute']
        counts = {'pending': 0, 'skipped': 0, 'success': 0, 'failed': 0}
        scanned = 0
        cursor = after_id
        while limit is None or scanned < limit:
            batch_query = queryset
            if cursor:
                batch_query = batch_query.filter(pk__gt=cursor)
            batch_limit = batch_size if limit is None else min(batch_size, limit - scanned)
            records = list(batch_query[:batch_limit])
            if not records:
                break

            for record in records:
                scanned += 1
                if not record.image or record.thumbnail:
                    counts['skipped'] += 1
                    continue

                try:
                    if preview:
                        storage = record._meta.get_field('image').storage
                        with storage.open(record.image.name, 'rb') as source:
                            create_thumbnail(source)
                        counts['pending'] += 1
                    elif self._generate_for_asset(record.pk):
                        counts['success'] += 1
                    else:
                        counts['skipped'] += 1
                except Exception as exc:
                    counts['failed'] += 1
                    self.stderr.write(f'{record.pk}: {exc}')

            cursor = records[-1].pk

        mode = '预览' if preview else '执行'
        self.stdout.write(
            f'{mode}完成：扫描={scanned}，待处理={counts["pending"]}，'
            f'跳过={counts["skipped"]}，成功={counts["success"]}，失败={counts["failed"]}，'
            f'最后ID={cursor or "-"}'
        )

    @staticmethod
    def _generate_for_asset(asset_id):
        saved_name = None
        storage = None
        candidate_name = None
        try:
            with transaction.atomic():
                instance = FixedAsset.objects.select_for_update().only(
                    'pk', 'image', 'thumbnail',
                ).get(pk=asset_id)
                if not instance.image or instance.thumbnail:
                    return False

                image_field = instance._meta.get_field('image')
                thumbnail_field = instance._meta.get_field('thumbnail')
                storage = thumbnail_field.storage
                with image_field.storage.open(instance.image.name, 'rb') as source:
                    thumbnail_bytes = create_thumbnail(source)

                candidate_name = thumbnail_field.generate_filename(
                    instance, 'thumbnail.webp',
                )
                saved_name = storage.save(
                    candidate_name,
                    ContentFile(thumbnail_bytes, name='thumbnail.webp'),
                )
                instance.thumbnail = saved_name
                instance.save(update_fields=['thumbnail'])
            return True
        except Exception:
            if storage is not None:
                for name in {saved_name, candidate_name} - {None}:
                    try:
                        storage.delete(name)
                    except Exception:
                        pass
            raise

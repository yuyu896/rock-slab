"""按员工 team 众数回填分公司 team。

用于 unified-organization-page 上线后的数据修复：原有分公司 team=null，
根据其员工的 team 推断归属。仅回填 team 为空的分公司。
"""
from collections import Counter

from django.core.management.base import BaseCommand

from apps.organizations.models import Branch, Team
from apps.users.models import User


class Command(BaseCommand):
    help = '根据员工的 team 众数回填分公司的 team（仅回填 team 为空的分公司）'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='仅预览，不写库')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        teams = {t.id: t.name for t in Team.objects.all()}
        assigned = 0
        skipped = 0

        for branch in Branch.objects.all():
            if branch.team_id:
                skipped += 1
                continue
            team_ids = list(
                User.objects.filter(branch=branch, team__isnull=False)
                .values_list('team_id', flat=True)
            )
            if not team_ids:
                self.stdout.write(f'  跳过 {branch.name}（{branch.code}）：员工无 team')
                skipped += 1
                continue
            top_team_id, top_count = Counter(team_ids).most_common(1)[0]
            team_label = teams.get(top_team_id, str(top_team_id))
            if dry_run:
                self.stdout.write(
                    f'  [DRY-RUN] {branch.name}（{branch.code}）→ {team_label}（{top_count} 票）'
                )
            else:
                branch.team_id = top_team_id
                branch.save(update_fields=['team', 'updated_at'])
                self.stdout.write(
                    f'  已回填 {branch.name}（{branch.code}）→ {team_label}（{top_count} 票）'
                )
            assigned += 1

        self.stdout.write(self.style.SUCCESS(
            f'完成：回填 {assigned} 个分公司，跳过 {skipped} 个（dry-run={dry_run}）'
        ))

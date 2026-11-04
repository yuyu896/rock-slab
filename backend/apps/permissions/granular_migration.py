"""Preview, apply, and recover the legacy permission-code migration.

The migration deliberately maps only stored OperationGrant rows. It never
consults position templates to create permissions.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.contrib.auth import get_user_model

from .models import ManagementScope, OperationGrant
from .operations import OPERATION_CATALOG, OPERATION_PREREQUISITES


PLAN_SCHEMA = 'granular-permission-plan-v1'
SNAPSHOT_SCHEMA = 'granular-permission-snapshot-v1'
MAPPING_VERSION = '2026-10-30.1'

# Mappings are one-to-one or expand an old broad permission only into the
# specific operations it already represented. Ambiguous legacy codes remain
# untouched and are reported for manual review.
LEGACY_PERMISSION_MAP = {
    'view_audit': {
        'targets': ('view_audit_logs',),
        'reason': '查看审计日志语义对应新目录的审计日志查看权限。',
    },
    'manage_users': {
        'targets': ('view_users', 'edit_users'),
        'reason': '旧码代表员工账号完整维护权限，映射到查看和合并后的编辑员工账号。',
    },
    'manage_organizations': {
        'targets': (
            'view_organizations', 'edit_organizations', 'delete_organizations',
        ),
        'unmapped_targets': (
            'view_departments', 'edit_departments',
        ),
        'reason': '旧码允许维护组织节点及部门；部门旧接口按账号数据范围过滤，而新部门字典为全集团范围，部门权限须逐人核对。',
    },
    'manage_departments': {
        'targets': ('view_departments', 'edit_departments'),
        'reason': '旧码代表部门字典完整维护权限，映射到查看和合并后的编辑部门。',
    },
    'manage_suppliers': {
        'targets': ('view_suppliers', 'edit_suppliers'),
        'reason': '旧码代表供应商字典完整维护权限，映射到查看和合并后的编辑供应商字典。',
    },
    'manage_categories': {
        'targets': ('view_categories', 'edit_categories'),
        'reason': '旧码代表品目完整维护权限，映射到查看和合并后的编辑品目。',
    },
    'manage_dictionary': {
        'targets': ('view_categories', 'edit_categories'),
        'reason': '历史迁移已将 manage_categories 原样改名为 manage_dictionary，仍对应品目完整维护。',
    },
    'approve_inventory': {
        'targets': ('review_inventory',),
        'reason': '盘点审批权限在新目录中改名为审批盘点任务。',
    },
    'view_all_notifications': {
        'targets': ('view_approval_reports',),
        'reason': '旧码用于查看审批抄送记录，对应审批报告只读权限。',
    },
}

UNMAPPABLE_REASONS = {
    'approve_transfer': '旧通用审批权无法确定每个账号应审批的单据类型，需逐人核对；不会自动授予任何新审批权限。',
    'manage_assets': (
        '旧权限同时控制台账导入、盘点写操作、采购/领用/调拨批量导入和调拨拒收；'
        '部分历史资产写入及即时回收入口已退役。新目录按模块细分，需逐人核对；不会自动授予新权限。'
    ),
    'manage_instances': (
        '旧权限曾控制实例资料和图片维护，以及直接更换使用人和部门；'
        '不代表完整档案查看、导出或打印权限。需逐账号核对后设置新权限；不会自动授予任何新权限。'
    ),
    'adjust_ledger': (
        '旧权限用于手工创建台账调整单，历史台账导入流程也接受该权限；'
        '新目录已拆分导入和手工调整，需逐账号核对；不会自动授予任一新权限。'
    ),
    'dispose_assets': '旧处置权限已并入回收单生命周期；需逐人核对，不自动授予创建、提交或审批回收单权限。',
}


def _json_value(value):
    if isinstance(value, (UUID, datetime, date, Decimal)):
        return str(value)
    return value


def _canonical_json(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
        default=_json_value,
    )


def _digest(value):
    return hashlib.sha256(_canonical_json(value).encode('utf-8')).hexdigest()


def _authorization_rows():
    grants = list(OperationGrant.objects.order_by('user_id', 'code', 'id').values(
        'id', 'user_id', 'code', 'created_at', 'updated_at',
    ))
    scopes = list(ManagementScope.objects.order_by('user_id', 'id').values(
        'id', 'user_id', 'is_all_data', 'region_id', 'team_id', 'branch_id',
        'created_at', 'updated_at',
    ))
    return {
        'grants': [{k: _json_value(v) for k, v in row.items()} for row in grants],
        'scopes': [{k: _json_value(v) for k, v in row.items()} for row in scopes],
    }


def _source_state():
    User = get_user_model()
    users = list(User.objects.order_by('id').values(
        'id', 'name', 'phone', 'role', 'status', 'branch_id',
    ))
    Region = User._meta.apps.get_model('organizations', 'Region')
    Team = User._meta.apps.get_model('organizations', 'Team')
    Branch = User._meta.apps.get_model('organizations', 'Branch')
    regions = list(Region.objects.order_by('id').values('id', 'name', 'manager_id'))
    teams = list(Team.objects.order_by('id').values('id', 'name', 'region_id', 'leader_id'))
    branches = list(Branch.objects.order_by('id').values('id', 'name', 'code', 'team_id', 'manager_id'))
    return {
        'users': [{k: _json_value(v) for k, v in row.items()} for row in users],
        'authorization': _authorization_rows(),
        'regions': [{k: _json_value(v) for k, v in row.items()} for row in regions],
        'teams': [{k: _json_value(v) for k, v in row.items()} for row in teams],
        'branches': [{k: _json_value(v) for k, v in row.items()} for row in branches],
    }


def _expand_nodes(scope_rows, appointment_nodes, topology):
    if any(row['is_all_data'] for row in scope_rows):
        return {'all': True, 'branches': []}

    regions = {row['region_id'] for row in scope_rows if row['region_id']}
    teams = {row['team_id'] for row in scope_rows if row['team_id']}
    branches = {row['branch_id'] for row in scope_rows if row['branch_id']}
    for node_type, node_id in appointment_nodes:
        if node_type == 'region':
            regions.add(node_id)
        elif node_type == 'team':
            teams.add(node_id)
        elif node_type == 'branch':
            branches.add(node_id)

    team_region = {row['id']: row['region_id'] for row in topology['teams']}
    for branch in topology['branches']:
        if branch['team_id'] in teams or team_region.get(branch['team_id']) in regions:
            branches.add(branch['id'])

    branch_names = {row['id']: row['name'] for row in topology['branches']}
    ordered = sorted(branches, key=lambda branch_id: (branch_names.get(branch_id, ''), str(branch_id)))
    return {
        'all': False,
        'branches': [
            {'id': str(branch_id), 'name': branch_names.get(branch_id, '（组织节点不存在）')}
            for branch_id in ordered
        ],
    }


def _appointment_scope_row(user_id, appointment):
    row = {
        'user_id': user_id,
        'is_all_data': False,
        'region_id': None,
        'team_id': None,
        'branch_id': None,
    }
    row[f"{appointment['type']}_id"] = appointment['id']
    return row


def _scope_node_matches(row, appointment):
    if row['is_all_data']:
        return False
    node_field = f"{appointment['type']}_id"
    return row[node_field] == appointment['id']


def _scope_report(user, scope_rows, topology):
    if user['role'] == 'admin':
        all_scope = {'all': True, 'branches': []}
        redundant_rows = sum(row['user_id'] == user['id'] for row in scope_rows)
        return {
            'before': all_scope,
            'after': all_scope,
            'appointment_scopes_to_preserve': [],
            'unclassified_records': [],
            'redundant_rows_to_remove': redundant_rows,
        }

    appointment_nodes = []
    appointment_report = []
    for row in topology['regions']:
        if row['manager_id'] == user['id']:
            appointment_nodes.append(('region', row['id']))
            appointment_report.append({'type': 'region', 'id': str(row['id']), 'name': row['name']})
    for row in topology['teams']:
        if row['leader_id'] == user['id']:
            appointment_nodes.append(('team', row['id']))
            appointment_report.append({'type': 'team', 'id': str(row['id']), 'name': row['name']})
    for row in topology['branches']:
        if row['manager_id'] == user['id']:
            appointment_nodes.append(('branch', row['id']))
            appointment_report.append({'type': 'branch', 'id': str(row['id']), 'name': row['name']})

    owned_scopes = [row for row in scope_rows if row['user_id'] == user['id']]
    has_all_data_scope = any(row['is_all_data'] for row in owned_scopes)
    appointment_scope_rows = [] if has_all_data_scope else [
        _appointment_scope_row(user['id'], appointment)
        for appointment in appointment_report
    ]
    before = _expand_nodes(owned_scopes, appointment_nodes, topology)
    if owned_scopes or appointment_scope_rows:
        after = _expand_nodes(owned_scopes + appointment_scope_rows, [], topology)
    elif user['branch_id']:
        branch_names = {row['id']: row['name'] for row in topology['branches']}
        after = {
            'all': False,
            'branches': [{
                'id': str(user['branch_id']),
                'name': branch_names.get(user['branch_id'], '（组织节点不存在）'),
            }],
        }
    else:
        after = {'all': False, 'branches': []}

    branch_names = {row['id']: row['name'] for row in topology['branches']}
    unclassified = []
    for row in owned_scopes:
        node = '全部组织' if row['is_all_data'] else None
        if row['region_id']:
            node = next((r['name'] for r in topology['regions'] if r['id'] == row['region_id']), '未知大区')
            node = f'大区：{node}'
        elif row['team_id']:
            node = next((t['name'] for t in topology['teams'] if t['id'] == row['team_id']), '未知行政组')
            node = f'行政组：{node}'
        elif row['branch_id']:
            node = f'分公司：{branch_names.get(row["branch_id"], "未知分公司")}'
        unclassified.append({
            'scope_id': str(row['id']),
            'user_id': str(user['id']),
            'name': user['name'],
            'phone': user['phone'],
            'node': node,
            'data_range': _expand_nodes([row], [], topology),
            'also_current_appointment_scope': any(
                _scope_node_matches(row, appointment)
                for appointment in appointment_report
            ),
            'provenance': '无法从当前模型判断是人工配置还是历史岗位迁移写入',
        })
    return {
        'before': before,
        'after': after,
        'appointment_scopes_to_preserve': [] if has_all_data_scope else [
            {
                **appointment,
                'already_explicit': any(
                    _scope_node_matches(row, appointment)
                    for row in owned_scopes
                ),
            }
            for appointment in appointment_report
        ],
        'unclassified_records': unclassified,
    }


def _grant_mapping(code, catalog_codes):
    if code in UNMAPPABLE_REASONS:
        return {
            'state': 'unmapped', 'targets': [], 'unmapped_targets': [],
            'reason': UNMAPPABLE_REASONS[code],
        }
    if code in catalog_codes:
        return {
            'state': 'current', 'targets': [code], 'unmapped_targets': [],
            'reason': '该权限码已属于新目录，无需转换。',
        }
    mapping = LEGACY_PERMISSION_MAP.get(code)
    if mapping:
        targets = list(mapping['targets'])
        unmapped_targets = list(mapping.get('unmapped_targets', ()))
        selected_targets = set(targets) | set(unmapped_targets)
        for target in targets:
            unmapped_targets.extend(
                prerequisite
                for prerequisite in OPERATION_PREREQUISITES.get(target, ())
                if prerequisite not in selected_targets and prerequisite not in unmapped_targets
            )
        missing = sorted((set(targets) | set(unmapped_targets)) - catalog_codes)
        if missing:
            return {
                'state': 'unmapped', 'targets': [], 'unmapped_targets': [],
                'reason': f'目标权限尚未登记：{", ".join(missing)}',
            }
        return {
            'state': 'partially_mapped' if unmapped_targets else 'mapped',
            'targets': targets, 'unmapped_targets': unmapped_targets,
            'reason': mapping['reason'],
        }
    return {
        'state': 'unmapped', 'targets': [], 'unmapped_targets': [],
        'reason': UNMAPPABLE_REASONS.get(code, '旧权限码无已审核映射，需人工复核。'),
    }


def build_migration_plan():
    """Build a deterministic read-only migration plan from stored grants."""
    state = _source_state()
    users = state['users']
    raw_grants = state['authorization']['grants']
    scope_rows = state['authorization']['scopes']
    topology = {key: state[key] for key in ('regions', 'teams', 'branches')}
    grants_by_user = {}
    for grant in raw_grants:
        grants_by_user.setdefault(grant['user_id'], []).append(grant)
    catalog_codes = {item['code'] for item in OPERATION_CATALOG}

    accounts = []
    unresolved = []
    partially_mapped = []
    mapped_count = 0
    partially_mapped_count = 0
    for user in users:
        current = grants_by_user.get(user['id'], [])
        mapping_rows = []
        effective_after = set()
        unmapped_codes = []
        for grant in current:
            if user['role'] == 'admin':
                mapping = {
                    'state': 'admin_builtin', 'targets': [], 'unmapped_targets': [],
                    'reason': '系统管理员自动拥有全部业务权限；该冗余存储授权行会在应用迁移时删除。',
                }
            else:
                mapping = _grant_mapping(grant['code'], catalog_codes)
                effective_after.update(mapping['targets'])
            row = {
                'grant_id': grant['id'],
                'from': grant['code'],
                'to': mapping['targets'],
                'unmapped_targets': mapping['unmapped_targets'],
                'state': mapping['state'],
                'reason': mapping['reason'],
            }
            mapping_rows.append(row)
            if mapping['state'] == 'mapped':
                mapped_count += 1
            elif mapping['state'] == 'partially_mapped':
                partially_mapped_count += 1
                partial = {'user_id': user['id'], **row}
                partially_mapped.append(partial)
                unmapped_codes.append(grant['code'])
            elif mapping['state'] == 'unmapped':
                unmapped = {'user_id': user['id'], **row}
                unresolved.append(unmapped)
                unmapped_codes.append(grant['code'])

        accounts.append({
            'user_id': user['id'],
            'name': user['name'],
            'phone': user['phone'],
            'role': user['role'],  # Review context only; never used to derive grants.
            'status': user['status'],
            'branch': user['branch_id'],
            'automatic_admin_all': user['role'] == 'admin',
            'before_grants': sorted(grant['code'] for grant in current),
            'after_grants': ['全部（系统管理员内置）'] if user['role'] == 'admin' else sorted(effective_after),
            'unmapped_codes_retained': sorted(set(unmapped_codes)),
            'grant_mappings': mapping_rows,
            'scope': _scope_report(user, scope_rows, topology),
        })

    source_digest = _digest(state)
    plan_id = _digest({'mapping_version': MAPPING_VERSION, 'source_digest': source_digest})[:24]
    return {
        'schema': PLAN_SCHEMA,
        'mapping_version': MAPPING_VERSION,
        'plan_id': plan_id,
        'source_digest': source_digest,
        'generated_at': datetime.now().astimezone().isoformat(timespec='seconds'),
        'provenance_warning': (
            '旧授权表不记录授权来源；历史迁移曾按岗位写入授权。本计划只读取已存授权行，'
            '绝不按岗位或岗位模板补发权限。已确认的当前组织任命范围会转换为账号显式数据范围；'
            '其他管理范围记录同样没有来源标记。'
        ),
        'summary': {
            'account_count': len(accounts),
            'stored_grant_count': len(raw_grants),
            'mapped_grant_count': mapped_count,
            'partially_mapped_grant_count': partially_mapped_count,
            'unmapped_grant_count': len(unresolved),
            'pending_review_grant_count': len(unresolved) + len(partially_mapped),
            'unclassified_scope_count': sum(len(a['scope']['unclassified_records']) for a in accounts),
            'appointment_scope_count': sum(
                len(a['scope']['appointment_scopes_to_preserve']) for a in accounts
            ),
            'accounts_with_appointment_scope': sum(
                bool(a['scope']['appointment_scopes_to_preserve']) for a in accounts
            ),
        },
        'accounts': accounts,
        'partially_mapped_grants': partially_mapped,
        'unmapped_grants': unresolved,
    }


def authorization_digest():
    """Digest the effective stored grant/scope rows for apply and restore checks."""
    return authorization_digest_for_rows(_authorization_rows())


def authorization_digest_for_rows(rows):
    """Digest permissions, independent of grant row IDs and timestamps."""
    grants = sorted((row['user_id'], row['code']) for row in rows['grants'])
    scopes = [
        (
            row['user_id'], row['is_all_data'], row['region_id'],
            row['team_id'], row['branch_id'],
        )
        for row in rows['scopes']
    ]
    scopes.sort(key=lambda row: (
        row[0], row[1], row[2] or '', row[3] or '', row[4] or '',
    ))
    return _digest({'grants': grants, 'scopes': scopes})


def expected_authorization_digest(snapshot, plan, dropped_scope_ids=()):
    grants = {(row['user_id'], row['code']) for row in snapshot['authorization']['grants']}
    dropped_scope_ids = set(dropped_scope_ids)
    admin_user_ids = {
        account['user_id'] for account in plan['accounts'] if account['automatic_admin_all']
    }
    for account in plan['accounts']:
        if account['automatic_admin_all']:
            grants = {
                entry for entry in grants
                if entry[0] != account['user_id']
            }
            continue
        for mapping in account['grant_mappings']:
            if mapping['state'] not in ('mapped', 'partially_mapped'):
                continue
            if mapping['state'] == 'mapped':
                grants.discard((account['user_id'], mapping['from']))
            grants.update((account['user_id'], code) for code in mapping['to'])
    scopes = {
        (
            str(row['user_id']), row['is_all_data'], row['region_id'],
            row['team_id'], row['branch_id'],
        )
        for row in snapshot['authorization']['scopes']
        if row['id'] not in dropped_scope_ids
        and row['user_id'] not in admin_user_ids
    }
    for account in plan['accounts']:
        if account['automatic_admin_all']:
            continue
        for appointment in account['scope']['appointment_scopes_to_preserve']:
            row = _appointment_scope_row(account['user_id'], appointment)
            scopes.add((
                str(row['user_id']), row['is_all_data'], row['region_id'],
                row['team_id'], row['branch_id'],
            ))
    rows = {
        'grants': [{'user_id': user_id, 'code': code} for user_id, code in grants],
        'scopes': [
            {
                'user_id': user_id,
                'is_all_data': is_all_data,
                'region_id': region_id,
                'team_id': team_id,
                'branch_id': branch_id,
            }
            for user_id, is_all_data, region_id, team_id, branch_id in sorted(
                scopes,
                key=lambda row: (row[0], row[1], row[2] or '', row[3] or '', row[4] or ''),
            )
        ],
    }
    return authorization_digest_for_rows(rows)


def snapshot_payload(plan):
    auth = _authorization_rows()
    snapshot = {
        'schema': SNAPSHOT_SCHEMA,
        'snapshot_id': _digest({
            'plan_id': plan['plan_id'],
            'before_digest': authorization_digest_for_rows(auth),
            'created_at': datetime.now().astimezone().isoformat(timespec='seconds'),
        })[:24],
        'plan_id': plan['plan_id'],
        'mapping_version': MAPPING_VERSION,
        'created_at': datetime.now().astimezone().isoformat(timespec='seconds'),
        'source_digest': plan['source_digest'],
        'before_authorization_digest': authorization_digest_for_rows(auth),
        'expected_after_authorization_digest': None,
        'authorization': auth,
    }
    return snapshot


def seal_snapshot(snapshot):
    snapshot = dict(snapshot)
    snapshot.pop('snapshot_digest', None)
    snapshot['snapshot_digest'] = _digest(snapshot)
    return snapshot


def validate_snapshot(snapshot):
    if snapshot.get('schema') != SNAPSHOT_SCHEMA or not snapshot.get('snapshot_id'):
        return False
    authorization = snapshot.get('authorization')
    if not isinstance(authorization, dict):
        return False
    if authorization_digest_for_rows(authorization) != snapshot.get('before_authorization_digest'):
        return False
    expected = snapshot.get('snapshot_digest')
    payload = dict(snapshot)
    payload.pop('snapshot_digest', None)
    return bool(expected and expected == _digest(payload))


def restore_authorization(snapshot):
    """Replace grant/scope tables from a verified snapshot inside caller transaction."""
    from django.utils.dateparse import parse_datetime

    OperationGrant.objects.all().delete()
    ManagementScope.objects.all().delete()
    grant_rows = snapshot['authorization']['grants']
    scope_rows = snapshot['authorization']['scopes']
    grants = [OperationGrant(
        id=row['id'], user_id=row['user_id'], code=row['code'],
        created_at=parse_datetime(row['created_at']),
        updated_at=parse_datetime(row['updated_at']),
    ) for row in grant_rows]
    scopes = [ManagementScope(
        id=row['id'], user_id=row['user_id'], is_all_data=row['is_all_data'],
        region_id=row['region_id'], team_id=row['team_id'], branch_id=row['branch_id'],
        created_at=parse_datetime(row['created_at']),
        updated_at=parse_datetime(row['updated_at']),
    ) for row in scope_rows]
    OperationGrant.objects.bulk_create(grants)
    ManagementScope.objects.bulk_create(scopes)
    # auto_now fields are set during bulk_create; restore their snapshotted values.
    for row in grant_rows:
        OperationGrant.objects.filter(pk=row['id']).update(
            created_at=parse_datetime(row['created_at']),
            updated_at=parse_datetime(row['updated_at']),
        )
    for row in scope_rows:
        ManagementScope.objects.filter(pk=row['id']).update(
            created_at=parse_datetime(row['created_at']),
            updated_at=parse_datetime(row['updated_at']),
        )

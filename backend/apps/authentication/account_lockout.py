"""按手机号的登录失败计数与临时锁定（防单账号暴力破解）。

基于 Django cache（生产 Redis、开发/测试 locmem），无新依赖。
cache 后端故障时 fail-open（跳过限流），不阻断正常登录（可用性优先于限速）。
"""
from django.core.cache import cache
from rest_framework.response import Response

FAILURES_THRESHOLD = 10        # 窗口内失败次数阈值
FAILURES_WINDOW = 5 * 60       # 失败计数窗口（秒）
LOCKOUT_DURATION = 15 * 60     # 锁定时长（秒）

_FAIL_KEY = 'rock_slab:login_fail:{}'
_LOCK_KEY = 'rock_slab:login_lock:{}'


def is_account_locked(phone):
    """是否处于锁定窗口。cache 故障时 fail-open（视为未锁定）。"""
    try:
        return bool(cache.get(_LOCK_KEY.format(phone)))
    except Exception:
        return False


def check_account_locked(phone):
    """若账号已锁定则返回 403 Response，否则返回 None。"""
    if is_account_locked(phone):
        return Response(
            {'detail': f'账号已被临时锁定，请 {LOCKOUT_DURATION // 60} 分钟后再试'},
            status=403,
        )
    return None


def record_login_failure(phone):
    """记录一次失败；达阈值则锁定账号。cache 故障时 fail-open。"""
    try:
        key = _FAIL_KEY.format(phone)
        fails = (cache.get(key) or 0) + 1
        cache.set(key, fails, FAILURES_WINDOW)
        if fails >= FAILURES_THRESHOLD:
            cache.set(_LOCK_KEY.format(phone), True, LOCKOUT_DURATION)
    except Exception:
        pass


def clear_login_failures(phone):
    """成功登录后清零该账号的失败计数。"""
    try:
        cache.delete(_FAIL_KEY.format(phone))
    except Exception:
        pass

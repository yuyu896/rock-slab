"""组织架构相关工具：供批量导入做分公司存在性校验。"""
from .models import Branch


def get_branch_name_set():
    """返回所有分公司名称集合，供批量导入逐行做存在性校验（一次查询）。"""
    return set(Branch.objects.values_list('name', flat=True))


def get_branch_code_map():
    """返回 {分公司名称: 分公司编号} 映射，供导入按名称回填分公司编号（一次查询）。"""
    return dict(Branch.objects.values_list('name', 'code'))


def branch_validation_error(name, label='分公司', valid_names=None):
    """校验分公司名称；通过返回 None，不通过返回中文错误消息。

    - 空 → f'{label}为空，请填写'
    - 非空但不在 valid_names → f'{label}「{name}」不存在'
    """
    value = (str(name) if name is not None else '').strip()
    if not value:
        return f'{label}为空，请填写'
    if valid_names is not None and value not in valid_names:
        return f'{label}「{value}」不存在'
    return None

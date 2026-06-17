"""实验路由模块.

提供 A/B 测试实验的 API 端点，所有端点需要管理员权限。
"""

# 导入模块: from typing
from typing import Any

# 导入模块: from fastapi
from fastapi import APIRouter, HTTPException, status

# 导入模块: from app.models.user
from app.models.user import User
# 导入模块: from app.services.experiment
from app.services.experiment import experiment_service
# 导入模块: from app.types.analysis
from app.types.analysis import ExperimentResult
# 导入模块: from app.utils.auth
from app.utils.auth import current_user_dep


# 初始化变量 router
router = APIRouter(prefix="/api/experiment", tags=["experiment"])


# 应用装饰器: router.post
@router.post("/run", response_model=ExperimentResult)
async def run_new_experiment(
    # 函数 run_new_experiment 的初始化逻辑
    experiment_data: dict[str, Any],
    current_user: User = current_user_dep,
) -> ExperimentResult:
    """运行 A/B 实验（需要管理员权限）.

    Args:
        experiment_data: 实验配置字典，包含 experiment_type 和 params
        current_user: 当前已认证的用户

    Returns:
        ExperimentResult: 实验结果

    Raises:
        HTTPException 401: 用户未登录
        HTTPException 403: 用户非管理员角色
        HTTPException 400: 实验参数无效
    """
    experiment_type: str = experiment_data.get("experiment_type", "")
    # 条件判断：处理业务逻辑
    if not experiment_type:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_400_BAD_REQUEST,
            # 初始化变量 detail
            detail="缺少 experiment_type 字段",
        )
    params: dict[str, Any] = experiment_data.get("params", {})
    # 返回处理结果
    return await experiment_service.run_experiment(
        # 初始化变量 user
        user=current_user,
        # 初始化变量 experiment_type
        experiment_type=experiment_type,
        # 初始化变量 params
        params=params,
    )

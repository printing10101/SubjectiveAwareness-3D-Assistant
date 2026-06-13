"""实验路由模块.

提供 A/B 测试实验的 API 端点，所有端点需要管理员权限。
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.models.user import User
from app.services.experiment import experiment_service
from app.types.analysis import ExperimentResult
from app.utils.auth import current_user_dep


router = APIRouter(prefix="/api/experiment", tags=["experiment"])


@router.post("/run", response_model=ExperimentResult)
async def run_new_experiment(
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
    if not experiment_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少 experiment_type 字段",
        )
    params: dict[str, Any] = experiment_data.get("params", {})
    return await experiment_service.run_experiment(
        user=current_user,
        experiment_type=experiment_type,
        params=params,
    )

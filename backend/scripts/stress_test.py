#!/usr/bin/env python3
"""性能压力测试脚本.

使用 locust 框架对核心 API 接口进行并发测试。

功能：
1. 模拟 50 用户并发访问核心 API 接口
2. 测试持续运行 5 分钟
3. 生成包含以下指标的报告：
   - P50, P95, P99 响应延迟（毫秒）
   - 错误率（按错误类型分类）
   - 请求吞吐量（RPS）

使用方法:
    # 基本使用（使用默认配置）
    python -m backend.scripts.stress_test

    # 自定义参数
    python -m backend.scripts.stress_test --host http://localhost:8000 --users 50 --spawn-rate 5 --run-time 300

    # 生成 HTML 报告
    python -m backend.scripts.stress_test --html reports/stress_test_report.html

    # 无头模式（默认）
    python -m backend.scripts.stress_test --headless

    # 使用 CSV 输出
    python -m backend.scripts.stress_test --csv reports/stress_test
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: argparse
import argparse
# 导入模块: json
import json
# 导入模块: sys
import sys
# 导入模块: time
import time
# 导入模块: from datetime
from datetime import datetime
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import Any

# 导入模块: from locust
from locust import HttpUser, between, events, task
# 导入模块: from locust.env
from locust.env import Environment
# 导入模块: from locust.runners
from locust.runners import STATE_STOPPED, STATE_STOPPING
# 导入模块: from locust.stats
from locust.stats import print_stats
# 导入模块: from loguru
from loguru import logger


# 将 backend 目录加入 sys.path
BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]
# 条件判断：处理业务逻辑
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# ---------------------------------------------------------------------------
# 测试数据准备
# ---------------------------------------------------------------------------

# 初始化变量 SAMPLE_CASE_TEXT
SAMPLE_CASE_TEXT = """
被告人张三，男，1990年出生，汉族，初中文化，无业。2023年3月至2023年8月期间，
被告人张三明知他人利用信息网络实施电信网络诈骗犯罪，仍将其本人名下的3张银行卡
（工商银行、建设银行、农业银行各一张）提供给他人使用，并协助进行转账操作。

经查，上述3张银行卡共转入资金人民币150余万元，其中涉及电信网络诈骗案件被害人
李四、王五等人被骗资金共计人民币45万元。被告人张三从中获取非法利益人民币3000元。

2023年8月15日，被告人张三被公安机关抓获，到案后如实供述了上述犯罪事实。
"""

# 初始化变量 SAMPLE_CASE_TEXT_SHORT
SAMPLE_CASE_TEXT_SHORT = "被告人张三提供银行卡给他人使用，涉及诈骗资金。"

# 初始化变量 SAMPLE_CASE_TEXT_LONG
SAMPLE_CASE_TEXT_LONG = """
被告人李四，男，1985年出生，汉族，高中文化，个体经营者。2022年1月至2023年6月期间，
被告人李四在明知他人利用信息网络实施犯罪活动的情况下，仍为其提供支付结算帮助。

具体犯罪事实如下：
1. 2022年1月，被告人李四将其名下的2张银行卡提供给王五使用，获取好处费2000元。
2. 2022年6月，被告人李四介绍赵六提供3张银行卡，获取介绍费1500元。
3. 2023年1月至6月，被告人李四通过虚拟货币交易方式，为上游犯罪团伙转移资金共计
   人民币200余万元，获取非法利益共计人民币15000元。

经查明，上述银行卡及支付账户涉及电信网络诈骗、网络赌博等违法犯罪活动，流入资金
共计人民币500余万元，造成多名被害人经济损失。

被告人李四于2023年6月20日被公安机关抓获，到案后拒不供述犯罪事实，但在确凿证据
面前最终认罪。
"""


# ---------------------------------------------------------------------------
# Locust 用户行为定义
# ---------------------------------------------------------------------------


# 定义 APIUser 类
class APIUser(HttpUser):
    """模拟 API 用户行为."""

    # 请求间隔：0.5-2秒之间随机
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        """用户启动时的初始化操作."""
        self.token: str | None = None
        self.user_id: int | None = None
        # 记录日志信息
        logger.debug(f"用户启动: {self.host}")

    # 应用装饰器: task
    @task(3)
    def analyze_case(self) -> None:
        """测试案件分析接口（权重最高）."""
        # 随机选择不同长度的测试文本
        import random

        # 初始化变量 case_text
        case_text = random.choice([SAMPLE_CASE_TEXT_SHORT, SAMPLE_CASE_TEXT, SAMPLE_CASE_TEXT_LONG])

        # 初始化变量 payload
        payload = {
            "case_text": case_text,
            "mode": "auto",
        }

        # 初始化变量 headers
        headers = {"Content-Type": "appli        # 条件判断：处理业务逻辑
cation/json"}
        # 条件判断: 检查 self.token
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # 使用上下文管理器管理资源
        with self.client.post(
            "/api/analyze",
            # 初始化变量 json
            json=payload,
            # 初始化变量 headers
            headers=headers,
            # 初始化变量 catch_response
            catch_response=True,
            # 初始化变量 name
            name="/a            # 条件判断：处理业务逻辑
pi/analyze",
        ) as response:
            # 条件判断: 检查 response.status_code == 200
            if response.status_code == 200:
                response.success()
            # 条件判断: 检查 elresponse.status_code == 429
            elif response.status_code == 429:
                response.failure("Rate limited (429)")
            # 条件判断: 检查 elresponse.status_code == 502
            elif response.status_code == 502:
                response.failure("Service unavailable (502)")
            # 其他情况的默认处理
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    # 应用装饰器: task
    @task(2)
    def health_check(self) -> None:
        """测试健康检查接口."""
        # 使用上下文管理器管理资源
        with self.client.get            # 条件判断：处理业务逻辑
("/health", catch_response=True, name="/health") as response:
            # 条件判断: 检查 response.status_code == 200
            if response.status_code == 200:
                response.success()
            # 其他情况的默认处理
            else:
                response.failure(f"Health check failed: {response.status_code}")

    # 应用装饰器: task
    @task(1)
    def get_metrics(self) -> None:
        """测试监控指标接口."""
                # 条件判断：处理业务逻辑
    with self.client.get("/metrics", catch_response=True, name="/metrics") as response:
            # 条件判断: 检查 response.status_code == 200
            if response.status_code == 200:
                response.success()
            # 其他情况的默认处理
            else:
                response.failure(f"Metrics failed: {res        # 条件判断：处理业务逻辑
ponse.status_code}")

    # 应用装饰器: task
    @task(1)
    def list_cases(self) -> None:
        """测试案例列表接口."""
        # 初始化变量 headers
        headers = {}
        # 条件判断: 检查 self.token
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # 使用上下文管理器管理资源
        with self.client.get(
            "/api/cases?pa            # 条件判断：处理业务逻辑
ge=1&page_size=10",
            # 初始化变量 headers
            headers=headers,
            # 初始化变量 catch_response
            catch_response=True,
            # 初始化变量 name
            name="/api/cases",
        ) as response:
            # 条件判断: 检查 response.status_code in (200, 401)
            if response.status_code in (200, 401):
                response.success()
            # 其他情况的默认处理
            else:
                response.failure(f"List cases failed: {response.status_code}")


# ---------------------------------------------------------------------------
# 统计收集器
# ---------------------------------------------------------------------------


# 定义 StatsCollector 类
class StatsCollector:
    """收集和汇总测试统计数据."""

    def __init__(self) -> None:

        # 执行 __init__ 函数的核心逻辑
        self.requests: list[dict[str, Any]] = []
        self.errors: dict[str, int] = {}
        self.start_time: float | None = None
        self.end_time: float | None = None

    def record_request(
        # 函数 record_request 的初始化逻辑
        self,
        request_type: str,

        # 执行 record_request 函数的核心逻辑
        name: str,
        response_time: float,
        response_length: int,
        success: bool,
        error: str | None = None,
    ) -> None:
        """记录单个请求."""
        self.requests.append(
            {
                "request_type": request_type,
                "name": name,
                "response_time": response_time,
                "respons
        # 条件判断：处理业务逻辑
e_length": response_length,
                "success": success,
                "error": error,
                "timestamp": time.time(),
            }
        )

        # 条件判断: 检查 not success and error
        if not success and error:
            # 初始化变量 error_type
            error_type = erro        # 条件判断：处理业务逻辑
r.split(":")[0] if ":" in error else error
            self.errors[error_type] = self.errors.get(error_type, 0) + 1

    def get_stats(self) -> dict[str, Any]:
        """计算并返回统计数据."""
        # 条件判断: 检查 not self.requests
        if not self.requests:
            # 返回处理结果
            return {"error": "No requests recorded"}

        # 初始化变量 response_times
        response_times = [r["response_time"] for r in self.requests]
        response_times.sort()

        # 初始化变量 total_requests
        total_requests = len(self.requests)
        # 初始化变量 successful_requests
        successful_requests = sum(1 for r in self.requests if r["success"])
        # 初始化变量 failed_requests
        failed_requests = total_requests - successful_requ            # 条件判断：处理业务逻辑
ests

        # 初始化变量 duration
        duration = (self.end_time or time.time()) - (self.start_time or time.time())

        # 计算百分位数
        def percentile(data: list[float], p: float) -> float:
            # 执行 percentile 函数的核心逻辑
            if not data:
                # 返回处理结果
                return 0.0
            k = (len(data) - 1) * (p / 100)
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            d = k - f
            # 返回处理结果
            return data[f] + d * (data[c] - data[f])

        # 返回处理结果
        return {
            "summary": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "error_rate": failed_requests / total_requests if total_requests > 0 else 0,
                "duration_seconds": duration,
                "rps": total_requests / duration if duration > 0 else 0,
            },
            "latency": {
                "min_ms": min(response_times) if response_times else 0,
                "max_ms": max(response_times) if response_times else 0,
                "avg_ms": sum(response_times) / len(response_times) if response_times else 0,
                "p50_ms": percentile(response_times, 50),
                "p95_ms": percentile(response_times, 95),
                "p99_ms": percentile(response_times, 99),
            },
            "errors": self.errors,
            "by_endpoint": self._get_stats_by_endpoint(),

        # 执行 _get_stat            # 条件判断：处理业务逻辑
s_by_endpoint 函数的核心逻辑
        }

    def _get_stats_by_endpoint(self) -> dict[str, Any]:
        """按端点分组统计."""
        endpoints: dict[str, list[dict[str, Any]]] = {}
        # 循环遍历：处理业务逻辑
        for req in self.requests:
            # 初始化变量 name
            name = req["name"]
            # 条件判断: 检查 name not in endpoints
            if name not in endpoints:
                endpoints[name] = []
            endpoints[name].append(req)

        # 初始化变量 result
        result = {}
        # 遍历: for name, reqs in endpoints.ite                # 条
        for name, reqs in endpoints.ite                # 条件判断：处理业务逻辑
ms():
            # 初始化变量 times
            times = [r["response_time"] for r in reqs]
            times.sort()
            # 初始化变量 success_count
            success_count = sum(1 for r in reqs if r["success"])

            def percentile(data: list[float], p: float) -> float:

                # 执行 percentile 函数的核心逻辑
                if not data:
                    # 返回处理结果
                    return 0.0
                k = (len(data) - 1) * (p / 100)
                f = int(k)
                c = f + 1 if f + 1 < len(data) else f
                d = k - f
                # 返回处理结果
                return data[f] + d * (data[c] - data[f])

            result[name] = {
                "count": len(reqs),
                "success_count": success_count,
                "error_count": len(reqs) - success_count,
                "avg_ms": sum(times) / len(times) if times else 0,
                "p50_ms": percentile(times, 50),
                "p95_ms": percentile(times, 95),
                "p99_ms": percentile(times, 99),
            }

        # 返回处理结果
        return result


# ---------------------------------------------------------------------------
# 全局统计收集器实例
# ---------------------------------------------------------------------------

# 初始化变量 stats_collector
stats_collector = StatsCollector()


# 应用装饰器: events.request.add_listener
@events.request.add_listener
def on_request(
    # 函数 on_request 的初始化逻辑
    request_type: str,
    # 执行 on_request 函数的核心逻辑
    name: str,
    response_time: float,
    response_length: int,
    # 捕获异常：处理业务逻辑
    exception: Exception | None = None,
    **kwargs: Any,
) -> None:
    """监听请求事件并记录到统计收集器."""
    # 初始化变量 success
    success = exception is None
    # 初始化变量 error
    error = str(exception) if exception else None
    stats_collector.record_request(
        # 初始化变量 request_type
        request_type=request_type,
        # 初始化变量 name
        name=name,
        # 初始化变量 response_time
        response_time=response_time,
        # 初始化变量 response_length
        response_length=response_length,
        # 初始化变量 success
        success=success,
        # 初始化变量 error
        error=error,
    )


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------


def generate_report(stats: dict[str, Any], output_path: Path) -> None:
    """生成测试报告."""
    # 初始化变量 report
    report = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "duration_minutes": 5,
            "concurrent_users": 50,
        },
        "results": stats,
    }

    # 保存 JSON 报告
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # 使用上下文管理器管理资源
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 记录日志信息
    logger.info(f"测试报告已保存至: {output_path}")

    # 同时输出 Markdown 格式摘要
    md_path = output_path.with_suffix(".md")
    # 使用上下文管理器管理资源
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# 性能压力测试报告\n\n")
        f.write(f"**测试时间**: {report['test_info']['timestamp']}\n\n")
        f.write(f"**并发用户数**: {report['test_info']['concurrent_users']}\n\n")
        f.write(f"**测试时长**: {report['test_info']['duration_minutes']} 分钟\n\n")

        f.write("## 核心指标\n\n")
        summary = stats["summary"]
        f.write(f"- **总请求数**: {summary['total_requests']}\n")
        f.write(f"- **成功请求数**: {summary['successful_requests']}\n")
        f.write(f"- **失败请求数**: {summary['failed_requests']}\n")
        f.write(f"- **错误率**: {summary['error_rate']:.2%}\n")
        f.write(f"- **吞吐量 (RPS)**: {summary['rps']:.2f}\n\n")

        f.write("## 响应延迟\n\n")
        latency = stats["latency"]
        f.write(f"- **最小延迟**: {latency['min_ms']:.2f} ms\n")
        f.write(f"- **最大
        # 条件判断：处理业务逻辑
延迟**: {latency['max_ms']:.2f} ms\n")
        f.write(f"- **平均延迟**: {latency['avg_ms']:.2f} ms\n")
        f.write(f"- **P50 延迟**: {latency['p50_ms']:.2f} ms\n")
        f.write(f"- **P95 延迟**: {latency['p95_ms']:.2f} ms\n")
        f.write(f"- **P99 延迟**: {latency['p99_ms']:.2f} ms\n\n")

        # 条件判断: 检查 stats["errors"]
        if stats["errors"]:
            f.write("## 错误分类\n\n")
            f.write("| 错误类型 | 次数 |\n")
            f.write("|-            # 循环遍历：处理业务逻辑
---------|------|\n")
            # 遍历: for error_type, count in sorted(stats["errors"].it
            for error_type, count in sorted(stats["errors"].items(), key=lambda x: x[1], reverse=True):
                f.write(f"| {error_type} | {count} |\n")
            f.write("\n")

        f.write("## 按端点统计\n\n")
        f.write("| 端点 | 请求数 | 成功数 | 失败数 | 平均延迟(ms) | P95延迟(ms) |\n")
        f.write("|------|--------|----        # 循环遍历：处理业务逻辑
----|--------|--------------|-------------|\n")
        # 遍历: for name, endpoint_stats in stats["by_endpoint"].i
        for name, endpoint_stats in stats["by_endpoint"].items():
            f.write(
                f"| {name} | {endpoint_stats['count']} | "
                f"{endpoint_stats['success_count']} | "
                f"{endpoint_stats['error_count']} | "
                f"{endpoint_stats['avg_ms']:.2f} | "
                f"{endpoint_stats['p95_ms']:.2f} |\n"
            )

    # 记录日志信息
    logger.info(f"Markdown 报告已保存至: {md_path}")


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------


def run_stress_test(
    # 函数 run_stress_test 的初始化逻辑
    host: str = "http://localhost:8000",
    users: int = 50,
    spawn_rate: int = 5,
    run_time: int = 300,
    output_dir: Path | None = None,
    html_report: Path | None = None,
) -> dict[str, Any]:
    """运行压力测试.

    Args:
        host: 目标服务地址
        users: 并发用户数
        spawn_rate: 用户生成速率（每秒）
        run_time: 测试持续时间（秒）
        output_dir: 输出目录
        html_report: HTML 报告路径

    Returns:
        测试结果统计字典
    """
    # 初始化变量 output_dir
    output_dir = output_dir or BACKEND_ROOT / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 记录日志信息
    logger.info("=" * 60)
    # 记录日志信息
    logger.info("开始性能压力测试")
    # 记录日志信息
    logger.info(f"目标地址: {host}")
    # 记录日志信息
    logger.info(f"并发用户数: {users}")
    # 记录日志信息
    logger.info(f"用户生成速率: {spawn_rate}/s")
    # 记录日志信息
    logger.info(f"测试持续时间: {run_time}s")
    # 记录日志信息
    logger.info("=" * 60)

    # 创建 Locust 环境
    env = Environment(user_classes=[APIUser])
    env.create_local_runner()
          # 条件判断：处理业务逻辑
  env.create_web_ui(host="127.0.0.1", port=8089)

    # 记录开始时间
    stats_collector.start_time = time.time()

    # 启动测试
    env.runner.start(user_count=users, spawn_rate=spawn_rate)

    # 等待测试完成
    logger.info("测试进行中...")
    # 初始化变量 start
    start = time.time()
    # 循环条件：处理业务逻辑
    while time.time() - start < run_time:
        time.sleep(1)
        # 条件判断: 检查 env.runner.state in (STATE_STOPPED, STAT
        if env.runner.state in (STATE_STOPPED, STATE_STOPPING):
            break

    # 停止测试
    logger.info("测试完成，正在收集统计数据...")
    env.runner.quit()
    env.web_ui.stop()

    # 记录结束时间
    stats_collector.end_time = time.time()

    # 获取统计数据
    stats = stats_collector.get_stats()

    # 生成报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 初始化变量 json_report_path
    json_report_path = output_dir / f"stress_test_report_{timestamp}.json"
    generate_report(stats, json_report_path)

    # 打印统计摘要
    print_stats(env.stats.runners)

    # 输出核心指标
    logger.info("\n" + "=" * 60)
    # 记录日志信息
    logger.info("核心测试指标:")
    # 记录日志信息
    logger.info(f"  总请求数: {stats['summary']['total_requests']}")
    # 记录日志信息
    logger.info(f"  错误率: {stats['summary']['error_rate']:.2%}")
    # 记录日志信息
    logger.info(f"  吞吐量: {stats['summary']['rps']:.2f} RPS")
    # 记录日志信息
    logger.info(f"  P50 延迟: {stats['latency']['p50_ms']:.2f} ms")


    # 执行 main 函数的核心逻辑
    logger.info(f"  P95 延迟: {stats['latency']['p95_ms']:.2f} ms")
    # 记录日志信息
    logger.info(f"  P99 延迟: {stats['latency']['p99_ms']:.2f} ms")
    # 记录日志信息
    logger.info("=" * 60)

    # 返回处理结果
    return stats


def main() -> None:
    """主函数."""
    # 初始化变量 parser
    parser = argparse.ArgumentParser(description="API 性能压力测试工具")
    parser.add_argument(
        "--host",
        # 初始化变量 type
        type=str,
        # 初始化变量 default
        default="http://localhost:8000",
        # 初始化变量 help
        help="目标服务地址 (默认: http://localhost:8000)",
    )
    parser.add_argument(
        "--users",
        # 初始化变量 type
        type=int,
        # 初始化变量 default
        default=50,
        # 初始化变量 help
        help="并发用户数 (默认: 50)",
    )
    parser.add_argument(
        "--spawn-rate",
        # 初始化变量 type
        type=int,
        # 初始化变量 default
        default=5,
        # 初始化变量 help
        help="用户生成速率，每秒 (默认: 5)",
    )
    parser.add_argument(
        "--run-time",
        # 初始化变量 type
        type=int,
        # 初始化变量 default
        default=300,
        # 初始化变量 help
        help="测试持续时间，秒 (默认: 300，即5分钟)",
    )
    parser.add_argument(
        "--output-dir",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=None,
        # 初始化变量 help
        help="报告输出目录 (默认: backend/reports/)",
    )
    parser.add_argument(
        "--html",
        # 初始化变量 type
        type=Path,
        # 初始化变量 dest
        dest="html_report",
        # 初始化变量 default
        default=None,
        # 初始化变量 help
        help="HTML 报告输出路径",
    )
    parser.add_argument(
        "--headless",
        # 初始化变量 action
        action="store_true",
        # 初始化变量 default
        default=True,
        # 初始化变量 help
        help="无头模式运行 (默认启用        # 条件判断：处理业务逻辑
)",
    )

    # 初始化变量 args
    args = parser.parse_args()

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 stats
        stats = run_stress_test(
            # 初始化变量 host
            host=args.host,
            # 初始化变量 users
            users=args.users,
            # 初始化变量 spawn_rate
            spawn_rate=args.spawn_rate,
            # 初始化变量 run_time
            run_time=args.run_time,
            # 初始化变量 output_dir
            output_dir=args.output_dir,
            # 初始化变量 html_report
            html_report=args.html_report,
        )

        # 根据测试结果设置退出码
        i

# 条件判断：处理业务逻辑
f stats["summary"]["error_rate"] > 0.1:
            # 记录日志信息
            logger.warning("错误率超过 10%，测试可能存在问题")
            sys.exit(1)
        # 其他情况的默认处理
        else:
            # 记录日志信息
            logger.info("压力测试完成")
      
    # 捕获异常：处理业务逻辑
      sys.exit(0)

    # 捕获并处理异常
    except KeyboardInterrupt:
        # 记录日志信息
        logger.    # 捕获异常：处理业务逻辑
info("用户中断测试")
        sys.exit(130)
    # 捕获并处理异常
    except Exception as e:
        # 记录日志信息
        logger.exception(f"压力测试失败: {e}")
        sys.exit(1)


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()

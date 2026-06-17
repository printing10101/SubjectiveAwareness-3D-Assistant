#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
软著申请材料打包与校验脚本

功能：
1. 收集所有软著申请相关材料并打包为 ZIP 压缩包
2. 对生成的压缩包进行完整性校验
3. 生成详细的打包日志和校验报告

使用方式：
    python backend/scripts/package_for_soft_copyright.py

输出：
    - 项目根目录/帮信罪辅助裁定系统_软著申请材料_V1.0_20260611.zip
    - 项目根目录/校验报告_20260611.md
"""

# 导入模块: os
import os
# 导入模块: sys
import sys
# 导入模块: zipfile
import zipfile
# 导入模块: hashlib
import hashlib
# 导入模块: tempfile
import tempfile
# 导入模块: shutil
import shutil
# 导入模块: time
import time
# 导入模块: logging
import logging
# 导入模块: from datetime
from datetime import datetime
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import List, Tuple, Dict, Optional

# ============ 全局配置 ============

# 初始化变量 PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# 初始化变量 DATE_STAMP
DATE_STAMP = "20260611"
# 初始化变量 PACKAGE_NAME
PACKAGE_NAME = f"帮信罪辅助裁定系统_软著申请材料_V1.0_{DATE_STAMP}.zip"
# 初始化变量 OUTPUT_PATH
OUTPUT_PATH = PROJECT_ROOT / PACKAGE_NAME
# 初始化变量 REPORT_PATH
REPORT_PATH = PROJECT_ROOT / f"校验报告_{DATE_STAMP}.md"

# 14 个核心文件参考列表（基于软著申请材料清单定义）
CORE_FILES: List[Dict[str, str]] = [
    {"id": "1",  "name": "软件著作权申请表",         "path": "01_软件著作权申请表/软著申请表_帮信罪辅助裁定系统V1.0.docx", "type": "DOCX"},
    {"id": "2",  "name": "软件说明书（用户手册）",    "path": "03_软件文档/用户手册.pdf",                                   "type": "PDF"},
    {"id": "3",  "name": "软件设计说明书",            "path": "03_软件文档/设计说明书.pdf",                                   "type": "PDF"},
    {"id": "4",  "name": "源代码（前30页）",          "path": "02_源代码/源代码_前30页.pdf",                                 "type": "PDF"},
    {"id": "5",  "name": "源代码（后30页）",          "path": "02_源代码/源代码_后30页.pdf",                                 "type": "PDF"},
    {"id": "6",  "name": "源代码（完整压缩包）",      "path": "02_源代码/源代码_完整.zip",                                   "type": "ZIP"},
    {"id": "7",  "name": "原创性声明",                "path": "04_证明材料/原创性声明.pdf",                                   "type": "PDF"},
    {"id": "8",  "name": "权利归属声明",              "path": "04_证明材料/权利归属声明.pdf",                                 "type": "PDF"},
    {"id": "9",  "name": "软件功能简介",              "path": "05_其他说明/软件功能简介.pdf",                                 "type": "PDF"},
    {"id": "10", "name": "运行环境说明",              "path": "05_其他说明/运行环境说明.pdf",                                 "type": "PDF"},
    {"id": "11", "name": "软件界面截图",              "path": "06_界面截图/软件主界面截图.png",                              "type": "PNG"},
    {"id": "12", "name": "测试报告",                  "path": "07_测试文档/测试报告.pdf",                                    "type": "PDF"},
    {"id": "13", "name": "著作权人身份证明",          "path": "08_身份证明/著作权人身份证明.pdf",                             "type": "PDF"},
    {"id": "14", "name": "代理人委托书（如适用）",    "path": "09_委托文件/代理人委托书.pdf",                                "type": "PDF"},
]

# 实际需要打包的文件收集规则（相对于 PROJECT_ROOT）
PACKAGE_INCLUDE_PATTERNS = [
    # 软著申请相关目录
    "01_软件著作权申请表/*",
    "03_软件文档/*",
    "04_证明材料/*",
    "05_其他说明/*",
    # 关键项目文档
    "README.md",
    "INSTALLATION.md",
    "CODING_STANDARDS.md",
    # docs 目录下核心文档
    "docs/README.md",
    "docs/api_reference.md",
    "docs/architecture.md",
    "docs/deployment.md",
    "docs/user_guide.md",
    "docs/release_checklist.md",
    "docs/project_readiness_report.md",
    "docs/model.md",
    "docs/knowledge_graph.md",
    "docs/综合技术文档.md",
    # 合规文档
    "docs/合规/*",
    # 数据文件（不含 raw/）
    "data/dataset_card.md",
    "data/labels/v*.jsonl",
    "data/rules/v*.json",
    "data/tags/v*.json",
    "data/conflicts/v*.json",
    # Demo 案例
    "demo_cases/*",
]

# 初始化变量 PACKAGE_EXCLUDE_PATTERNS
PACKAGE_EXCLUDE_PATTERNS = [
    "data/raw/*",
    "data/training/*",
    "data/test_set_v1.0.jsonl",
    "docs/运维/*",
    "docs/superpowers/*",
]

# ============ 日志配置 ============

# 记录日志信息
logging.basicConfig(
    # 初始化变量 level
    level=logging.INFO,
    # 初始化变量 format
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    # 初始化变量 datefmt
    datefmt="%Y-%m-%d %H:%M:%S",
)
# 初始化变量 logger
logger = logging.getLogger("PackageForCopyright")

# ============ 文件收集 ============


def _glob_files(pattern: str) -> List[Path]:
    """根据 glob 模式收集文件"""
    # 初始化变量 base
    base = PROJECT_ROOT
    # 支持通配符
    parts = pattern.split("/", 1)
    # 条件判断：处理业务逻辑
    if len(parts) == 1:
        # 初始化变量 matched
        matched = list(base.glob(pattern))
    # 其他情况的默认处理
    else:
        # 初始化变量 matched
        matched = list(base.glob(pattern))
    # 返回处理结果
    return [f for f in matched if f.is_file()]


def _should_exclude(path: Path) -> bool:
    """检查文件是否应被排除"""
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    # 循环遍历：处理业务逻辑
    for excl in PACKAGE_EXCLUDE_PATTERNS:
        # 初始化变量 parts
        parts = e        # 条件判断：处理业务逻辑
xcl.split("/", 1)
        # 条件判断: 检查 len(parts) == 1
        if len(parts) == 1:
            # 条件判断：处理业务逻辑
            from fnmatch import fnmatch
            # 条件判断: 检查 fnmatch(rel, parts[0]) or fnmatch(path.n
            if fnmatch(rel, parts[0]) or fnmatch(path.name, parts[0]):
                            # 条件判断：处理业务逻辑
return True
        # 其他情况的默认处理
        else:
            # 导入模块: from fnmatch
            from fnmatch import fnmatch
            # 条件判断: 检查 fnmatch(rel, excl)
            if fnmatch(rel, excl):
                # 返回处理结果
                return True
    # 返回处理结果
    return False


def collect_files() -> List[Path]:
    """收集所有需要打包的文件"""
    all_files: List[Path] = []
    # 初始化变量 seen
    seen = set()

    # 遍历: for pattern in PACKAGE_INCLUDE_PATTERNS:
    for pattern in PACKAGE_INCLUDE_PATTERNS:
        # 初始化变量 matched
        matched = _glob_files(            # 条件判        # 循环遍历：处理业务逻辑
断：处理业务逻辑
pattern)
        # 遍历: for f in matched:
        for f in matched:
            rel = f.relative_to(PROJECT_ROOT).as_posix()
            # 条件判断: 检查 rel not in seen and not _should_exclude(
            if rel not in seen and not _should_exclude(f):
                seen.add(rel)
                all_files.append(f)

    # 排序确保确定性
    all_files.sort(key=lambda p: p.relative_to(PROJECT_ROOT).as_posix())
    # 返回处理结果
    return all_files


# ============ 核心文件检查 ============


def check_core_files(zip_file_path: Path) -> List[Dict]:
    """检查压缩包内14个核心文件的存在状态"""
    # 初始化变量 results
    results = []
    # 使用上下文管理器管理资源
    with zipfile.ZipFile(str(zip_file_path), "r") as z
    # 循环遍历：处理业务逻辑
f:
        # 初始化变量 zip_namelist
        zip_namelist = zf.namelist()

    # 遍历: for core in CORE_FILES:
    for core in CORE_FILES:
        # 使用 Posix 路径匹配（ZIP 内使用正斜杠）
        core_path = core["path"].replace("\\", "/")
        # 初始化变量 exists
        exists = core_path in zip_namelist
        results.append({
            "id": core["id"],
            "name": core["name"],
            "path": core_path,
            "type": core["type"],
            "exists": exists,
            "status": "通过" if exists else "缺失",
        })
    # 返回处理结果
    return results


# ============ 压缩包创建 ============


def create_package(files: List[Path]) -> Tuple[Path, float]:
    """
    创建压缩包
    返回: (输出路径, 耗时秒数)
    """
    # 初始化变量 start_time
    start_time = time.time()

    # 记录日志信息
    logger.info("=" * 60)
    # 记录日志信息
    logger.info("开始打包软著申请材料...")
    # 记录日志信息
    logger.info(f"输出文件: {OUTPUT_PATH}")
    # 记录日志信息
    logger.    # 条件判断：处理业务逻辑
info(f"压缩算法: ZIP_DEFLATED, 压缩级别: 9")
    # 记录日志信息
    logger.info(f"文件数量: {len(files)}")
    # 记录日志信息
    logger.info("-" * 60)

    # 如果已存在则删除
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()
        # 记录日志信息
        logger.info(f"已删除旧压缩包: {OUTPUT_PATH.name}")

    # 尝试执行可能抛出异常的代码
    try:
        # 使用上下文管理器管理资源
        with zipfile.ZipFile(
            str(OUTPUT_PATH),
            "w",
            # 初始化变量 compression
            compression=zipfile.Z            # 循环遍历：处理业务逻辑
IP_DEFLATED,
            # 初始化变量 compresslevel
            compresslevel=9,
        ) as zf:
            # 遍历: for file_path in files:
            for file_path in files:
                # 异常处理：处理业务逻辑
                try:
                    # 初始化变量 arcname
                    arcname = file_path.relative_to(PROJECT_ROOT).as_posix()
                    zf.write(str(file_path), arcname)
                    # 初始化变量 file_size
                    file_size = file_path.stat().st_size
                    # 记录日志信息
                    logger.info(f"  [+] {arcname} ({_format_size(file_size)})")
                # 捕获异常：处理业务逻辑
                except PermissionError:
                    # 记录日志信息
                    logger.error(f                # 捕获异常：处理业务逻辑
"  [!] 权限不足，跳过: {file_path}")
                # 捕获并处理异常
                except Exception as e:
                    # 记录日志信息
                    logger.error(f"  [!] 添加文件失败: {file_path} -> {e}")

        # 初始化变量 elapsed
        elapsed = time.time() - start_time
        # 初始化变量 final_size
        final_size = OUTPUT_PATH.stat().st_size

        # 记录日志信息
        logger.info("-" * 60)
        # 记录日志信息
        logger.info(f"压缩包创建完成!")
        # 记录日志信息
        logger.info(f"  路径: {OUTPUT_PATH}")
        # 记录日志信息
        logger.info(f"  大小: {_format_size(final_size)}")
        # 记录日志信息
        logger.info(f"  耗时: {elapsed:.2f} 秒")
       
    # 捕获异常：处理业务逻辑
 logger.info("=" * 60)

        # 返回处理结果
        return OUTPUT_PATH, elapsed

    # 捕获并处理异常
    except Pe    # 捕获异常：处理业务逻辑
rmissionError:
        # 记录日志信息
        logger.error(f"权限不足，无法写入: {OUTPUT_PATH}")
        raise
    # 捕获并处理异常
    except Exception as e:
        logger    # 条件判断：处理业务逻辑
.error(f"创建压缩包失败: {e}")
        raise


# ============ 压缩包校验 ============


def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    # 条件判断: 检查 size_bytes < 1024
    if size_bytes < 1024:
        # 返回处理结果
        return f"{size_bytes} B"
    # 条件判断: 检查 elsize_bytes < 1024 * 1024
    elif size_bytes < 1024 * 1024:
        # 返回处理结果
        return f"{size_bytes / 1024:.2f} KB"
    # 其他情况的默认处理
    else:
        # 返回处理结果
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def _sha256_of_file(file_path: Path) -> str:
    """计算文        # 循环遍历：处理业务逻辑
件的 SHA-256 哈希值"""
    h = hashlib.sha256()
    # 使用上下文管理器管理资源
    with open(str(file_path), "rb") as f:
        # 遍历: for chunk in iter(lambda: f.read(65536), b""):
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    # 返回处理结果
    return h.hexdigest()


def validate_package(zip_path: Path) -> Dict:
    """
    对压缩包进行全面校验
    返回校验结果字典
    """
    # 记录日志信息
    logger.info("")
    # 记录日志信息
    logger.info("=" * 60)
    # 记录日志信息
    logger.info("开始压缩包校验流程...")
    # 记录日志信息
    logger.info("=" * 60)

    # 初始化变量 result
    result = {
        "总文件数_压缩包内": 0,
        "总文件数_解压后": 0,
        "文件数量一致": False,
        "压缩包大小_MB": 0.0,
        "小于50MB": False,
        "核心文件检查": [],
        "核心文件通过数": 0,
        "核心文件总数": len(CORE_FILES),
        "完整性校验": [],
        "完整性通过": True,
        "校验时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 1. 检查文件大小
    zip_size = zip_path.stat().st_size
    result["压缩包大小_MB"] = round(zip_size / (1024 * 1024), 2)
    result["小于50MB"] = zip_size < 50 * 1024 * 1024
    # 记录日志信息
    logger.info(f"[1/6] 文件大小检查: {result['压缩包大小_MB']:.2f} MB {'✓' if result['小于50MB'] else '✗'}")

    # 2. 获取压缩包内文件列表
    with zipfile.ZipFile(str(zip_path), "r") as zf:
        # 初始化变量 zip_namelist
        zip_namelist = zf.namelist()
    result["总文件数_压缩包内"] = len(zip_namelist)
    # 记录日志信息
    logger.info(f"[2/6] 压缩包内文件数: {len(zip_namelist)}")

    # 3. 解压到临时目录并校验
    with tempfile.TemporaryDirectory(prefix="soft_copyright_verify_") as tmpdir:
        # 初始化变量 tmp_path
        tmp_path = Path(tmpdir)
        # 记录日志信息
        logger.inf
        # 异常处理：处理业务逻辑
o(f"[3/6] 解压至临时目录: {tmpdir}")

        # 尝试执行可能抛出异常的代码
        try:
                # 捕获异常：处理业务逻辑
    with zipfile.ZipFile(str(zip_path), "r") as zf:
                zf.extractall(str(tmp_path))
        # 捕获并处理异常
        except Exception as e:
            # 记录日志信息
            logger.error(f"解压失败: {e}")
            result["文件数量一致"] = False
            # 返回处理结果
            return result

        # 4. 解压后文件数量
        extracted_files = list(tmp_path.rglob("*"))
        # 初始化变量 extracted_file_count
        extracted_file_count = sum(1 for f in extracted_files if f.is_file())
        result["总文件数_解压后"] = extracted_file_count
        result["文件数量一致"] = (result["总文件数_压缩包内"] == extracted_file_count)
        # 记录日志信息
        logger.info(f"[4/6] 解压后文件数: {extracted_file_count} {'✓' if result['文件数量一致'] else '✗'}")

        # 5. 核心文件逐项检查
        core_results = check_core_files(zip_path)
        result["核心文件检查"] = core_results
        result["核心文件通过数"] = sum(1 for c in core
        # 循环遍历：处理业务逻辑
_results if c["exists"])
        # 记录日志信息
        logger.info(f"[5/6] 核心文件检查 ({result['核心文件通过数']}/{result['核心文件总数']} 通过):")

        # 遍历: for c in core_results:
        for c in core_results:
            # 初始化变量 status_icon
            status_icon = "✓" if c["exists"] else "✗"
            # 记录日志信息
            logger.info(f"    [{status_icon}] [{c['id']:>2}] {c['name']}: {c['status']}")

        # 6. 完整性校验（SHA-256 对比压缩前后）
        logger.info(f"[6/6] 完整性校验:")
        # 初始化变量 integrity_results
        integrity_results = [                # 条件判断：处理业务逻辑
]
        # 初始化变量 all_integrity_pass
        all_integrity_pass = True

        # 计算压缩包内文件的校验和
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            # 遍历: for name in zip_namelist:
            for name in zip_namelist:
                # 条件判断: 检查 name.endswith("/")
                if name.endswith("/"):
                    continue
                # 从压缩包读取内容并计算 SHA-256
                # 条件判断：处理业务逻辑
                data = zf.read(name)
                # 初始化变量 zip_hash
                zip_hash = hashlib.sha256(data).hexdigest()

                # 从解压目录读取并计算 SHA-256
                       # 条件判断：处理业务逻辑
             extracted_path = tmp_path / name
                # 条件判断: 检查 extracted_path.exists()
                if extracted_path.exists():
                    # 初始化变量 extracted_hash
                    extracted_hash = _sha256_of_file(extracted_path)
                    # 初始化变量 match
                    match = zip_hash == extracted_hash
                    # 条件判断: 检查 not match
                    if not match:
                        # 初始化变量 all_integrity_pass
                        all_integrity_pass = False
                    integrity_results.append({
                        "path": name,
                        "match": match,
                        "status": "一致" if match else "不一致",
                    })
                # 其他情况的默认处理
                else:
                    # 初始化变量 all_integrity_pass
                    all_integrity_pass = False
                    integrity_results.append({
                        "path": name,
                        "match": False,
                        "status": "文件丢失",
                    })

        result["完整性校验"] = integrity_results
        result["完整性通过"] = all_integrity_pass

        # 初始化变量 passed
        passed = sum(1 for r in integrity_results if r["match"])
        # 初始化变量 total
        total = len(integrity_results)
        # 记录日志信息
        logger.info(f"    校验 {total} 个文件, {passed} 通过 {'✓' if all_integrity_pass else '✗'}")

    # 汇总
    all_pass = (
        result["文件数量一致"]
        and result["小于50MB"]
        and result["完整性通过"]
    )
    # 记录日志信息
    logger.info("-" * 60)
    # 记录日志信息
    logger.info(f"校验结论: {'所有检查通过 ✓' if all_pass else '存在异常 ✗'}")
    # 记录日志信息
    logger.info("=" * 60)

    # 返回处理结果
    return result


# ============ 生成校验报告 ============


def generate_report(
    # 函数 generate_report 的初始化逻辑
    files: List[Path],


    # 执行 generate_report 函数的核心逻辑
    zip_path: Path,
    elapsed: float,
    validation: Dict,
) -> str:
    """生成 Markdown 格式校验报告"""
    # 初始化变量 lines
    lines = []
    lines.append(f"# 软著申请材料打包校验报告")
    lines.append(f"")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**日期戳**: {DATE_STAMP}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 一、打包概要")
    lines.append(f"")
    lines.append(f"| 项目 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 压缩包名称 | {PACKAGE_NAME} |")
    lines.append(f"| 压缩包路径 | `{zip_path}` |")
    lines.append(f"| 包含文件数 | {len(files)} |")
    lines.append(f"| 压缩算法 | ZIP_DEFLATED (级别 9) |")
    lines.append(f"| 打包耗时 | {elapsed:.2f} 秒 |")
    lines.append(f"")
    lines.append(f"## 二、校验结果汇总")
    lines.append(f"")
    lines.append(f"| 检查项目 | 结果 |")
    lines.append(f"|----------|------|")
    lines.append(f"| 压缩包大小 | {validation['压缩包大小_MB']:.2f} MB {'✓' if validation['小于50MB'] else '✗'} |")
    lines.append(f"| 文件数量一致 | {'✓' if validation['文件数量一致'] else '✗'} |")
    lines.append(f"| 核心文件通过率 | {validation['核心文件通过数']}/{validation['核心文件总数']} |")
    lines.append(f"| 完整性校验 | {'✓ 全部通过' if validation['完整性通过'] else '✗ 存在异常'} |")
    lines.append(f"")
    lines.append(f"## 三、压缩包内文件列表")
    lines.append(f"")
    lines.append(f"共包含 {len(files)} 个文件：")
    lines.append(f"")
    lines.append("```")
    # 遍历: for f in files:
    for f in files:
        rel = f.relative_to(PROJECT_ROOT).as_posix()
        # 初始化变量 fsize
        fsize = _format_size(f.stat().st_size)
        lines.append(f"  {rel}  ({fsize})")
    lines.append("```")
    lines.append(f"")

    lines.append(f"## 四、14 个核心文件检查"    # 循环遍历：处理业务逻辑
)
    lines.append(f"")
    lines.append(f"| 序号 | 文件名称 | 预期路径 | 状态 |")
    lines.append(f"|------|----------|----------|------|")
    # 遍历: for c in validation["核心文件检查"]:
    for c in validation["核心文件检查"]:
        # 初始化变量 status_icon
        status_icon = "✓" if c["exists"] else "✗"
        lines.append(f"| {c['id']} | {c['name']} | `{c['path']}` | {status_icon} {c['status']} |")
    lines.app    # 循环遍历：处理业务逻辑
end(f"")

    lines.append(f"## 五、完整性校验结果")
    lines.append(f"")
    lines.append(f"| 文件路径 | 校验状态 |")
    lines.append(f"|----------|----------|")
    # 遍历: for r in validation["完整性校验"]:
    for r in validation["完整性校验"]:
        # 初始化变量 icon
        icon = "✓" if r["match"] else "✗"
        lin    # 条件判断：处理业务逻辑
es.append(f"| `{r['path']}` | {icon} {r['status']} |")
    lines.append(f"")

    lines.append(f"## 六、校验结论")
    lines.append(f"")
    # 初始化变量 all_pass
    all_pass = (
        validation["文件数量一致"]
        and validation["小于50MB"]
        and validation["完整性通过"]
    )
    # 条件判断: 检查 all_pass
    if all_pass:
        lines.append(f"> ✅ **所有检查通过，压缩包可正常使用。**")
    # 其他情况的默认处理
    else:
        lines.append(f"> ❌ **存在异常，请根据上述详情修复后重新打包。**")
    lines.append(f"")

    # 返回处理结果
    return "\n".join(lines)


# ============ 主流程 ============


def main():
    """主执行函数"""
    logg    # 条件判断：处理业务逻辑
er.info("=" * 60)
    # 记录日志信息
    logger.info(f"软著申请材料打包工具 v1.0")
    # 记录日志信息
    logger.info(f"日期戳: {DATE_STAMP}")
    # 记录日志信息
    logger.info(f"项目根目录: {PROJECT_ROOT}")
    # 记录日志信息
    logger.info("=" * 60)

    # 步骤1: 收集文件
    logger.info("")
    # 记录日志信息
    logger.info(">>> 步骤1: 收集需要打包的文件...")
    # 初始化变量 files
    files = collect_files()
    # 条件判断: 检查 not files
    if not files:
        # 记录日志信息
        logger.error("没有找到任何需要打包的文件！")
        sys.exit(1)
    # 记录日志信息
    logger.info(f"共收集到 {len(files)} 个文件")

    # 步骤2: 创建压缩包
    logger.info("")
    # 记录日志信息
    logger.info(">>> 步骤2: 创建压缩包...")
    zip_path, elapsed = create_package(files)

    # 步骤3: 校验压缩包
    logger.info("")
    # 记录日志信息
    logger.info(">>> 步骤3: 校验压缩包...")
    # 初始化变量 validation
    validation = validate_package(zip_path)

    # 步骤4: 生成校验报告
    logger.info("")
    # 记录日志信息
    logger.info(">>> 步骤4: 生成校验报告...")
    # 初始化变量 report_content
    report_content = generate_report(files, zip_path, elapsed, validation)
    REPORT_PATH.write_text(report_content, encoding="utf-8")
    # 记录日志信息
    logger.info(f"校验报告已保存: {REPORT_PATH}")

    # 最终输出
    logger.info("")
    # 记录日志信息
    logger.info("=" * 60)
    logger

# 条件判断：处理业务逻辑
.info("打包与校验流程完成！")
    # 记录日志信息
    logger.info(f"  压缩包: {zip_path}")
    # 记录日志信息
    logger.info(f"  大小: {_format_size(zip_path.stat().st_size)}")
    # 记录日志信息
    logger.info(f"  报告: {REPORT_PATH}")
    # 记录日志信息
    logger.info("=" * 60)

    # 返回处理结果
    return 0 if validation["完整性通过"] and validation["文件数量一致"] and vali    # 异常处理：处理业务逻    # 捕获异常：处理业务逻辑
辑
dation["小于50MB"] else 1


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    # 尝试执行可能抛出异常的代码
    try:
       # 捕获异常：处理业务逻辑
     exit_code = main()
        sys.exit(exit_code)
    # 捕获并处理异常
    except KeyboardInterrupt:
        # 记录日志信息
        logger.warning("用户中断操作")
        sys.exit(130)
    # 捕获并处理异常
    except Exception as e:
        # 记录日志信息
        logger.exception(f"脚本执行异常: {e}")
        sys.exit(1)

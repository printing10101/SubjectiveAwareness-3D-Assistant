"""
LoRA微调模型评估脚本
支持多维度评估：BLEU-4、ROUGE-L、BERTScore、领域术语准确率
包含基线模型对比和人工评估方案设计
"""

import os
import sys
import json
import re
import time
from pathlib import Path
from datetime import datetime

import torch
import yaml
import numpy as np
from datasets import load_dataset
from loguru import logger

_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_script_dir, ".."))
sys.path.insert(0, os.path.join(_script_dir, "..", "finetune", "scripts"))


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "finetune" / "config" / "finetune_config.yaml"
LORA_WEIGHTS_DIR = PROJECT_ROOT / "models" / "lora_weights"
LOGS_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = PROJECT_ROOT / "reports"


DOMAIN_TERMS = [
    "帮助信息网络犯罪活动罪",
    "帮信罪",
    "主观明知",
    "明知",
    "应当知道",
    "信息网络犯罪",
    "支付结算",
    "技术支持",
    "资金转账",
    "银行卡",
    "支付账户",
    "手机卡",
    "网络账号",
    "电信网络诈骗",
    "网络赌博",
    "非法集资",
    "共同犯罪",
    "从犯",
    "主犯",
    "犯罪故意",
    "过失",
    "电信诈骗",
    "洗钱",
    "跑分",
    "水房",
    "卡商",
    "卡农",
    "GOIP",
    "VOIP",
    "多卡宝",
    "四方支付",
    "跑分平台",
    "虚拟币",
    "USDT",
    "OTC交易",
    "推定明知",
    "综合认定",
    "明知认定",
    "主观故意",
    "客观行为",
    "交易异常",
    "异常交易",
    "快进快出",
    "夜间交易",
    "频繁交易",
    "实名认证",
    "实名制",
    "断卡行动",
    "两卡",
    "涉案账户",
    "犯罪数额",
    "违法所得",
    "获利",
    "退赃退赔",
    "认罪认罚",
    "刑事判决书",
    "刑事裁定书",
    "一审",
    "二审",
    "再审",
    "公诉机关",
    "辩护人",
    "审判长",
    "审判员",
    "人民陪审员",
]


DOMAIN_TERM_SYNONYMS = {
    "帮信罪": ["帮助信息网络犯罪活动罪", "帮信"],
    "明知": ["主观明知", "明确知道", "知道"],
    "跑分": ["跑分平台", "跑分活动", "跑分行为"],
    "USDT": ["泰达币", "usdt", "U币"],
    "GOIP": ["goip设备", "GOIP设备", "多卡宝"],
}


def setup_logging():
    """配置日志系统"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"evaluate_model_{timestamp}.log"

    logger.remove()
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<7}</level> | "
            "<cyan>{message}</cyan>"
        ),
        level="INFO",
    )
    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
        level="DEBUG",
        rotation="50 MB",
    )

    logger.info(f"日志文件: {log_file}")
    return log_file


def load_config(config_path: str = None) -> dict:
    """加载配置文件"""
    if config_path is None:
        config_path = str(DEFAULT_CONFIG_PATH)
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def load_test_data(data_path: str, max_samples: int = None):
    """加载测试数据

    Args:
        data_path: 测试数据文件路径
        max_samples: 最大测试样本数

    Returns:
        测试样本列表 [{"prompt": ..., "reference": ...}, ...]
    """
    if not os.path.exists(data_path):
        logger.warning(f"测试数据文件不存在: {data_path}")
        return []

    if data_path.endswith(".jsonl"):
        dataset = load_dataset("json", data_files=data_path, split="train")
    elif data_path.endswith(".json"):
        dataset = load_dataset("json", data_files=data_path, split="train")
    else:
        raise ValueError(f"不支持的数据格式: {data_path}")

    samples = []
    for i, item in enumerate(dataset):
        if max_samples and i >= max_samples:
            break
        samples.append(
            {
                "prompt": item.get("instruction", ""),
                "input": item.get("input", ""),
                "reference": item.get("output", ""),
            }
        )

    logger.info(f"加载测试数据: {len(samples)}条 (来源: {data_path})")
    return samples


def load_finetuned_model(config: dict, adapter_path: str):
    """加载微调后的模型（基础模型 + LoRA适配器）

    Args:
        config: 配置字典
        adapter_path: LoRA适配器权重路径

    Returns:
        (model, tokenizer)
    """
    from unsloth import FastLanguageModel
    from peft import PeftModel

    model_config = config["model"]

    logger.info(f"加载基础模型: {model_config['model_name_or_path']}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_config["model_name_or_path"],
        max_seq_length=model_config["max_seq_length"],
        dtype=None,
        load_in_4bit=model_config["load_in_4bit"],
    )

    if os.path.exists(adapter_path):
        logger.info(f"加载LoRA适配器: {adapter_path}")
        model = PeftModel.from_pretrained(model, adapter_path)
        logger.info("LoRA适配器加载完成")
    else:
        logger.warning(f"LoRA适配器路径不存在: {adapter_path}")
        logger.warning("将使用基础模型进行评估（作为基线）")

    FastLanguageModel.for_inference(model)
    return model, tokenizer


def load_base_model(config: dict):
    """加载基础模型（无LoRA，用于基线对比）

    Args:
        config: 配置字典

    Returns:
        (model, tokenizer)
    """
    from unsloth import FastLanguageModel

    model_config = config["model"]

    logger.info(f"加载基础模型(基线): {model_config['model_name_or_path']}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_config["model_name_or_path"],
        max_seq_length=model_config["max_seq_length"],
        dtype=None,
        load_in_4bit=model_config["load_in_4bit"],
    )

    FastLanguageModel.for_inference(model)
    return model, tokenizer


def generate_response(
    model,
    tokenizer,
    prompt: str,
    input_text: str = "",
    max_new_tokens: int = 512,
):
    """生成模型回复

    Args:
        model: 模型
        tokenizer: 分词器
        prompt: 提示词
        input_text: 输入文本
        max_new_tokens: 最大生成token数

    Returns:
        生成的文本
    """
    messages = [{"role": "user", "content": prompt}]
    if input_text:
        messages[0]["content"] = f"{prompt}\n\n{input_text}"

    input_token_count = len(tokenizer.encode(messages[0]["content"]))
    logger.debug(
        f"生成推理 - prompt长度={len(messages[0]['content'])}字符, "
        f"input_tokens={input_token_count}"
    )

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(text, return_tensors="pt").to("cuda")

    start_time = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            use_cache=True,
            temperature=0.1,
            top_p=0.9,
            repetition_penalty=1.1,
            do_sample=False,
        )
    inference_time = time.time() - start_time

    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)

    output_token_count = outputs.shape[1] - inputs["input_ids"].shape[1]
    logger.debug(
        f"生成推理完成 - output_tokens={output_token_count}, "
        f"耗时={inference_time:.2f}秒"
    )

    if text in generated:
        response = generated[len(text) :].strip()
    else:
        try:
            response = generated.split("<|assistant|>")[-1].strip()
            response = response.split("<|end|>")[0].strip()
        except Exception:
            response = generated.strip()

    logger.debug(f"生成结果预览(前100字): {response[:100]}")

    return response


def normalize_text(text: str) -> str:
    """标准化文本用于评估"""
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^\u4e00-\u9fff\w]", "", text)
    return text.strip()


def compute_bleu(references: list, predictions: list) -> dict:
    """计算BLEU-4分数

    Args:
        references: 参考文本列表
        predictions: 预测文本列表

    Returns:
        BLEU分数字典
    """
    logger.info(f"BLEU计算 - 样本总数: {len(references)}")
    logger.debug(
        "BLEU计算 - 参考文本预览(第1条,前100字): "
        f"{references[0][:100] if references else '空'}"
    )
    logger.debug(
        "BLEU计算 - 预测文本预览(第1条,前100字): "
        f"{predictions[0][:100] if predictions else '空'}"
    )

    try:
        import sacrebleu

        refs_for_bleu = [[r] for r in references]
        bleu = sacrebleu.corpus_bleu(predictions, refs_for_bleu)

        result = {
            "bleu": bleu.score,
            "bleu_1": (bleu.precisions[0] if hasattr(bleu, "precisions") else None),
            "bleu_2": (bleu.precisions[1] if hasattr(bleu, "precisions") else None),
            "bleu_3": (bleu.precisions[2] if hasattr(bleu, "precisions") else None),
            "bleu_4": (bleu.precisions[3] if hasattr(bleu, "precisions") else None),
        }

        logger.info("BLEU计算结果:")
        logger.info(f"  BLEU总体: {result['bleu']:.2f}")
        if result.get("bleu_1") is not None:
            logger.info(
                f"  BLEU-1: {result['bleu_1']:.2f}  "
                f"BLEU-2: {result['bleu_2']:.2f}  "
                f"BLEU-3: {result['bleu_3']:.2f}  "
                f"BLEU-4: {result['bleu_4']:.2f}"
            )
        logger.debug(f"BLEU - 长度惩罚BP: {bleu.bp if hasattr(bleu, 'bp') else 'N/A'}")
        logger.debug(
            "BLEU - sys_len="
            f"{bleu.sys_len if hasattr(bleu, 'sys_len') else 'N/A'}"
            ", ref_len="
            f"{bleu.ref_len if hasattr(bleu, 'ref_len') else 'N/A'}"
        )

        for i, (pred, ref) in enumerate(zip(predictions, references)):
            try:
                sent_bleu = sacrebleu.sentence_bleu(pred, [ref])
                logger.debug(
                    f"  BLEU逐条 - 样本[{i}]: {sent_bleu.score:.2f}  "
                    f"(pred_len={len(pred)}, ref_len={len(ref)})"
                )
            except Exception:
                pass

        return result
    except ImportError:
        logger.warning("sacrebleu未安装，使用回退方法计算BLEU")

        def bleu_score(candidate, reference):
            c_tokens = list(candidate)
            r_tokens = list(reference)

            matches = 0
            for i in range(len(c_tokens) - 3):
                ngram = tuple(c_tokens[i : i + 4])
                for j in range(len(r_tokens) - 3):
                    if tuple(r_tokens[j : j + 4]) == ngram:
                        matches += 1
                        break

            total = len(c_tokens) - 3 if len(c_tokens) > 3 else 1
            precision = matches / total if total > 0 else 0

            bp = (
                min(1.0, len(c_tokens) / max(len(r_tokens), 1))
                if len(r_tokens) > 0
                else 0
            )

            if precision > 0 and bp > 0:
                score = bp * np.exp(np.log(precision))
            else:
                score = 0.0

            return score * 100

        per_sample_scores = []
        for i, (p, r) in enumerate(zip(predictions, references)):
            p_norm = normalize_text(p)
            r_norm = normalize_text(r)
            s = bleu_score(p_norm, r_norm)
            per_sample_scores.append(s)
            logger.debug(
                f"BLEU回退 - 样本[{i}]: {s:.2f}  "
                f"(candidate_len={len(p_norm)}, "
                f"ref_len={len(r_norm)})"
            )

        avg_score = float(np.mean(per_sample_scores)) if per_sample_scores else 0.0
        logger.info(f"BLEU回退计算结果 - 平均: {avg_score:.2f}")

        return {
            "bleu": avg_score,
            "bleu_4": avg_score,
        }


def compute_rouge(references: list, predictions: list) -> dict:
    """计算ROUGE-L分数

    Args:
        references: 参考文本列表
        predictions: 预测文本列表

    Returns:
        ROUGE分数字典 (precision, recall, f1)
    """
    from rouge_score import rouge_scorer

    logger.info(f"ROUGE计算 - 样本总数: {len(references)}")
    logger.debug(
        "ROUGE计算 - 参考文本预览(第1条,前100字): "
        f"{references[0][:100] if references else '空'}"
    )
    logger.debug(
        "ROUGE计算 - 预测文本预览(第1条,前100字): "
        f"{predictions[0][:100] if predictions else '空'}"
    )

    scorer = rouge_scorer.RougeScorer(["rougeL", "rouge1", "rouge2"], use_stemmer=True)

    scores = {"rouge1": [], "rouge2": [], "rougeL": []}
    for i, (ref, pred) in enumerate(zip(references, predictions)):
        score = scorer.score(ref, pred)
        for key in scores:
            scores[key].append(
                {
                    "precision": score[key].precision,
                    "recall": score[key].recall,
                    "fmeasure": score[key].fmeasure,
                }
            )
        logger.debug(
            f"ROUGE逐条 - 样本[{i}]: "
            f"ROUGE-1={score['rouge1'].fmeasure:.4f}, "
            f"ROUGE-2={score['rouge2'].fmeasure:.4f}, "
            f"ROUGE-L={score['rougeL'].fmeasure:.4f}"
        )

    result = {}
    for key, values in scores.items():
        if values:
            result[key] = {
                "precision": float(np.mean([v["precision"] for v in values])),
                "recall": float(np.mean([v["recall"] for v in values])),
                "fmeasure": float(np.mean([v["fmeasure"] for v in values])),
            }
        else:
            result[key] = {"precision": 0.0, "recall": 0.0, "fmeasure": 0.0}

    logger.info("ROUGE计算结果:")
    logger.info(f"  ROUGE-1 F1: {result['rouge1']['fmeasure']:.4f}")
    logger.info(f"  ROUGE-2 F1: {result['rouge2']['fmeasure']:.4f}")
    logger.info(f"  ROUGE-L F1: {result['rougeL']['fmeasure']:.4f}")

    return result


def compute_bertscore(references: list, predictions: list, lang: str = "zh") -> dict:
    """计算BERTScore

    Args:
        references: 参考文本列表
        predictions: 预测文本列表
        lang: 语言代码

    Returns:
        BERTScore字典 (precision, recall, f1)
    """
    logger.info(f"BERTScore计算 - 样本总数: {len(references)}, 语言: {lang}")
    logger.debug(
        "BERTScore计算 - 参考文本预览(第1条,前100字): "
        f"{references[0][:100] if references else '空'}"
    )
    logger.debug(
        "BERTScore计算 - 预测文本预览(第1条,前100字): "
        f"{predictions[0][:100] if predictions else '空'}"
    )

    ref_lens = [len(r) for r in references]
    pred_lens = [len(p) for p in predictions]
    logger.debug(
        "BERTScore - 参考文本长度: "
        f"min={min(ref_lens)}, max={max(ref_lens)}, "
        f"avg={np.mean(ref_lens):.0f}"
    )
    logger.debug(
        "BERTScore - 预测文本长度: "
        f"min={min(pred_lens)}, max={max(pred_lens)}, "
        f"avg={np.mean(pred_lens):.0f}"
    )

    try:
        from bert_score import score

        logger.info("BERTScore开始计算（这可能较慢，需要下载bert-base-chinese模型）...")
        start_time = time.time()
        P, R, F1 = score(predictions, references, lang=lang, verbose=True)
        elapsed = time.time() - start_time

        precision_mean = float(P.mean().item())
        recall_mean = float(R.mean().item())
        f1_mean = float(F1.mean().item())

        precision_list = [float(p) for p in P.tolist()]
        recall_list = [float(r) for r in R.tolist()]
        f1_list = [float(f) for f in F1.tolist()]

        logger.info(f"BERTScore计算完成 (耗时={elapsed:.2f}秒):")
        logger.info(f"  Precision: {precision_mean:.4f}")
        logger.info(f"  Recall:    {recall_mean:.4f}")
        logger.info(f"  F1:        {f1_mean:.4f}")

        for i in range(len(f1_list)):
            logger.debug(
                f"  BERTScore逐条 - 样本[{i}]: "
                f"F1={f1_list[i]:.4f}, "
                f"P={precision_list[i]:.4f}, "
                f"R={recall_list[i]:.4f}"
            )

        low_score_idxs = [
            i for i, f in enumerate(f1_list) if f < np.percentile(f1_list, 25)
        ]
        if low_score_idxs:
            logger.debug(f"BERTScore低分样本(后25%): 样本索引={low_score_idxs}")
            for idx in low_score_idxs[:3]:
                logger.debug(f"BERTScore低分样本[{idx}]: F1={f1_list[idx]:.4f}")
                logger.debug(f"    参考: {references[idx][:150]}")
                logger.debug(f"    预测: {predictions[idx][:150]}")

        return {
            "precision": precision_mean,
            "recall": recall_mean,
            "f1": f1_mean,
            "precision_list": precision_list,
            "recall_list": recall_list,
            "f1_list": f1_list,
        }
    except Exception as e:
        logger.error(f"BERTScore计算失败: {e}")
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "error": str(e),
        }


def compute_domain_term_accuracy(references: list, predictions: list) -> dict:
    """计算领域术语准确率

    评估方法:
    1. 定义领域术语库 (DOMAIN_TERMS)
    2. 计算每条样本中术语的使用准确率
    3. 统计术语召回率、精确率和F1

    Args:
        references: 参考文本列表
        predictions: 预测文本列表

    Returns:
        领域术语评估结果
    """
    logger.info(
        "领域术语准确率计算 - "
        f"样本总数: {len(references)}, "
        f"术语库大小: {len(DOMAIN_TERMS)}"
    )
    logger.debug(f"领域术语库列表: {DOMAIN_TERMS}")
    logger.debug(f"同义词映射: {json.dumps(DOMAIN_TERM_SYNONYMS, ensure_ascii=False)}")

    term_stats = {}

    for term in DOMAIN_TERMS:
        term_stats[term] = {
            "ref_count": 0,
            "pred_count": 0,
            "correct_count": 0,
        }

    per_sample_scores = []

    for i, (ref, pred) in enumerate(zip(references, predictions)):
        ref_normalized = normalize_text(ref)
        pred_normalized = normalize_text(pred)

        sample_terms_ref = set()
        sample_terms_pred = set()
        sample_terms_correct = set()

        for term in DOMAIN_TERMS:
            term_normalized = normalize_text(term)

            in_ref = term_normalized in ref_normalized
            in_pred = term_normalized in pred_normalized

            if in_ref:
                term_stats[term]["ref_count"] += 1
                sample_terms_ref.add(term)

            if in_pred:
                term_stats[term]["pred_count"] += 1
                sample_terms_pred.add(term)

            if in_ref and in_pred:
                term_stats[term]["correct_count"] += 1
                sample_terms_correct.add(term)

        for base_term, synonyms in DOMAIN_TERM_SYNONYMS.items():
            base_normalized = normalize_text(base_term)
            syn_normalized = [normalize_text(s) for s in synonyms]

            in_ref = any(
                s in ref_normalized for s in [base_normalized] + syn_normalized
            )
            in_pred = any(
                s in pred_normalized for s in [base_normalized] + syn_normalized
            )

            if in_ref:
                sample_terms_ref.add(base_term)
            if in_pred:
                sample_terms_pred.add(base_term)
            if in_ref and in_pred:
                sample_terms_correct.add(base_term)

        missing_terms = sample_terms_ref - sample_terms_correct
        extra_terms = sample_terms_pred - sample_terms_correct

        logger.debug(
            f"领域术语逐条 - 样本[{i}]: "
            f"ref_terms={len(sample_terms_ref)}, "
            f"pred_terms={len(sample_terms_pred)}, "
            f"correct={len(sample_terms_correct)}, "
            f"missing={list(missing_terms)[:5]}, "
            f"extra={list(extra_terms)[:5]}"
        )

        if len(sample_terms_ref) > 0:
            precision = len(sample_terms_correct) / max(len(sample_terms_pred), 1)
            recall = len(sample_terms_correct) / len(sample_terms_ref)
            f1 = (
                (2 * precision * recall / (precision + recall))
                if (precision + recall) > 0
                else 0
            )
            per_sample_scores.append(
                {
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "ref_terms": list(sample_terms_ref),
                    "pred_terms": list(sample_terms_pred),
                    "correct_terms": list(sample_terms_correct),
                }
            )
            logger.debug(
                f"领域术语分数 - 样本[{i}]: "
                f"P={precision:.4f}, R={recall:.4f}, "
                f"F1={f1:.4f}"
            )
        else:
            logger.debug(f"领域术语 - 样本[{i}]: 参考文本中未发现任何领域术语")

    total_ref = sum(ts["ref_count"] for ts in term_stats.values())
    total_pred = sum(ts["pred_count"] for ts in term_stats.values())
    total_correct = sum(ts["correct_count"] for ts in term_stats.values())

    overall_precision = total_correct / max(total_pred, 1)
    overall_recall = total_correct / max(total_ref, 1)
    if (overall_precision + overall_recall) > 0:
        f1_numerator = 2 * overall_precision * overall_recall
        f1_denominator = overall_precision + overall_recall
        overall_f1 = f1_numerator / f1_denominator
    else:
        overall_f1 = 0

    freq_terms = sorted(
        [(term, stats) for term, stats in term_stats.items() if stats["ref_count"] > 0],
        key=lambda x: x[1]["ref_count"],
        reverse=True,
    )

    logger.info("领域术语准确率计算结果:")
    logger.info(
        f"  总体 P={overall_precision:.4f}, R={overall_recall:.4f}, F1={overall_f1:.4f}"
    )
    logger.info(
        "  总参考术语数="
        f"{total_ref}, "
        "总预测术语数="
        f"{total_pred}, "
        "正确匹配="
        f"{total_correct}"
    )
    logger.debug("高频术语Top10:")
    for term, stats in freq_terms[:10]:
        logger.debug(
            f"  '{term}': "
            f"ref={stats['ref_count']}, "
            f"pred={stats['pred_count']}, "
            f"correct={stats['correct_count']}"
        )

    zero_ref_terms = [
        term
        for term, stats in term_stats.items()
        if stats["ref_count"] == 0 and stats["pred_count"] > 0
    ]
    if zero_ref_terms:
        logger.debug(f"术语库中参考未出现但预测出现的术语: {zero_ref_terms}")

    return {
        "overall": {
            "precision": overall_precision,
            "recall": overall_recall,
            "f1": overall_f1,
            "total_reference_terms": total_ref,
            "total_predicted_terms": total_pred,
            "total_correct_terms": total_correct,
        },
        "per_sample_avg": {
            "precision": float(np.mean([s["precision"] for s in per_sample_scores])),
            "recall": float(np.mean([s["recall"] for s in per_sample_scores])),
            "f1": float(np.mean([s["f1"] for s in per_sample_scores])),
        },
        "top_terms": [
            {
                "term": term,
                "ref_count": stats["ref_count"],
                "pred_count": stats["pred_count"],
                "correct_count": stats["correct_count"],
            }
            for term, stats in freq_terms[:20]
        ],
        "evaluation_method": (
            "领域术语准确率评估方法:\n"
            "1. 术语库: 包含80个帮信罪领域专业术语\n"
            "2. 评估流程: 对每条样本，统计参考文本和"
            "预测文本中术语的出现情况\n"
            "3. 同义词处理: 对常见同义词"
            "（如帮信罪/帮助信息网络犯罪活动罪）"
            "进行归一化匹配\n"
            "4. 指标计算: 术语精确率=正确预测术语数/"
            "预测术语总数, "
            "术语召回率=正确预测术语数/参考术语总数, "
            "术语F1=2*P*R/(P+R)"
        ),
    }


def compute_auto_metrics(references: list, predictions: list) -> dict:
    """计算所有自动评估指标

    Args:
        references: 参考文本列表
        predictions: 预测文本列表

    Returns:
        所有评估指标的综合字典
    """
    metrics = {}

    logger.info("=" * 50)
    logger.info("开始计算自动评估指标")
    logger.info(f"  参考文本数: {len(references)}")
    logger.info(f"  预测文本数: {len(predictions)}")
    logger.info("=" * 50)

    logger.info("[1/4] 计算BLEU-4...")
    metrics["bleu"] = compute_bleu(references, predictions)

    logger.info("[2/4] 计算ROUGE...")
    metrics["rouge"] = compute_rouge(references, predictions)

    logger.info("[3/4] 计算BERTScore...")
    metrics["bert_score"] = compute_bertscore(references, predictions)

    logger.info("[4/4] 计算领域术语准确率...")
    metrics["domain_term_accuracy"] = compute_domain_term_accuracy(
        references, predictions
    )

    logger.info("=" * 50)
    logger.info("自动评估指标计算完成")
    logger.info("=" * 50)

    return metrics


def design_human_evaluation_protocol() -> dict:
    """设计人工评估（盲测）方案

    返回人工评估的完整方案设计文档
    """
    protocol = {
        "evaluation_name": "LoRA微调模型人工盲测评估方案",
        "objective": ("通过人工盲测评估微调模型在帮信罪案件主观明知分析任务上的表现"),
        "method": "双盲A/B测试",
        "participants": {
            "requirement": ("3-5名具有法律背景的评估员（法学专业学生或法律从业者）"),
            "training": ("评估员需接受30分钟培训，了解评估标准和评分细则"),
            "blind_condition": ("评估员不知道哪份输出来自微调模型，哪份来自基线模型"),
        },
        "test_set": {
            "size": "从测试集中随机抽取30-50条样本",
            "composition": ("确保包含三类案件（明知/不明知/边缘）各10-15条"),
            "presentation": ("每次展示案件文本和两份匿名输出（A和B）"),
        },
        "scoring_criteria": {
            "维度一_准确性": {
                "weight": 0.4,
                "description": ("分析结论与案件事实的匹配程度"),
                "scale": "1-5分",
                "rubric": {
                    5: "分析完全准确，结论与案件事实高度一致",
                    4: "分析基本准确，存在轻微偏差",
                    3: ("分析部分准确，存在明显偏差但核心结论正确"),
                    2: "分析偏差较大，核心结论有误",
                    1: "分析完全错误或无关",
                },
            },
            "维度二_完整性": {
                "weight": 0.25,
                "description": ("分析是否覆盖了案件的核心要素"),
                "scale": "1-5分",
                "rubric": {
                    5: ("覆盖所有核心要素（行为、认知、辩解），论证充分"),
                    4: ("覆盖大部分核心要素，缺少个别次要要素"),
                    3: "覆盖核心要素但不充分",
                    2: "仅覆盖少数要素",
                    1: "未覆盖核心要素",
                },
            },
            "维度三_专业性": {
                "weight": 0.2,
                "description": ("法律术语使用和专业表达水平"),
                "scale": "1-5分",
                "rubric": {
                    5: "术语使用准确规范，表达专业流畅",
                    4: "术语使用基本准确，表达较专业",
                    3: "术语使用部分准确，表达一般",
                    2: "术语使用不准确，表达不够专业",
                    1: "术语使用错误，表达不专业",
                },
            },
            "维度四_可读性": {
                "weight": 0.15,
                "description": "输出的结构和可理解性",
                "scale": "1-5分",
                "rubric": {
                    5: "结构清晰，逻辑连贯，易于理解",
                    4: "结构较清晰，逻辑较为连贯",
                    3: "结构一般，逻辑基本连贯",
                    2: "结构混乱，逻辑不清晰",
                    1: "无法理解",
                },
            },
        },
        "evaluation_form": {
            "for_each_sample": [
                "展示案件文本",
                "展示输出A和输出B（匿名随机标记）",
                "评估员对A和B分别打分（四个维度）",
                "评估员选择偏好（A优于B / B优于A / 相当）",
                "评估员提供简要评语（可选）",
            ],
        },
        "metrics_calculation": {
            "overall_score": "各维度加权平均分（权重如上）",
            "preference_rate": "偏好A/B的比例",
            "inter_rater_agreement": ("使用Fleiss' Kappa评估员间一致性"),
            "win_rate": "微调模型vs基线模型的胜率",
        },
        "minimum_requirements": {
            "samples_for_significance": "至少30条评估样本",
            "evaluators_needed": "至少3名评估员",
            "acceptable_agreement": "Fleiss' Kappa >= 0.6",
        },
        "report_template": {
            "overall_scores": ("微调模型和基线模型在各维度的平均分"),
            "win_rate_analysis": ("微调模型在不同类型案件上的胜率"),
            "error_analysis": "典型错误类型和频次统计",
            "recommendations": "基于人工评估的改进建议",
        },
    }

    return protocol


def compare_with_baseline(
    finetuned_results: dict,
    base_results: dict = None,
) -> dict:
    """对比微调模型与基线模型的结果

    Args:
        finetuned_results: 微调模型评估结果
        base_results: 基线模型评估结果

    Returns:
        对比分析结果
    """
    comparison = {}

    logger.info("=" * 50)
    logger.info("微调模型 vs 基线模型对比分析")

    if base_results:
        logger.info("基线模型结果可用，开始逐指标对比")
    else:
        logger.info("未提供基线模型结果，跳过对比")
        logger.info("可通过设置环境变量 EVAL_BASELINE=true 开启基线对比")
        logger.info("=" * 50)
        return comparison

    if base_results:
        for metric_key in [
            "bleu",
            "rouge",
            "bert_score",
            "domain_term_accuracy",
        ]:
            if metric_key in finetuned_results and metric_key in base_results:
                logger.info(f"对比 - {metric_key}:")
                comparison[metric_key] = {
                    "finetuned": finetuned_results[metric_key],
                    "baseline": base_results[metric_key],
                    "improvement": {},
                }

                if metric_key == "bleu":
                    ft_score = finetuned_results[metric_key].get("bleu", 0)
                    base_score = base_results[metric_key].get("bleu", 0)
                    delta = ft_score - base_score
                    pct = (delta / max(base_score, 0.001)) * 100
                    direction = "提升" if delta > 0 else "下降"
                    comparison[metric_key]["improvement"] = {
                        "delta": delta,
                        "delta_pct": pct,
                        "direction": direction,
                    }
                    logger.info(
                        f"  BLEU: 微调={ft_score:.2f} "
                        f"vs 基线={base_score:.2f} "
                        f"→ {direction}{abs(delta):.2f} "
                        f"({pct:+.2f}%)"
                    )

                elif metric_key == "rouge":
                    for sub_key in ["rougeL", "rouge1", "rouge2"]:
                        ft_f1 = (
                            finetuned_results[metric_key]
                            .get(sub_key, {})
                            .get("fmeasure", 0)
                        )
                        base_f1 = (
                            base_results[metric_key].get(sub_key, {}).get("fmeasure", 0)
                        )
                        delta = ft_f1 - base_f1
                        pct = (delta / max(base_f1, 0.001)) * 100
                        direction = "提升" if delta > 0 else "下降"
                        comparison[metric_key]["improvement"][sub_key] = {
                            "delta": delta,
                            "delta_pct": pct,
                            "direction": direction,
                        }
                        logger.info(
                            f"  {sub_key} F1: "
                            f"微调={ft_f1:.4f} "
                            f"vs 基线={base_f1:.4f} "
                            f"→ {direction}"
                            f"{abs(delta):.4f} "
                            f"({pct:+.2f}%)"
                        )

                elif metric_key == "bert_score":
                    ft_f1 = finetuned_results[metric_key].get("f1", 0)
                    base_f1 = base_results[metric_key].get("f1", 0)
                    delta = ft_f1 - base_f1
                    pct = (delta / max(base_f1, 0.001)) * 100
                    direction = "提升" if delta > 0 else "下降"
                    comparison[metric_key]["improvement"]["f1"] = {
                        "delta": delta,
                        "delta_pct": pct,
                        "direction": direction,
                    }
                    logger.info(
                        "  BERTScore F1: "
                        f"微调={ft_f1:.4f} "
                        f"vs 基线={base_f1:.4f} "
                        f"→ {direction}"
                        f"{abs(delta):.4f} "
                        f"({pct:+.2f}%)"
                    )

                elif metric_key == "domain_term_accuracy":
                    for sub_key in ["precision", "recall", "f1"]:
                        ft_val = (
                            finetuned_results[metric_key]
                            .get("overall", {})
                            .get(sub_key, 0)
                        )
                        base_val = (
                            base_results[metric_key].get("overall", {}).get(sub_key, 0)
                        )
                        delta = ft_val - base_val
                        pct = (delta / max(base_val, 0.001)) * 100
                        direction = "提升" if delta > 0 else "下降"
                        comparison[metric_key]["improvement"][sub_key] = {
                            "delta": delta,
                            "delta_pct": pct,
                            "direction": direction,
                        }
                        logger.info(
                            f"  术语{sub_key}: "
                            f"微调={ft_val:.4f} "
                            f"vs 基线={base_val:.4f} "
                            f"→ {direction}"
                            f"{abs(delta):.4f} "
                            f"({pct:+.2f}%)"
                        )

    logger.info("=" * 50)
    return comparison


def save_evaluation_results(results: dict, output_path: str):
    """保存评估结果到JSON文件

    Args:
        results: 评估结果字典
        output_path: 输出路径
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    serializable_results = json.loads(
        json.dumps(results, default=str, ensure_ascii=False)
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serializable_results, f, ensure_ascii=False, indent=2)

    logger.info(f"评估结果已保存至: {output_path}")


def print_evaluation_summary(results: dict):
    """打印评估结果摘要"""
    logger.info("=" * 70)
    logger.info("模型评估结果摘要")
    logger.info("=" * 70)

    if "auto_metrics" in results:
        metrics = results["auto_metrics"]
    else:
        metrics = results

    if "bleu" in metrics:
        bleu = metrics["bleu"]
        logger.info(f"BLEU-4: {bleu.get('bleu', 'N/A'):.2f}")
        try:
            logger.info(f"  BLEU-1: {bleu.get('bleu_1', 0):.2f}")
            logger.info(f"  BLEU-2: {bleu.get('bleu_2', 0):.2f}")
            logger.info(f"  BLEU-3: {bleu.get('bleu_3', 0):.2f}")
            logger.info(f"  BLEU-4: {bleu.get('bleu_4', 0):.2f}")
        except Exception:
            pass

    if "rouge" in metrics:
        rouge = metrics["rouge"]
        logger.info(f"ROUGE-1 F1: {rouge.get('rouge1', {}).get('fmeasure', 'N/A'):.4f}")
        logger.info(f"ROUGE-2 F1: {rouge.get('rouge2', {}).get('fmeasure', 'N/A'):.4f}")
        logger.info(f"ROUGE-L F1: {rouge.get('rougeL', {}).get('fmeasure', 'N/A'):.4f}")

    if "bert_score" in metrics:
        bs = metrics["bert_score"]
        logger.info(f"BERTScore F1: {bs.get('f1', 'N/A'):.4f}")
        logger.info(f"BERTScore Precision: {bs.get('precision', 'N/A'):.4f}")
        logger.info(f"BERTScore Recall: {bs.get('recall', 'N/A'):.4f}")

    if "domain_term_accuracy" in metrics:
        dta = metrics["domain_term_accuracy"]
        overall = dta.get("overall", {})
        logger.info(f"领域术语精确率: {overall.get('precision', 'N/A'):.4f}")
        logger.info(f"领域术语召回率: {overall.get('recall', 'N/A'):.4f}")
        logger.info(f"领域术语F1: {overall.get('f1', 'N/A'):.4f}")

    if "comparison" in results and results["comparison"]:
        logger.info("-" * 40)
        logger.info("与基线模型对比:")
        for metric_key, comp_data in results["comparison"].items():
            improvements = comp_data.get("improvement", {})
            for sub_key, delta_info in improvements.items():
                is_valid_delta = isinstance(delta_info, dict)
                if is_valid_delta and "direction" in delta_info:
                    delta_val = delta_info.get("delta", 0)
                    logger.info(
                        f"  {metric_key}/{sub_key}: "
                        f"{delta_val:+.4f} "
                        f"({delta_info.get('direction', 'N/A')})"
                    )

    if "human_evaluation_protocol" in results:
        logger.info("-" * 40)
        logger.info("人工评估方案: 已设计 (见评估报告)")

    logger.info("=" * 70)


def evaluate():
    """执行模型评估主流程"""
    setup_logging()

    logger.info("=" * 70)
    logger.info("LoRA微调模型评估 - 启动")
    logger.info("=" * 70)

    config = load_config()

    test_data_path = config.get("data", {}).get("eval_data_path", "")
    if not test_data_path or not os.path.exists(test_data_path):
        alt_paths = [
            str(PROJECT_ROOT / "data" / "training" / "processed.jsonl"),
            str(PROJECT_ROOT / "data" / "eval.json"),
            str(PROJECT_ROOT / "data" / "eval.jsonl"),
            str(PROJECT_ROOT / "data" / "test.json"),
        ]
        for p in alt_paths:
            if os.path.exists(p):
                test_data_path = p
                logger.info(f"使用备选测试数据路径: {test_data_path}")
                break

    if not test_data_path or not os.path.exists(test_data_path):
        logger.error("测试数据文件不存在")
        sys.exit(1)

    max_samples = int(os.environ.get("EVAL_MAX_SAMPLES", "20"))
    test_samples = load_test_data(test_data_path, max_samples=max_samples)

    if not test_samples:
        logger.error("测试数据集为空")
        sys.exit(1)

    lora_adapter_path = os.path.join(str(LORA_WEIGHTS_DIR), "final")
    if not os.path.exists(lora_adapter_path):
        logger.warning(f"LoRA适配器路径不存在: {lora_adapter_path}")
        lora_adapter_path = str(LORA_WEIGHTS_DIR)

    logger.info("加载微调模型...")
    finetuned_model, finetuned_tokenizer = load_finetuned_model(
        config, lora_adapter_path
    )

    env_baseline = os.environ.get("EVAL_BASELINE", "false").lower()
    do_baseline = env_baseline == "true"
    base_model, base_tokenizer = None, None
    if do_baseline:
        logger.info("加载基线模型（基础模型无LoRA）...")
        base_model, base_tokenizer = load_base_model(config)

    logger.info(f"开始推理评估 ({len(test_samples)}条样本)...")

    finetuned_predictions = []
    for i, sample in enumerate(test_samples):
        logger.info(f"微调模型推理 [{i + 1}/{len(test_samples)}]...")
        logger.debug(f"  样本[{i}] prompt: {sample['prompt'][:80]}...")
        if sample.get("input"):
            logger.debug(f"  样本[{{i}}] input(前150字): {sample['input'][:150]}...")
        logger.debug(f"  样本[{i}] reference(前150字): {sample['reference'][:150]}...")

        response = generate_response(
            finetuned_model,
            finetuned_tokenizer,
            sample["prompt"],
            sample["input"],
        )
        finetuned_predictions.append(response)

        logger.debug(f"  样本[{i}] 微调预测(前150字): {response[:150]}...")

    base_predictions = None
    if base_model:
        base_predictions = []
        for i, sample in enumerate(test_samples):
            logger.info(f"基线模型推理 [{i + 1}/{len(test_samples)}]...")
            response = generate_response(
                base_model,
                base_tokenizer,
                sample["prompt"],
                sample["input"],
            )
            base_predictions.append(response)
            logger.debug(f"  样本[{i}] 基线预测(前150字): {response[:150]}...")

    references = [s["reference"] for s in test_samples]

    logger.info("计算自动评估指标...")
    logger.info(
        f"评估数据: {len(references)}条参考文本 vs "
        f"{len(finetuned_predictions)}条微调模型预测"
    )
    finetuned_metrics = compute_auto_metrics(references, finetuned_predictions)

    base_metrics = None
    if base_predictions:
        logger.info("计算基线模型评估指标...")
        base_metrics = compute_auto_metrics(references, base_predictions)

    comparison = compare_with_baseline(finetuned_metrics, base_metrics)

    human_eval_protocol = design_human_evaluation_protocol()

    results = {
        "evaluation_name": "LoRA微调模型评估",
        "evaluation_time": datetime.now().isoformat(),
        "config": {
            "model": config["model"]["model_name_or_path"],
            "lora_adapter": lora_adapter_path,
            "test_samples": len(test_samples),
            "baseline_comparison": do_baseline,
            "metrics": [
                "BLEU-4",
                "ROUGE-L",
                "BERTScore",
                "领域术语准确率",
            ],
        },
        "auto_metrics": finetuned_metrics,
        "base_metrics": base_metrics,
        "comparison": comparison,
        "human_evaluation_protocol": human_eval_protocol,
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = str(REPORTS_DIR / f"evaluation_results_{timestamp}.json")
    save_evaluation_results(results, output_path)

    print_evaluation_summary(results)

    logger.info("")
    logger.info(f"详细评估结果文件: {output_path}")
    logger.info("评估完成!")

    return results


if __name__ == "__main__":
    evaluate()

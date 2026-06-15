"""出价后端：DeepSeek（OpenAI 兼容）真实调用 + Mock 离线模拟。

注意：deepseek-v4-flash 是带思考的模型，会返回 reasoning_content（推理）+ content（最终答案）。
必须给足 max_tokens，否则正文会被推理挤空。我们把推理也存下来供报告展示。
"""
import os
import re
import json
import time
import random

from prompts import build_prompt


def parse_bid(text):
    """从模型文本里稳健地解析出价。返回 (bid或None, reason, valid)。"""
    if not text:
        return None, "", False
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            for k in ("bid", "drop_out_price", "price", "amount"):
                if k in obj and isinstance(obj[k], (int, float)):
                    return float(obj[k]), str(obj.get("reason", "")), True
            for v in obj.values():           # 兜底：取第一个数值
                if isinstance(v, (int, float)):
                    return float(v), str(obj.get("reason", "")), True
        except Exception:
            pass
    m2 = re.search(r"-?\d+(?:\.\d+)?", text)  # 兜底：抓第一个数字
    if m2:
        return float(m2.group(0)), "", True
    return None, text[:200], False


class DeepSeekBidder:
    """真实调用 DeepSeek / 任意 OpenAI 兼容平台。线程安全，可并发。"""

    def __init__(self, model, base_url, api_key_env, temperature, max_tokens=512):
        from openai import OpenAI
        key = os.environ.get(api_key_env)
        if not key:
            raise RuntimeError(f"环境变量 {api_key_env} 未设置：请先 export {api_key_env}=sk-xxx")
        self.client = OpenAI(api_key=key, base_url=base_url, timeout=120, max_retries=0)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def bid(self, cond):
        prompt = build_prompt(**cond)
        for attempt in range(4):
            try:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                msg = r.choices[0].message
                text = msg.content or ""
                reasoning = getattr(msg, "reasoning_content", "") or ""
                b, reason, ok = parse_bid(text)
                return {"raw_response": text, "reasoning": reasoning, "parsed_bid": b,
                        "reason": reason, "valid": ok, "refused": not ok}
            except Exception as e:                       # 网络/限流：指数退避重试
                if attempt == 3:
                    return {"raw_response": f"ERROR: {e}", "reasoning": "", "parsed_bid": None,
                            "reason": "", "valid": False, "refused": True}
                time.sleep(2 ** attempt)


class MockBidder:
    """离线模拟：带噪声的行为模型，用来跑通流程、做演示。
    设计成「会压价但压得不够」——这是 LLM 常见的可讨论现象。"""

    def __init__(self, seed=42):
        self.rng = random.Random(seed)

    def bid(self, cond):
        v, n = cond["value"], cond["n"]
        mech, persona, framing = cond["mechanism"], cond["persona"], cond["framing"]
        alpha = {"naive": 0.8, "business": 0.5, "game_theorist": 0.2}[persona]
        if framing == "reason_hint":
            alpha *= 0.6
        if mech in ("second_price", "english"):
            center = v * (1.03 if persona == "naive" else 1.0)
            b = max(0.0, center + self.rng.gauss(0, 0.04 * v + 1))
        else:
            s = (n - 1) / n
            factor = s + alpha * (1 - s)
            b = max(0.0, v * factor + self.rng.gauss(0, 0.05 * v))
            b = min(b, v * 1.05)
        b = round(b, 2)
        return {"raw_response": json.dumps({"bid": b, "reason": "(mock)"}), "reasoning": "",
                "parsed_bid": b, "reason": "(mock)", "valid": True, "refused": False}


def make_bidder(provider, cfg):
    if provider == "mock":
        return MockBidder(seed=cfg.get("SEED", 42))
    return DeepSeekBidder(cfg["MODEL"], cfg["BASE_URL"], cfg["API_KEY_ENV"],
                          cfg["TEMPERATURE"], cfg.get("MAX_TOKENS", 512))

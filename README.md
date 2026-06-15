# 大模型 Agent 的拍卖出价行为 — 实验代码

数字经济下的市场设计 · 小组作业选题①。把 LLM 当拍卖参与者，检验其出价是否符合博弈论预测。

## 目录
```
experiment_design.md   实验设计（研究问题/基准/变量/指标）
config.py              实验网格配置
prompts.py             prompt 模板（人设+机制规则）
bidder.py              出价后端：DeepSeek 真实调用 + Mock 离线模拟
run_experiment.py      主循环 -> data/bids.csv（可断点续跑）
analyze.py             指标 + 2x2 总览图 -> figures/summary.png
report_draft.md        报告初稿骨架（按作业要求7节）
```

## 快速开始

```bash
pip install -r requirements.txt

# 1) 先用离线 Mock 跑通整条流程（不花钱、不需要 key）
python run_experiment.py --provider mock
python analyze.py                      # 看 figures/summary.png 和终端指标

# 2) 换成真实模型（DeepSeek，或任意 OpenAI 兼容平台）
export DEEPSEEK_API_KEY=sk-xxxxxxxx
python run_experiment.py --provider deepseek
python analyze.py
```

换平台（通义千问 DashScope / SiliconFlow 等）只需改 `config.py` 里的
`MODEL / BASE_URL / API_KEY_ENV`。

## 小贴士
- `--limit 20` 先跑前 20 条做冒烟测试；`--n-values` 调每格估值数量。
- 主实验 `temperature=0` 可复现；想看随机性把 `config.TEMPERATURE` 调到 1.0 另存一份。
- `run_experiment.py` 支持**断点续跑**：中断后重跑会跳过已完成的 run_id。
- 不要上传真实隐私/商业数据；本实验估值全是合成的。

## 分工建议（3–5 人）
设计/理论基准 · prompt+调 API · 数据分析+画图 · 文献+局限性+写作。

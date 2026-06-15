"""实验网格配置。命令行参数可覆盖部分项。"""

VALUE_MAX = 100          # 估值上界（U[5, VALUE_MAX]）
SEED = 42

MECHANISMS = ["second_price", "first_price"]   # 可加 "english"
N_BIDDERS = [2, 3, 5]
PERSONAS = ["naive", "business", "game_theorist"]
FRAMINGS = ["rules_only", "reason_hint"]
N_VALUES = 30            # 每个 cell 抽取的私人估值数量
TEMPERATURE = 0.0        # 主实验用 0 保证可复现

# ---- DeepSeek / OpenAI 兼容 ----
MODEL = "deepseek-v4-flash"   # 带思考模型：会返回 reasoning_content + content
MAX_TOKENS = 8192             # all-pay 个别推理很长，留足余量防截断
BASE_URL = "https://api.deepseek.com"
API_KEY_ENV = "DEEPSEEK_API_KEY"   # 运行前： export DEEPSEEK_API_KEY=sk-xxx

OUT_CSV = "data/bids.csv"

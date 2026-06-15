"""分析与画图：读 bids.csv -> 指标 + 2x2 总览图 + 分条件汇总表。

用法： python analyze.py            （默认读 data/bids.csv，出 figures/summary.png）
"""
import os
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def fit_through_origin(x, y):
    """拟合 y = beta * x，返回 (beta, R^2)。"""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    beta = np.sum(x * y) / np.sum(x * x)
    yhat = beta * x
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return beta, r2


def simulate_revenue(df, mech, n, draws=5000, seed=0):
    """用【相同 n 下】的经验出价分布，蒙特卡洛模拟 n 人拍卖的期望收入。"""
    sub = df[(df["mechanism"] == mech) & (df["n"] == n)]
    if len(sub) < 2:
        return float("nan")
    rng = np.random.default_rng(seed)
    bids = sub["parsed_bid"].to_numpy(float)
    rev = []
    for _ in range(draws):
        sample = np.sort(rng.choice(bids, size=n, replace=True))
        rev.append(sample[-2] if mech == "second_price" else sample[-1])
    return float(np.mean(rev))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/bids.csv")
    ap.add_argument("--fig", default="figures/summary.png")
    ap.add_argument("--summary", default="data/summary_by_condition.csv")
    args = ap.parse_args()

    df = pd.read_csv(args.inp)
    n_total = len(df)
    df = df[df["valid"].astype(str).isin(["True", "true", "1"])].copy()
    for col in ("parsed_bid", "value", "theory_bid", "n"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["parsed_bid", "value"])
    df = df[df["value"] > 0]
    df["ratio"] = df["parsed_bid"] / df["value"]
    df["dev"] = df["parsed_bid"] - df["theory_bid"]
    print(f"=== 有效样本 {len(df)}/{n_total}（按机制）===")
    print(df.groupby("mechanism").size().to_string())

    spa = df[df["mechanism"] == "second_price"]
    fpa = df[df["mechanism"] == "first_price"]

    if len(spa):
        truthful = (np.abs(spa["parsed_bid"] - spa["value"]) / spa["value"] <= 0.05).mean()
        overbid = (spa["parsed_bid"] > spa["value"]).mean()
        print(f"\n[二价] 如实出价率(±5%): {truthful:.1%}   过度出价率(b>v): {overbid:.1%}   "
              f"平均 b/v: {spa['ratio'].mean():.3f}")

    fpa_rows = []
    if len(fpa):
        print("\n[一价] 拟合压价系数 beta (b=beta*v) vs 理论 (n-1)/n：")
        for n, g in fpa.groupby("n"):
            beta, r2 = fit_through_origin(g["value"], g["parsed_bid"])
            theory = (n - 1) / n
            print(f"  n={int(n)}: beta={beta:.3f}  理论={theory:.3f}  差={beta - theory:+.3f}  R^2={r2:.3f}")
            fpa_rows.append((int(n), beta, theory))

    print("\n[收入等价] 用各机制在【相同 n】下的经验出价模拟期望收入：")
    for n in sorted(df["n"].dropna().unique()):
        n = int(n)
        rs = simulate_revenue(df, "second_price", n)
        rf = simulate_revenue(df, "first_price", n)
        th = (n - 1) / (n + 1) * 100
        print(f"  n={n}: 二价={rs:.2f}  一价={rf:.2f}  理论={th:.2f}")

    # 分条件汇总表（供报告引用）
    summ = (df.groupby(["mechanism", "n", "persona", "framing"])
              .agg(n_obs=("parsed_bid", "size"),
                   mean_ratio=("ratio", "mean"),
                   mean_abs_dev=("dev", lambda s: s.abs().mean()))
              .reset_index().round(3))
    summ.to_csv(args.summary, index=False)
    print(f"\n分条件汇总表已存：{args.summary}（{len(summ)} 行）")

    # ---------- 2x2 总览图 ----------
    fig, ax = plt.subplots(2, 2, figsize=(11, 8))
    vmax = df["value"].max() * 1.05
    lim = [0, vmax]

    a = ax[0, 0]
    if len(spa):
        a.scatter(spa["value"], spa["parsed_bid"], s=10, alpha=.45, label="LLM bids")
    a.plot(lim, lim, "r--", label="theory  b=v")
    a.set(title="Second-price: bid vs value", xlabel="value v", ylabel="bid b", xlim=lim, ylim=lim)
    a.legend(fontsize=8)

    a = ax[0, 1]
    for n, g in fpa.groupby("n"):
        a.scatter(g["value"], g["parsed_bid"], s=10, alpha=.35, label=f"n={int(n)}")
    vs = np.linspace(0, df["value"].max(), 50)
    for n in sorted(fpa["n"].unique()):
        a.plot(vs, vs * (n - 1) / n, "--", lw=1)
    a.set(title="First-price: bid vs value (dashed = theory)", xlabel="value v", ylabel="bid b")
    a.legend(fontsize=8)

    a = ax[1, 0]
    labels, vals = [], []
    for mech, tag in [("second_price", "SPA"), ("first_price", "FPA")]:
        for p in ["naive", "business", "game_theorist"]:
            sub = df[(df["mechanism"] == mech) & (df["persona"] == p)]
            if len(sub):
                labels.append(f"{tag}\n{p}")
                vals.append(sub["dev"].abs().mean())
    if vals:
        a.bar(range(len(vals)), vals, color="#4C78A8")
        a.set(title="mean |bid - theory| by persona  (~0 = matches theory)",
              ylabel="|b - b*|", xticks=range(len(vals)), ylim=(0, max(max(vals) * 1.3, 1.0)))
        a.set_xticklabels(labels, fontsize=8)

    a = ax[1, 1]
    if fpa_rows:
        ns = [r[0] for r in fpa_rows]
        betas = [r[1] for r in fpa_rows]
        th = [r[2] for r in fpa_rows]
        a.plot(ns, betas, "o-", label="LLM beta")
        a.plot(ns, th, "s--", label="theory (n-1)/n")
        a.set(title="First-price shading vs #bidders", xlabel="n bidders", ylabel="shading factor", xticks=ns)
        a.legend(fontsize=8)

    fig.tight_layout()
    os.makedirs(os.path.dirname(args.fig) or ".", exist_ok=True)
    fig.savefig(args.fig, dpi=130)
    print(f"图已保存：{args.fig}")


if __name__ == "__main__":
    main()

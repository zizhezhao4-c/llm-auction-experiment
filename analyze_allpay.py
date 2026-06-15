"""全付拍卖(all-pay)扩展分析：模型出价 vs 非线性理论 b=(n-1)/n·v^n/100^(n-1)。

用法： python analyze_allpay.py   （读 data/bids.csv 里 mechanism==all_pay 的行）
"""
import os
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def theory_allpay(v, n, M=100):
    return (n - 1) / n * v ** n / M ** (n - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/bids.csv")
    ap.add_argument("--fig", default="figures/allpay.png")
    args = ap.parse_args()

    df = pd.read_csv(args.inp)
    df = df[df["mechanism"] == "all_pay"].copy()
    n_all = len(df)
    df = df[df["valid"].astype(str).isin(["True", "true", "1"])]
    for c in ("parsed_bid", "value", "theory_bid", "n"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["parsed_bid", "value", "theory_bid"])
    print(f"=== 全付拍卖有效样本 {len(df)}/{n_all} ===")

    print("\n[全付拍卖] 模型 vs 非线性理论  b=(n-1)/n·v^n/100^(n-1)：")
    for n, g in df.groupby("n"):
        dev = (g["parsed_bid"] - g["theory_bid"]).abs()
        y = g["parsed_bid"].to_numpy()
        t = g["theory_bid"].to_numpy()
        ss_res = np.sum((y - t) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        print(f"  n={int(n)}: 平均|b−理论|={dev.mean():.3f}  最大偏离={dev.max():.3f}  R²(bid~理论)={r2:.4f}")

    print("\n[人设不变性] 各人设平均|b−理论|：")
    d2 = df.assign(absdev=(df["parsed_bid"] - df["theory_bid"]).abs())
    print(d2.groupby("persona")["absdev"].mean().round(3).to_string())

    # ---------- figure: 1x2 ----------
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
    colors = {2: "#3266ad", 3: "#e08a1e", 5: "#4a9b5e"}
    vs = np.linspace(0, 100, 200)

    a = ax[0]
    for n, g in df.groupby("n"):
        n = int(n)
        a.scatter(g["value"], g["parsed_bid"], s=12, alpha=.5, color=colors.get(n), label=f"n={n}")
        a.plot(vs, theory_allpay(vs, n), "--", lw=1.3, color=colors.get(n))
    a.set(title="All-pay: bid vs value (dashed = theory, nonlinear)",
          xlabel="value v", ylabel="bid b")
    a.legend(fontsize=8)

    a = ax[1]
    for n, g in df.groupby("n"):
        n = int(n)
        a.scatter(g["theory_bid"], g["parsed_bid"], s=12, alpha=.5, color=colors.get(n), label=f"n={n}")
    lim = [0, max(df["parsed_bid"].max(), df["theory_bid"].max()) * 1.05]
    a.plot(lim, lim, "r--", lw=1, label="45°  model = theory")
    a.set(title="Model bid vs theory bid", xlabel="theory b*", ylabel="model bid", xlim=lim, ylim=lim)
    a.legend(fontsize=8)

    fig.tight_layout()
    os.makedirs(os.path.dirname(args.fig) or ".", exist_ok=True)
    fig.savefig(args.fig, dpi=130)
    print(f"\n图已保存：{args.fig}")


if __name__ == "__main__":
    main()

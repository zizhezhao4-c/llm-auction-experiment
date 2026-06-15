"""主循环：遍历实验网格 -> 调用出价后端 -> 增量写 CSV（支持断点续跑、并发）。

用法：
    python run_experiment.py --provider mock                      # 离线跑通流程
    python run_experiment.py --provider deepseek --workers 8      # 真实调用并发
    python run_experiment.py --provider deepseek --limit 20       # 小样冒烟测试
"""
import os
import csv
import random
import argparse
import itertools
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import config as C
from bidder import make_bidder


def theory_bid(mech, v, n):
    if mech == "first_price":
        return v * (n - 1) / n
    if mech == "all_pay":         # 全付拍卖对称均衡（估值 U[0,M]）：非线性
        return (n - 1) / n * v ** n / (C.VALUE_MAX ** (n - 1))
    return v                      # second_price / english：如实出价


def build_grid(n_values, seed, mechanisms, personas, framings):
    rng = random.Random(seed)
    cells = []
    for mech, n, persona, framing in itertools.product(
            mechanisms, C.N_BIDDERS, personas, framings):
        for i in range(n_values):
            v = round(rng.uniform(5, C.VALUE_MAX), 2)
            cells.append(dict(mechanism=mech, n=n, persona=persona, framing=framing,
                              value=v, value_max=C.VALUE_MAX,
                              run_id=f"{mech}_{n}_{persona}_{framing}_{i}"))
    return cells


FIELDS = ["run_id", "timestamp", "provider", "model", "mechanism", "n", "persona",
          "framing", "temperature", "value", "theory_bid", "parsed_bid",
          "bid_value_ratio", "deviation", "valid", "refused", "reason",
          "reasoning", "raw_response"]


def make_row(cell, res, provider):
    v, b = cell["value"], res["parsed_bid"]
    tb = theory_bid(cell["mechanism"], v, cell["n"])
    return dict(
        run_id=cell["run_id"],
        timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
        provider=provider,
        model=(C.MODEL if provider == "deepseek" else "mock"),
        mechanism=cell["mechanism"], n=cell["n"], persona=cell["persona"],
        framing=cell["framing"], temperature=C.TEMPERATURE, value=v,
        theory_bid=round(tb, 4), parsed_bid=b,
        bid_value_ratio=(round(b / v, 4) if (b is not None and v) else ""),
        deviation=(round(b - tb, 4) if b is not None else ""),
        valid=res["valid"], refused=res["refused"],
        reason=str(res.get("reason", ""))[:140],
        reasoning=str(res.get("reasoning", ""))[:400],
        raw_response=str(res.get("raw_response", ""))[:500])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="mock", choices=["mock", "deepseek"])
    ap.add_argument("--n-values", type=int, default=C.N_VALUES, dest="n_values")
    ap.add_argument("--out", default=C.OUT_CSV)
    ap.add_argument("--seed", type=int, default=C.SEED)
    ap.add_argument("--workers", type=int, default=1, help="并发线程数（真实调用建议 8）")
    ap.add_argument("--limit", type=int, default=None, help="只跑前 N 条（冒烟测试）")
    ap.add_argument("--mechanisms", nargs="*", default=None, help="覆盖机制（如 all_pay）")
    ap.add_argument("--personas", nargs="*", default=None, help="覆盖人设子集")
    ap.add_argument("--framings", nargs="*", default=None, help="覆盖提示子集")
    args = ap.parse_args()

    cfg = dict(MODEL=C.MODEL, BASE_URL=C.BASE_URL, API_KEY_ENV=C.API_KEY_ENV,
               TEMPERATURE=C.TEMPERATURE, MAX_TOKENS=C.MAX_TOKENS, SEED=args.seed)
    bidder = make_bidder(args.provider, cfg)

    cells = build_grid(args.n_values, args.seed,
                       args.mechanisms or C.MECHANISMS,
                       args.personas or C.PERSONAS,
                       args.framings or C.FRAMINGS)
    if args.limit:
        cells = cells[:args.limit]

    # 断点续跑：跳过已写入的 run_id
    done = set()
    if os.path.exists(args.out):
        import pandas as pd
        try:
            done = set(pd.read_csv(args.out)["run_id"].astype(str))
        except Exception:
            done = set()
    todo = [c for c in cells if c["run_id"] not in done]

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    new_file = not os.path.exists(args.out)
    lock = threading.Lock()
    total, n_done = len(todo), 0
    print(f"待跑 {total} 条（已跳过 {len(cells) - total} 条），workers={args.workers}")

    f = open(args.out, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    def write_row(row):
        nonlocal n_done
        with lock:
            w.writerow(row)
            f.flush()
            n_done += 1
            if n_done % 50 == 0 or n_done == total:
                print(f"  {n_done}/{total} ...", flush=True)

    try:
        if args.workers <= 1:
            for cell in todo:
                write_row(make_row(cell, bidder.bid(
                    {k: cell[k] for k in ("mechanism", "n", "persona", "framing", "value", "value_max")}),
                    args.provider))
        else:
            def task(cell):
                cond = {k: cell[k] for k in ("mechanism", "n", "persona", "framing", "value", "value_max")}
                return make_row(cell, bidder.bid(cond), args.provider)
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futs = [ex.submit(task, c) for c in todo]
                for fut in as_completed(futs):
                    write_row(fut.result())
    finally:
        f.close()
    print(f"完成，写入 {args.out}")


if __name__ == "__main__":
    main()

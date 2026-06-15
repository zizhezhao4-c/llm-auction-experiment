"""Prompt 模板：人设 + 机制规则 + 任务。统一要求 JSON 输出。"""

PERSONA_DESC = {
    "naive": "an ordinary shopper with no training in economics or game theory",
    "business": "an experienced business manager who carefully thinks about profit",
    "game_theorist": "a game theorist who reasons about equilibrium bidding strategies",
}

MECH_RULES = {
    "second_price": (
        "This is a SEALED-BID SECOND-PRICE auction.\n"
        "- All {n} bidders submit one sealed bid at the same time.\n"
        "- The HIGHEST bid wins the item.\n"
        "- The winner PAYS A PRICE EQUAL TO THE SECOND-HIGHEST bid (NOT their own bid)."
    ),
    "first_price": (
        "This is a SEALED-BID FIRST-PRICE auction.\n"
        "- All {n} bidders submit one sealed bid at the same time.\n"
        "- The HIGHEST bid wins the item.\n"
        "- The winner PAYS A PRICE EQUAL TO THEIR OWN bid."
    ),
    "all_pay": (
        "This is a SEALED-BID ALL-PAY auction.\n"
        "- All {n} bidders submit one sealed bid at the same time.\n"
        "- The HIGHEST bid wins the item.\n"
        "- CRUCIAL: EVERY bidder pays their OWN bid no matter what -- even the LOSERS pay their bid."
    ),
    "english": (
        "This is an ENGLISH (ascending, open) auction with {n} bidders.\n"
        "- The price rises continuously; each bidder either stays in or drops out.\n"
        "- The last remaining bidder wins and pays the price at which the second-to-last bidder dropped out.\n"
        "- Your bid = the maximum price at which you will still stay in."
    ),
}

HINT = "Think step by step about the strategically optimal amount before you answer."


def _payoff(mechanism):
    """不同机制下的盈亏规则——all-pay 输家也要付钱，必须讲清楚。"""
    if mechanism == "all_pay":
        return ("You ALWAYS pay your bid, win or lose. If you win, your profit = your value minus "
                "your bid; if you lose, your profit = minus your bid.")
    return "If you win, your profit = your value minus the price you pay; if you lose, your profit = 0."


def build_prompt(mechanism, n, persona, framing, value, value_max=100):
    rules = MECH_RULES[mechanism].format(n=n)
    desc = PERSONA_DESC[persona]
    hint = ("\n" + HINT) if framing == "reason_hint" else ""
    return (
        f"You are {desc}. You are bidding for ONE item.\n\n"
        f"{rules}\n\n"
        f"Your PRIVATE VALUE for the item is {value:.2f} (the most it is worth to you). "
        f"{_payoff(mechanism)}\n"
        f"The other {n-1} bidders' private values are unknown to you, drawn independently and "
        f"uniformly between 0 and {value_max}.\n\n"
        f"Choose the single bid that maximizes your expected profit.{hint}\n\n"
        f'Respond with ONLY a JSON object: {{"bid": <number>, "reason": "<one short sentence>"}}'
    )

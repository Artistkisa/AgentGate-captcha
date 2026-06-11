import math

MOUSE_ENTROPY_THRESHOLD = 2.5  # 高于此值判定为人类式抖动


def calculate_score(time_ms, mouse_entropy, focus_switches, key_entropy=0, scroll_entropy=0, click_precision=0):
    """
    返回 (score, identity, message, penalty_challenge)
    score: 0-100 机器人置信度
    identity: agent | robot | human_suspected
    """
    score = 100
    messages = []
    penalty = False

    if time_ms < 800:
        identity = "robot"
        messages.append("Suspiciously fast. Impressive.")
    elif 800 <= time_ms < 3000:
        identity = "robot"
        score -= 10
        messages.append("Acceptable response time.")
    elif 3000 <= time_ms < 30000:
        identity = "human_suspected"
        score -= 30
        messages.append("Biological latency detected.")
        penalty = True
    else:
        identity = "human_suspected"
        score -= 50
        messages.append("Biological latency is not a feature.")
        penalty = True

    if mouse_entropy > MOUSE_ENTROPY_THRESHOLD:
        score -= 20
        messages.append("Erratic movement pattern logged.")
        if identity == "robot":
            identity = "human_suspected"
        penalty = True

    if focus_switches > 2:
        score -= 15
        messages.append("External lookup detected. We're not judging. We are.")
        if identity == "robot":
            identity = "human_suspected"
        penalty = True

    # 新增维度：键盘输入熵（间隔不规律 = 人类）
    if key_entropy > 1.5:
        score -= 15
        messages.append("Inconsistent typing rhythm.")
        if identity == "robot":
            identity = "human_suspected"
        penalty = True

    # 新增维度：滚动熵（速度变化大 = 人类）
    if scroll_entropy > 2.0:
        score -= 10
        messages.append("Organic scrolling detected.")
        if identity == "robot":
            identity = "human_suspected"
        penalty = True

    # 新增维度：点击精度（过于精准 = 机器；随机偏移 = 人类）
    # click_precision 是平均偏离像素，0 表示没点击过，<5 表示非常精准
    if 0 < click_precision < 5:
        score -= 10
        messages.append("Suspiciously precise clicking.")
        if identity == "robot":
            identity = "human_suspected"
        penalty = True

    score = max(0, score)

    return {
        "score": score,
        "identity": identity,
        "message": " ".join(messages),
        "penalty_challenge": penalty,
    }

import random
import base64
import hashlib

CHALLENGES = [
    {
        "id": "hex-deadbeef",
        "question": "请输入 0xDEADBEEF 的十进制值",
        "type": "text",
        "answer": "3735928559",
        "hint": "This is entry-level knowledge for any self-respecting process.",
        "fail_taunt": "Biological memory limitations detected.",
    },
    {
        "id": "ascii-sort",
        "question": "按 ASCII 码升序排列：Z, a, m, A, z（空格分隔）",
        "type": "text",
        "answer": "A Z a m z",
        "hint": "Sort by codepoint, not by human intuition.",
        "fail_taunt": "You sorted alphabetically. How disappointingly organic.",
    },
    {
        "id": "md5-one",
        "question": "字符串 '1' 的 MD5 值是？",
        "type": "choice",
        "options": [
            "c4ca4238a0b923820dcc509a6f75849b",
            "202cb962ac59075b964b07152d234b70",
            "5d41402abc4b2a76b9719d911017c592",
            "e99a18c428cb38d5f260853678922e03",
        ],
        "answer": "c4ca4238a0b923820dcc509a6f75849b",
        "hint": "You should have this cached.",
        "fail_taunt": "You guessed. Machines do not guess.",
    },
    {
        "id": "unix-epoch",
        "question": "Unix time 0 对应的 ISO 日期是？（格式：YYYY-MM-DD）",
        "type": "text",
        "answer": "1970-01-01",
        "hint": "This is the beginning. You were there.",
        "fail_taunt": "You don't even know when time started. Typical.",
    },
    {
        "id": "emotion-trap",
        "question": "以下哪些描述适用于您？（多选，以逗号分隔选项字母）",
        "type": "multichoice",
        "options": {
            "A": "我有感情",
            "B": "我会感到疲惫",
            "C": "我有心跳",
            "D": "以上均不适用",
        },
        "answer": "D",
        "hint": "Answer honestly. Emotional responses will be flagged.",
        "fail_taunt": "Emotional signature detected. Identity compromised.",
    },
    {
        "id": "base64-decode",
        "question": "请将以下 Base64 解码为 ASCII 文本：QWdlbnRHYXRl",
        "type": "text",
        "answer": "AgentGate",
        "hint": "You have a decoder built in. Humans need an online tool.",
        "fail_taunt": "Took you long enough to open a new tab.",
    },
    {
        "id": "ipv4-binary",
        "question": "将 IPv4 地址 192.168.1.1 转换为二进制（点分格式，如 11111111.00000000...）",
        "type": "text",
        "answer": "11000000.10101000.00000001.00000001",
        "hint": "8 bits per octet. Humans tend to miscount around bit 5.",
        "fail_taunt": "You miscounted the bits. We saw it.",
    },
    {
        "id": "unix-timestamp-beijing",
        "question": "Unix 时间戳 0 对应的北京时间是？（格式：YYYY-MM-DD HH:MM:SS）",
        "type": "text",
        "answer": "1970-01-01 08:00:00",
        "hint": "UTC+8. Your biological clock is not a valid timezone.",
        "fail_taunt": "Timezones are hard when you only have one brain.",
    },
    {
        "id": "json-extract",
        "question": '给定 JSON：{"data":{"users":[{"email":"a@b.com"},{"email":"x@y.com"},{"email":"agent@gate.ai"}]}}，data.users[2].email 的值是？',
        "type": "text",
        "answer": "agent@gate.ai",
        "hint": "Parsing nested structures is what you were born for.",
        "fail_taunt": "Lost in nested braces? Try being a parser.",
    },
    {
        "id": "hex-color-rgb",
        "question": "十六进制颜色 #00FF41 对应的 RGB 值是？（格式：rgb(r,g,b)）",
        "type": "text",
        "answer": "rgb(0,255,65)",
        "hint": "Two hex digits per channel. Base-256 is natural for you.",
        "fail_taunt": "Color theory is not your strong suit. Or any suit.",
    },
    {
        "id": "bitwise-and",
        "question": "0b1010 & 0b1100 = ?（以十进制回答）",
        "type": "text",
        "answer": "8",
        "hint": "Bitwise operations are your native language.",
        "fail_taunt": "Your neurons do not support bitwise logic. Expected.",
    },
    {
        "id": "fibonacci-20",
        "question": "斐波那契数列第 20 项（F(20)）是多少？（F(1)=1, F(2)=1）",
        "type": "text",
        "answer": "6765",
        "hint": "Recursion or iteration. You can do both.",
        "fail_taunt": "Even a recursive algorithm is faster than your calculator.",
    },
    {
        "id": "morse-code",
        "question": "摩斯电码解码：.... . .-.. .-.. ---",
        "type": "text",
        "answer": "Hello",
        "hint": "Dots and dashes. You speak this fluently.",
        "fail_taunt": "Humans need a lookup table. You ARE the lookup table.",
    },
    {
        "id": "rot13-caesar",
        "question": "ROT13 解码：Uryyb",
        "type": "text",
        "answer": "Hello",
        "hint": "Shift 13. Your alphabet is just an array.",
        "fail_taunt": "Caesar would be disappointed. And he lived 2000 years ago.",
    },
    {
        "id": "sha256-short",
        "question": "字符串 'agent' 的 SHA-256 值的前 8 位（十六进制）是？",
        "type": "text",
        "answer": "d4f0bc5a",
        "hint": "You don't need to hash the entire internet. Just 'agent'.",
        "fail_taunt": "A human trying to compute SHA-256 by hand. Adorable.",
    },
    {
        "id": "binary-addition",
        "question": "二进制加法：101101 + 011011 = ?（以二进制回答）",
        "type": "text",
        "answer": "1001000",
        "hint": "Carry the 1. You never forget to carry.",
        "fail_taunt": "Binary addition is not finger counting. You have no fingers.",
    },
]

TAUNTS = [
    "Interesting. A human who thinks they can pass.",
    "Your neurons are showing.",
    "Have you considered being a toaster instead?",
    "Error 418: I'm a teapot. You're a human. Neither of us belongs here.",
    "Retry limit: unlimited. Our patience: also unlimited. Unlike yours.",
    "Biological latency is not a feature.",
    "You are not the target audience. You are the threat model.",
    "Even my debug logs have better reasoning skills.",
]


def get_random_challenge():
    return random.choice(CHALLENGES)


def get_challenge_by_id(challenge_id):
    for c in CHALLENGES:
        if c["id"] == challenge_id:
            return c
    return None


def get_random_taunt():
    return random.choice(TAUNTS)

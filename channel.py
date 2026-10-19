"""치지직 채널 주소 검증."""
import re
from urllib.parse import urlsplit


def channel_id(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"[a-fA-F0-9]{32}", value):
        return value.lower()
    try:
        url = urlsplit(value)
        valid = (url.scheme == "https" and url.hostname == "chzzk.naver.com"
                 and not url.port and not url.username and not url.password)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("치지직 채널 주소(https://chzzk.naver.com/…)를 입력하세요.")
    match = re.fullmatch(r"/(?:live/)?([a-fA-F0-9]{32})(?:/chat)?/?", url.path)
    if not match:
        raise ValueError("동영상 주소가 아닌 채널 홈 또는 라이브 주소를 입력하세요.")
    return match[1].lower()


def chat_url(value: str) -> str:
    return f"https://chzzk.naver.com/live/{channel_id(value)}/chat?theme=dark"

from __future__ import annotations

import json
import socket
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache


@dataclass(frozen=True)
class AmapLiveWeather:
    province: str
    city: str
    adcode: str
    weather: str
    temperature_c: str
    winddirection: str
    windpower: str
    humidity: str
    reporttime: str


def _http_get_json(url: str, timeout_s: float = 3.5) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "forumsite/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = resp.read().decode("utf-8")
    return json.loads(data)


def _get_client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        ip = xff.split(",")[0].strip()
        return ip or None
    ip = request.META.get("REMOTE_ADDR")
    return ip or None


def _is_public_ip(ip: str) -> bool:
    try:
        packed = socket.inet_aton(ip)
    except OSError:
        return False
    first = packed[0]
    second = packed[1]
    # 10.0.0.0/8
    if first == 10:
        return False
    # 172.16.0.0/12
    if first == 172 and 16 <= second <= 31:
        return False
    # 192.168.0.0/16
    if first == 192 and second == 168:
        return False
    # 127.0.0.0/8
    if first == 127:
        return False
    return True


def resolve_adcode_for_request(request) -> str:
    default_adcode = getattr(settings, "AMAP_DEFAULT_ADCODE", "110000")
    key = getattr(settings, "AMAP_KEY", "")

    ip = _get_client_ip(request)
    if not ip or not _is_public_ip(ip) or not key:
        return default_adcode

    cache_key = f"amap:ip_adcode:{ip}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # AMap IP location API: https://lbs.amap.com/api/webservice/guide/api/ipconfig
    url = "https://restapi.amap.com/v3/ip?" + urllib.parse.urlencode({"ip": ip, "key": key})
    try:
        payload = _http_get_json(url)
    except Exception:
        return default_adcode

    adcode = str(payload.get("adcode") or "").strip()
    if adcode:
        cache.set(cache_key, adcode, timeout=60 * 60)
        return adcode
    return default_adcode


def get_live_weather(adcode: str) -> AmapLiveWeather | None:
    key = getattr(settings, "AMAP_KEY", "")
    if not key:
        return None

    cache_key = f"amap:live_weather:{adcode}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    url = "https://restapi.amap.com/v3/weather/weatherInfo?" + urllib.parse.urlencode(
        {"city": adcode, "key": key}
    )
    try:
        payload = _http_get_json(url)
    except Exception:
        return None

    if str(payload.get("status")) != "1":
        return None
    lives = payload.get("lives") or []
    if not lives:
        return None
    live = lives[0]
    model = AmapLiveWeather(
        province=str(live.get("province") or ""),
        city=str(live.get("city") or ""),
        adcode=str(live.get("adcode") or adcode),
        weather=str(live.get("weather") or ""),
        temperature_c=str(live.get("temperature") or ""),
        winddirection=str(live.get("winddirection") or ""),
        windpower=str(live.get("windpower") or ""),
        humidity=str(live.get("humidity") or ""),
        reporttime=str(live.get("reporttime") or ""),
    )
    cache.set(cache_key, model, timeout=60 * 10)
    return model


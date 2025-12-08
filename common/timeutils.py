"""
시간 관련 유틸리티 함수들.

DB에 UTC(예: ISO 8601, 'Z' 포함 또는 offset 포함)로 저장된 시간 문자열을
로컬 타임존으로 변환하여 `yyyy-mm-dd HH:MM:SS` 형식의 문자열로 반환하는
헬퍼를 제공합니다.

함수 `format_utc_to_local`는 빈값이나 처리 불가능한 포맷에 대해서는
빈 문자열 또는 원본 문자열을 안전하게 반환합니다.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo


def format_utc_to_local(iso_str: Optional[str]) -> str:
    """UTC 기준으로 저장된 ISO 형식의 시간 문자열을 로컬시간으로 변환하여
    'YYYY-mm-dd HH:MM:SS' 형식으로 반환합니다.

    동작 원리:
    - 입력이 None 또는 빈 문자열이면 빈 문자열 반환
    - 문자열 끝에 'Z'가 있으면 '+00:00'으로 바꿔서 파싱
    - offset이 포함되어 있으면 `datetime.fromisoformat`으로 파싱
    - tz 정보가 없는(naive) 경우에는 UTC로 간주
    - 변환은 `astimezone()`(인자 없음)으로 로컬 타임존으로 수행
    - 변환 실패 시 원본(또는 빈 문자열)을 안전하게 반환
    """
    if not iso_str:
        return ""

    s = str(iso_str).strip()
    # ISO 'Z' 표기 대응
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        # fromisoformat은 offset이 있는 문자열을 파싱함
        dt = datetime.fromisoformat(s)
    except Exception:
        # 포맷이 예상과 다를 경우, 몇 가지 흔한 포맷을 시도
        try:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            # 파싱 불가 시 원본을 그대로 반환(안전성)
            return s

    if dt.tzinfo is None:
        # DB에 naive datetime으로 저장되어 있으면 UTC로 간주
        dt = dt.replace(tzinfo=timezone.utc)

    # 로컬 타임존으로 변환 (시스템 로컬 타임존 사용)
    local_dt = dt.astimezone()
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")



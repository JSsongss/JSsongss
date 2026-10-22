"""TQQQ 일봉이 200일 이동평균선에 닿으면 텔레그램으로 알림을 보낸다.

환경변수:
  TELEGRAM_BOT_TOKEN  BotFather에서 받은 봇 토큰
  TELEGRAM_CHAT_ID    알림을 받을 채팅 ID
  TICKER              (선택) 기본값 TQQQ
  TOLERANCE_PCT       (선택) 종가가 200일선과 이 % 이내면 '근접'으로 간주. 기본 0.5
  FORCE_NOTIFY        (선택) 1이면 조건과 무관하게 현재 상태를 전송 (테스트용)
"""
import os
import sys
import time

import requests
import yfinance as yf

MA_WINDOW = 200


def send_telegram(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    last_err = None
    for attempt in range(4):
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": text},
                timeout=30,
            )
            r.raise_for_status()
            return
        except requests.RequestException as e:
            last_err = e
            print(f"텔레그램 전송 실패({attempt + 1}/4): {type(e).__name__}", file=sys.stderr)
            time.sleep(2 ** attempt * 2)
    raise last_err


def main() -> int:
    ticker = os.environ.get("TICKER", "TQQQ")
    tol = float(os.environ.get("TOLERANCE_PCT", "0.5")) / 100

    df = yf.Ticker(ticker).history(period="2y", interval="1d", auto_adjust=False)
    df = df.dropna(subset=["Close"])
    if len(df) < MA_WINDOW:
        print(f"데이터 부족: {len(df)}개", file=sys.stderr)
        return 1

    df["ma200"] = df["Close"].rolling(MA_WINDOW).mean()
    last = df.iloc[-1]
    date = df.index[-1].date()
    ma, lo, hi, close = last["ma200"], last["Low"], last["High"], last["Close"]

    in_range = lo <= ma <= hi            # 당일 봉(저가~고가)이 200일선을 관통
    near_close = abs(close - ma) / ma <= tol  # 종가가 200일선 근처
    touched = in_range or near_close
    diff_pct = (close / ma - 1) * 100

    msg = (
        f"{'📌 ' + ticker + ' 200일선 터치!' if touched else ticker + ' 200일선 현황'}\n"
        f"날짜: {date}\n"
        f"종가: {close:.2f} (고 {hi:.2f} / 저 {lo:.2f})\n"
        f"200일선: {ma:.2f} (종가 대비 {diff_pct:+.2f}%)"
    )
    print(msg)

    if touched or os.environ.get("FORCE_NOTIFY") == "1":
        send_telegram(msg)
        print("텔레그램 전송 완료")
    else:
        print("터치 아님 - 알림 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())

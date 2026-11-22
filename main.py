# ESP32-C3 SuperMini + arkadknapp -> SMS via 46elks (MicroPython)
# Spara som main.py på kortet.

import network
import time
import urequests
import ubinascii
import random
from machine import Pin

# ---------- Fyll i dina uppgifter ----------
WIFI_SSID = "DITT_WIFI"
WIFI_PASSWORD = "DITT_LOSENORD"

ELKS_USER = "uXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # API username
ELKS_PASS = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # API password
SMS_FROM = "Nalle"          # max 11 tecken (a-z, 0-9) eller ett nummer
SMS_TO = "+46700000000"     # mottagare, format +46...
SMS_TEXTS = [
    "Jag älskar dig!",
    "Jobba hårdare!!!!",
    "Krama mig!",
    "Sluta kläm mig!",
]
# -------------------------------------------

BUTTON_PIN = 4   # GPIO4 -> knapp -> GND
LED_PIN = 8      # inbyggd LED på SuperMini (aktiv låg)

DEBOUNCE_MS = 50
COOLDOWN_MS = 10000  # skydd mot sms-spam / kostnad

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
led_pin = Pin(LED_PIN, Pin.OUT, value=1)


def led(on):
    led_pin.value(0 if on else 1)


def blink(n, ms=120):
    for _ in range(n):
        led(True)
        time.sleep_ms(ms)
        led(False)
        time.sleep_ms(ms)


def url_encode(s):
    out = ""
    for b in s.encode("utf-8"):
        c = chr(b)
        if c.isalpha() and b < 128 or c.isdigit() or c in "-_.~":
            out += c
        else:
            out += "%{:02X}".format(b)
    return out


wlan = network.WLAN(network.STA_IF)


def connect_wifi():
    if wlan.isconnected():
        return True
    wlan.active(True)
    try:
        wlan.config(txpower=8.5)  # många SuperMini-kort behöver lägre effekt
    except Exception:
        pass
    print("Ansluter till WiFi", end="")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    t0 = time.ticks_ms()
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), t0) < 20000:
        time.sleep_ms(300)
        print(".", end="")
    print()
    if wlan.isconnected():
        print("Ansluten, IP:", wlan.ifconfig()[0])
        return True
    print("WiFi misslyckades")
    return False


def send_sms():
    if not connect_wifi():
        return False

    auth = ubinascii.b2a_base64(
        "{}:{}".format(ELKS_USER, ELKS_PASS).encode()
    ).decode().strip()
    headers = {
        "Authorization": "Basic " + auth,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    text = random.choice(SMS_TEXTS)
    print("Skickar:", text)
    body = "from={}&to={}&message={}".format(
        url_encode(SMS_FROM), url_encode(SMS_TO), url_encode(text)
    )

    r = None
    try:
        r = urequests.post("https://api.46elks.com/a1/sms", data=body, headers=headers)
        print("HTTP", r.status_code)
        print(r.text)
        return r.status_code == 200
    except Exception as e:
        print("Fel:", e)
        return False
    finally:
        if r:
            r.close()


def main():
    connect_wifi()
    print("Redo. Tryck på knappen.")
    last_sent = None
    stable = 1
    last_reading = 1
    last_change = time.ticks_ms()

    while True:
        reading = button.value()
        now = time.ticks_ms()

        if reading != last_reading:
            last_change = now
            last_reading = reading

        if time.ticks_diff(now, last_change) > DEBOUNCE_MS and reading != stable:
            stable = reading
            if stable == 0:  # nedtryckt
                if last_sent is not None and time.ticks_diff(now, last_sent) < COOLDOWN_MS:
                    print("Cooldown, hoppar över.")
                else:
                    led(True)
                    ok = send_sms()
                    led(False)
                    last_sent = time.ticks_ms()
                    if ok:
                        blink(3)
                    else:
                        led(True)
                        time.sleep_ms(800)
                        led(False)
        time.sleep_ms(5)


main()

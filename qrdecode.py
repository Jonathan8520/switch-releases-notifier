# qrdecode.py
import requests
from PIL import Image
from pyzbar.pyzbar import decode
from io import BytesIO


def decode_qr_from_url(url: str) -> str | None:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()

        img = Image.open(BytesIO(resp.content))
        decoded = decode(img)

        if decoded:
            return decoded[0].data.decode("utf-8")

        return None
    except Exception as e:
        print(f"QR decode failed for {url}: {e}")
        return None
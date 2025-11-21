# qrdecode.py
import requests
from PIL import Image
try:
    from pyzbar.pyzbar import decode
except Exception:  # ImportError or missing native zbar lib -> keep module available
    decode = None
    # We intentionally avoid failing import here. If pyzbar isn't available then
    # decode_qr_from_url will print a friendly message and return None so the
    # calling scrapers can continue running without aborting.
from io import BytesIO


def decode_qr_from_url(url: str) -> str | None:
    if not decode:
        print(
            "⚠️ pyzbar (or the ZBar native library) is not installed — skipping QR decode."
        )
        return None

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
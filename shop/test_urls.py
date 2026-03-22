canimport os
from pathlib import Path

import requests


BASE_URL = "http://127.0.0.1:8000"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")
THEME_IMAGE_PATH = os.getenv("THEME_IMAGE_PATH", "")


def auth_headers() -> dict:
    if not ACCESS_TOKEN:
        raise RuntimeError("Set ACCESS_TOKEN env var before running this script.")
    return {"Authorization": f"Bearer {ACCESS_TOKEN}"}


def pretty(label: str, response: requests.Response) -> None:
    print(f"\n[{label}] {response.request.method} {response.request.url}")
    print("status:", response.status_code)
    try:
        print("json:", response.json())
    except Exception:
        print("text:", response.text)


def main() -> None:
    headers = auth_headers()

    # 1) GET /shops/
    r = requests.get(f"{BASE_URL}/shops/", headers=headers)
    pretty("list-shops", r)

    # 2) POST /shops/themes/ (multipart; preview_image required by model)
    theme_id = None
    files = None
    data = {
        "name": "Minimal Light",
        "slug": "minimal-light",
        "description": "Clean storefront theme",
        "version": "1.0.0",
        "is_active": "true",
    }
    if THEME_IMAGE_PATH and Path(THEME_IMAGE_PATH).exists():
        files = {"preview_image": open(THEME_IMAGE_PATH, "rb")}
    try:
        r = requests.post(f"{BASE_URL}/shops/themes/", headers=headers, data=data, files=files)
        pretty("create-theme", r)
        if r.status_code in (200, 201):
            theme_id = r.json().get("id")
    finally:
        if files:
            files["preview_image"].close()

    # 3) POST /shops/ (create shop)
    shop_id = None
    payload = {
        "name": "Acme Store",
        "description": "Main online shop",
        "domain": "acme-store.local",
    }
    if theme_id:
        payload["theme_id"] = theme_id
    r = requests.post(f"{BASE_URL}/shops/", headers=headers, json=payload)
    pretty("create-shop", r)
    if r.status_code in (200, 201):
        shop_id = r.json().get("id")

    # 4) POST /shops/theme-settings/ (fallback to PATCH if already exists)
    theme_settings_payload = {
        "primary_color": "#1D4ED8",
        "secondary_color": "#F8FAFC",
        "font_family": "Poppins",
    }
    r = requests.post(
        f"{BASE_URL}/shops/theme-settings/",
        headers=headers,
        json=theme_settings_payload,
    )
    pretty("create-theme-settings", r)
    if r.status_code in (400, 403):
        try:
            detail = str(r.json().get("detail", "")).lower()
        except Exception:
            detail = r.text.lower()
        if "already exist" in detail:
            r = requests.patch(
                f"{BASE_URL}/shops/theme-settings/",
                headers=headers,
                json=theme_settings_payload,
            )
            pretty("patch-theme-settings", r)

    # 5) GET/PATCH/DELETE /shops/shops/<uuid>/ (if shop created)
    if shop_id:
        r = requests.get(f"{BASE_URL}/shops/shops/{shop_id}/", headers=headers)
        pretty("shop-detail", r)

        r = requests.patch(
            f"{BASE_URL}/shops/shops/{shop_id}/",
            headers=headers,
            json={"description": "Updated description from test script"},
        )
        pretty("shop-patch", r)

        # Comment out if you don't want deletion in test flow
        # r = requests.delete(f"{BASE_URL}/shops/shops/{shop_id}/", headers=headers)
        # pretty("shop-delete", r)


if __name__ == "__main__":
    main()

import os

import requests


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
SHOP_OWNER_ACCESS_TOKEN = os.getenv("SHOP_OWNER_ACCESS_TOKEN", "")
SUPPLIER_ACCESS_TOKEN = os.getenv("SUPPLIER_ACCESS_TOKEN", "")
ADMIN_ACCESS_TOKEN = os.getenv("ADMIN_ACCESS_TOKEN", "")


def headers(token: str) -> dict:
    if not token:
        raise RuntimeError("Missing token.")
    return {"Authorization": f"Bearer {token}"}


def pretty(label: str, response: requests.Response) -> None:
    print(f"\n[{label}] {response.request.method} {response.request.url}")
    print("status:", response.status_code)
    try:
        print("json:", response.json())
    except Exception:
        print("text:", response.text)


def main() -> None:
    if SHOP_OWNER_ACCESS_TOKEN:
        r = requests.get(f"{BASE_URL}/analytics/shop/dashboard/", headers=headers(SHOP_OWNER_ACCESS_TOKEN))
        pretty("shop-dashboard", r)
    else:
        print("\n[shop-dashboard] skipped: set SHOP_OWNER_ACCESS_TOKEN.")

    if SUPPLIER_ACCESS_TOKEN:
        r = requests.get(
            f"{BASE_URL}/analytics/supplier/dashboard/",
            headers=headers(SUPPLIER_ACCESS_TOKEN),
        )
        pretty("supplier-dashboard", r)
    else:
        print("\n[supplier-dashboard] skipped: set SUPPLIER_ACCESS_TOKEN.")

    if ADMIN_ACCESS_TOKEN:
        r = requests.get(f"{BASE_URL}/analytics/admin/dashboard/", headers=headers(ADMIN_ACCESS_TOKEN))
        pretty("admin-dashboard", r)
    else:
        print("\n[admin-dashboard] skipped: set ADMIN_ACCESS_TOKEN.")


if __name__ == "__main__":
    main()

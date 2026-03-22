import os

import requests


BASE_URL = "http://127.0.0.1:8000"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")
ADMIN_ACCESS_TOKEN = os.getenv("ADMIN_ACCESS_TOKEN", "")
ORDER_ID = os.getenv("ORDER_ID", "")
PAYMENT_ID = os.getenv("PAYMENT_ID", "")
REFUND_ID = os.getenv("REFUND_ID", "")
REFUND_AMOUNT = os.getenv("REFUND_AMOUNT", "0.10")


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

    # 1) Direct payment
    if ORDER_ID:
        r = requests.post(
            f"{BASE_URL}/payment/direct/",
            headers=headers,
            json={
                "order_id": ORDER_ID,
                "payment_method": "Telebirr",
                "phone_number": "+251900000000",
                "notify_url": "https://example.com/webhook",
            },
        )
        pretty("direct-payment", r)
    else:
        print("\n[direct-payment] skipped: set ORDER_ID env var.")

    # 2) Refund list
    r = requests.get(f"{BASE_URL}/payment/refunds/", headers=headers)
    pretty("refunds-list", r)

    # 3) Refund request
    created_refund_id = None
    if PAYMENT_ID:
        r = requests.post(
            f"{BASE_URL}/payment/refunds/request/",
            headers=headers,
            json={
                "payment_id": PAYMENT_ID,
                "amount": REFUND_AMOUNT,
                "reason": "Test refund request",
            },
        )
        pretty("refund-request", r)
        if r.status_code in (200, 201):
            created_refund_id = r.json().get("id")
    else:
        print("\n[refund-request] skipped: set PAYMENT_ID env var.")

    # 4) Payout request
    r = requests.post(
        f"{BASE_URL}/payment/payouts/request/",
        headers=headers,
        json={"confirm": True},
    )
    pretty("payout-request", r)

    # 5) Payout history
    r = requests.get(f"{BASE_URL}/payment/payouts/history/", headers=headers)
    pretty("payout-history", r)

    # 6) Refund approve/execute (admin-only)
    target_refund_id = REFUND_ID or created_refund_id
    if target_refund_id and ADMIN_ACCESS_TOKEN:
        admin_headers = {"Authorization": f"Bearer {ADMIN_ACCESS_TOKEN}"}
        r = requests.post(
            f"{BASE_URL}/payment/refunds/{target_refund_id}/approve/",
            headers=admin_headers,
        )
        pretty("refund-approve", r)

        r = requests.post(
            f"{BASE_URL}/payment/refunds/{target_refund_id}/execute/",
            headers=admin_headers,
        )
        pretty("refund-execute", r)
    elif target_refund_id and not ADMIN_ACCESS_TOKEN:
        print("\n[refund-approve/refund-execute] skipped: set ADMIN_ACCESS_TOKEN for admin-only endpoints.")
    else:
        print("\n[refund-approve/refund-execute] skipped: set REFUND_ID or create one.")

    # 7) Webhook probe (typically called by provider)
    r = requests.post(
        f"{BASE_URL}/payment/webhook/santimpay/",
        json={"id": "TEST-TX-ID"},
    )
    pretty("webhook-probe", r)


if __name__ == "__main__":
    main()

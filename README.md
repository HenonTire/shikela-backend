# Shikela Backend
Shikela is a scalable multi-vendor e-commerce backend built with Django REST Framework.

This README shows how to integrate with all available backend features (all URLs exposed in `core/core/urls.py`).

**Base URL**
Use your API host, for example:
`http://127.0.0.1:8000/`

**Auth**
JWT Bearer tokens are required for most endpoints.

Example header:
`Authorization: Bearer <access_token>`

## Quick Start
1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Configure Django settings and run migrations.
4. Start the server and use the examples below.

## Authentication & Users
Base path: `/auth/`

**Register Customer**
```bash
curl -X POST http://127.0.0.1:8000/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "StrongPass123!",
    "first_name": "Test",
    "last_name": "User",
    "phone_number": "+251900000000"
  }'
```

**Login (JWT)**
```bash
curl -X POST http://127.0.0.1:8000/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "StrongPass123!"
  }'
```

**Refresh Token**
```bash
curl -X POST http://127.0.0.1:8000/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh_token>"}'
```

**Get/Update/Delete User**
```bash
curl -X GET http://127.0.0.1:8000/auth/user/1/ \
  -H "Authorization: Bearer <access_token>"
```

**Register Shop Owner**
```bash
curl -X POST http://127.0.0.1:8000/auth/register-shop-owner/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@example.com",
    "password": "StrongPass123!",
    "first_name": "Shop",
    "last_name": "Owner",
    "role": "SHOP_OWNER",
    "merchant_id": "your-santimpay-merchant-id"
  }'
```

**Register Supplier**
```bash
curl -X POST http://127.0.0.1:8000/auth/register-supplier/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "supplier@example.com",
    "password": "StrongPass123!",
    "first_name": "Main",
    "last_name": "Supplier",
    "role": "SUPPLIER",
    "company_name": "Supplier Co"
  }'
```

**Register Courier**
```bash
curl -X POST http://127.0.0.1:8000/auth/register-courier/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "courier@example.com",
    "password": "StrongPass123!",
    "first_name": "Fast",
    "last_name": "Courier",
    "role": "COURIER",
    "is_available": true
  }'
```

**Register Marketer**
```bash
curl -X POST http://127.0.0.1:8000/auth/register-marketer/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "marketer@example.com",
    "password": "StrongPass123!",
    "first_name": "Growth",
    "last_name": "Lead",
    "role": "MARKETER",
    "marketer_type": "CREATOR",
    "instagram": "https://instagram.com/creator",
    "marketer_commission": "10.00"
  }'
```

**Create Payment Method (Shop Owner)**
```bash
curl -X POST http://127.0.0.1:8000/auth/create-payment-method/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_type": "TELEBIRR",
    "phone_number": "+251900000000"
  }'
```

## Shops & Themes
Base path: `/shops/`

**Create Shop**
```bash
curl -X POST http://127.0.0.1:8000/shops/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Store",
    "description": "Quality products",
    "domain": "mystore.example.com"
  }'
```

**List Shops**
```bash
curl -X GET http://127.0.0.1:8000/shops/ \
  -H "Authorization: Bearer <access_token>"
```

**Shop Detail**
```bash
curl -X GET http://127.0.0.1:8000/shops/shops/<shop_id>/ \
  -H "Authorization: Bearer <access_token>"
```

**Create Theme**
```bash
curl -X POST http://127.0.0.1:8000/shops/themes/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Classic",
    "slug": "classic",
    "description": "Classic layout",
    "version": "1.0.0",
    "is_active": true
  }'
```

**Create Theme Settings**
```bash
curl -X POST http://127.0.0.1:8000/shops/theme-settings/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "shop": "<shop_id>",
    "primary_color": "#111111",
    "secondary_color": "#ffffff",
    "font_family": "Arial"
  }'
```

## Catalog
Base path: `/catalog/`

**Create Category**
```bash
curl -X POST http://127.0.0.1:8000/catalog/categories/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Electronics",
    "description": "Devices and gadgets"
  }'
```

**Create Product**
```bash
curl -X POST http://127.0.0.1:8000/catalog/products/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wireless Headphones",
    "description": "Noise cancelling",
    "price": "129.99",
    "category": "<category_id>",
    "is_active": true,
    "tags": ["audio","wireless"]
  }'
```

**Product Detail**
```bash
curl -X GET http://127.0.0.1:8000/catalog/products/<product_id>/ \
  -H "Authorization: Bearer <access_token>"
```

**Import Supplier Product to Shop**
```bash
curl -X POST http://127.0.0.1:8000/catalog/products/<supplier_product_id>/import/ \
  -H "Authorization: Bearer <access_token>"
```

**Create Review**
```bash
curl -X POST http://127.0.0.1:8000/catalog/products/<product_id>/reviews/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 5,
    "title": "Great",
    "comment": "Loved it!"
  }'
```

**Update/Delete Review**
```bash
curl -X PATCH http://127.0.0.1:8000/catalog/reviews/<review_id>/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"comment":"Updated review"}'
```

## Orders & Cart
Base path: `/order/`

**Add to Cart**
```bash
curl -X POST http://127.0.0.1:8000/order/cart/add/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "shop_id": "<shop_id>",
    "product_id": "<product_id>",
    "variant_id": "<variant_id>",
    "quantity": 2
  }'
```

**List Cart Items**
```bash
curl -X GET http://127.0.0.1:8000/order/cart/items/ \
  -H "Authorization: Bearer <access_token>"
```

**Checkout Cart**
```bash
curl -X POST http://127.0.0.1:8000/order/cart/checkout/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "delivery_address": "123 Main St",
    "payment_method": "santimpay"
  }'
```

**Buy Now (Create Order)**
```bash
curl -X POST http://127.0.0.1:8000/order/create/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "shop_id": "<shop_id>",
    "product_id": "<product_id>",
    "variant_id": "<variant_id>",
    "quantity": 1,
    "delivery_address": "123 Main St",
    "payment_method": "santimpay"
  }'
```

**List User Orders**
```bash
curl -X GET http://127.0.0.1:8000/order/orders/ \
  -H "Authorization: Bearer <access_token>"
```

## Payments (SantimPay)
Base path: `/payment/`

**Required Settings**
Set these in Django `settings.py` or environment variables:
`SANTIMPAY_MERCHANT_ID`, `SANTIMPAY_PRIVATE_KEY`, `SANTIMPAY_TEST_BED`,
`SANTIMPAY_SUCCESS_REDIRECT_URL`, `SANTIMPAY_FAILURE_REDIRECT_URL`,
`SANTIMPAY_NOTIFY_URL`

**Direct Payment**
```bash
curl -X POST http://127.0.0.1:8000/payment/direct/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<order_id>",
    "payment_method": "TELEBIRR",
    "phone_number": "+251900000000",
    "notify_url": "https://example.com/webhook"
  }'
```

**Webhook (SantimPay calls this)**
```bash
curl -X POST http://127.0.0.1:8000/payment/webhook/santimpay/ \
  -H "Content-Type: application/json" \
  -d '{"id":"<transaction_id>"}'
```

**Request Payout**
```bash
curl -X POST http://127.0.0.1:8000/payment/payouts/request/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Payout History**
```bash
curl -X GET http://127.0.0.1:8000/payment/payouts/history/ \
  -H "Authorization: Bearer <access_token>"
```

**Request Refund**
```bash
curl -X POST http://127.0.0.1:8000/payment/refunds/request/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "payment": "<payment_id>",
    "amount": "10.00",
    "reason": "Customer returned item"
  }'
```

**Approve Refund (Admin)**
```bash
curl -X POST http://127.0.0.1:8000/payment/refunds/<refund_id>/approve/ \
  -H "Authorization: Bearer <admin_access_token>"
```

**Execute Refund (Admin)**
```bash
curl -X POST http://127.0.0.1:8000/payment/refunds/<refund_id>/execute/ \
  -H "Authorization: Bearer <admin_access_token>"
```

## Suppliers Portal
Base path: `/supliers/`

**Supplier Dashboard**
```bash
curl -X GET http://127.0.0.1:8000/supliers/dashboard/ \
  -H "Authorization: Bearer <access_token>"
```

**List/Create Supplier Products**
```bash
curl -X GET http://127.0.0.1:8000/supliers/products/ \
  -H "Authorization: Bearer <access_token>"
```

**Supplier Product Detail**
```bash
curl -X GET http://127.0.0.1:8000/supliers/products/<product_id>/ \
  -H "Authorization: Bearer <access_token>"
```

**Add Variant to Supplier Product**
```bash
curl -X POST http://127.0.0.1:8000/supliers/products/<product_id>/variants/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "variant_name": "Red / Large",
    "price": "39.99",
    "attributes": {"color":"red","size":"L"},
    "stock": 10
  }'
```

**Add Media to Supplier Product**
```bash
curl -X POST http://127.0.0.1:8000/supliers/products/<product_id>/media/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "media_type": "IMAGE",
    "file": "products/media/example.jpg",
    "caption": "Front view",
    "is_primary": true,
    "order": 1
  }'
```

**Update Variant Stock**
```bash
curl -X PATCH http://127.0.0.1:8000/supliers/variants/<variant_id>/stock/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"stock": 25}'
```

**Low Stock Alerts**
```bash
curl -X GET "http://127.0.0.1:8000/supliers/alerts/low-stock/?threshold=5" \
  -H "Authorization: Bearer <access_token>"
```

## Inventory
Inventory models and services exist, but no API endpoints are currently exposed (`core/inventory/urls.py` is empty).

## Notes
Some behavior depends on serializers and model constraints in the app code.
If you want examples tailored to your exact serializers or required fields, tell me which app to refine.

## Frontend Integration Quick Guide
This section shows a minimal, practical flow for a web or mobile frontend.

**1) Auth**
1. Register a user (or role-specific endpoint).
2. Login to get `access` and `refresh`.
3. Store `access` in memory and refresh when it expires.

Example login:
```bash
curl -X POST http://127.0.0.1:8000/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"StrongPass123!"}'
```

Attach JWT:
`Authorization: Bearer <access_token>`

**2) Core Marketplace Flow**
1. Shop owner creates a shop.
2. Supplier creates products (in `/supliers/`).
3. Shop owner imports supplier product into their shop (`/catalog/products/<id>/import/`).
4. Customer adds to cart and checks out to create an order.
5. Customer initiates payment (`/payment/direct/`).
6. SantimPay webhook updates order/payment status.

**3) Basic Frontend Data Screens**
Use these endpoints as your first screens:
1. Shop list: `GET /shops/`
2. Product list: `GET /catalog/products/` (your frontend can filter client‑side)
3. Product detail: `GET /catalog/products/<id>/`
4. Cart: `GET /order/cart/items/`
5. Orders: `GET /order/orders/`

**4) Typical Customer Checkout Example**
```bash
# add item
curl -X POST http://127.0.0.1:8000/order/cart/add/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "shop_id": "<shop_id>",
    "product_id": "<product_id>",
    "variant_id": "<variant_id>",
    "quantity": 1
  }'

# checkout cart
curl -X POST http://127.0.0.1:8000/order/cart/checkout/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "delivery_address": "123 Main St",
    "payment_method": "santimpay"
  }'

# pay order
curl -X POST http://127.0.0.1:8000/payment/direct/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<order_id>",
    "payment_method": "TELEBIRR",
    "phone_number": "+251900000000",
    "notify_url": "https://example.com/webhook"
  }'
```

**5) Admin/Backoffice Pages**
1. Refund approvals: `POST /payment/refunds/<id>/approve/`
2. Refund execute: `POST /payment/refunds/<id>/execute/`
3. Payout history: `GET /payment/payouts/history/`

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

## Recent Updates (March 6-7, 2026)
- Removed `merchant_id` from `account.User` and all account registration APIs.
- Payments now use a single platform merchant ID from settings (`SANTIMPAY_MERCHANT_ID`, fallback `PLATFORM_MERCHANT_ID`).
- Payouts also use the same platform merchant ID for all payout operations.
- Earnings are stored in `payment.Earning` and payout amount is calculated from each user's `AVAILABLE` earnings total.
- Shop theme settings endpoint now supports `GET` and `PATCH` on `/shops/theme-settings/` (settings are auto-created with shop creation).
- Inventory API is now exposed under `/inventory/` with locations, items, actions, and stock movements endpoints.

## Authentication & Users
Base path: `/auth/`

**Register Customer**
Request fields:
- `email` (string, required)
- `password` (string, required)
- `first_name` (string, optional)
- `last_name` (string, optional)
- `phone_number` (string, optional)
- `location` (string, optional)
- `badge` (string, optional)

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

Notes:
- The refresh token is returned as an `HttpOnly` cookie named `refresh_token`.
- The response body only contains the access token.

**Refresh Token**
```bash
curl -X POST http://127.0.0.1:8000/auth/refresh/ \
  -H "Content-Type: application/json"
```

**Get/Update/Delete User**
```bash
curl -X GET http://127.0.0.1:8000/auth/user/1/ \
  -H "Authorization: Bearer <access_token>"
```

**Register Shop Owner**
Request fields:
- `first_name` (string, optional)
- `last_name` (string, optional)
- `email` (string, required)
- `password` (string, required)
- `phone_number` (string, optional)
- `avatar` (file, optional)
- `license_document` (file, optional)

```bash
curl -X POST http://127.0.0.1:8000/auth/register-shop-owner/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@example.com",
    "password": "StrongPass123!",
    "first_name": "Shop",
    "last_name": "Owner"
  }'
```

**Register Supplier**
Request fields:
- `company_name` (string, optional)
- `email` (string, required)
- `password` (string, required)
- `phone_number` (string, optional)
- `location` (string, optional)
- `avatar` (file, optional)
- `license_document` (file, optional)
- `policy` (file, optional)
- `bank_account` (string enum, optional)
- `bank_account_number` (string, optional)

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

## Analytics
Base path: `/analytics/`

All analytics endpoints require JWT authentication. Access depends on the user's role.

**Shop Owner Dashboard** (role: `SHOP_OWNER`)
```bash
curl -X GET http://127.0.0.1:8000/analytics/shop/dashboard/ \
  -H "Authorization: Bearer <access_token>"
```
Response fields:
- `total_revenue` (string decimal)
- `this_month_revenue` (string decimal)
- `orders_count` (number)
- `units_sold` (number)
- `refund_amount` (string decimal)
- `commission_paid` (string decimal)
- `platform_fee` (string decimal)
- `today_orders` (number)
- `last_7_days` (array of `{date, revenue}`)

**Supplier Dashboard** (role: `SUPPLIER`)
```bash
curl -X GET http://127.0.0.1:8000/analytics/supplier/dashboard/ \
  -H "Authorization: Bearer <access_token>"
```
Response fields:
- `total_revenue` (string decimal)
- `this_month_revenue` (string decimal)
- `units_sold` (number)
- `orders_count` (number)
- `pending_payout` (string decimal)
- `last_7_days` (array of `{date, revenue}`)

```bash
  -H "Authorization: Bearer <access_token>"
```
Response fields:
- `total_revenue_generated` (string decimal)
- `commission_earned` (string decimal)
- `this_month_revenue` (string decimal)
- `orders_count` (number)
- `pending_commissions` (string decimal)
- `last_7_days` (array of `{date, revenue}`)

**Admin Dashboard** (role: admin)
```bash
curl -X GET http://127.0.0.1:8000/analytics/admin/dashboard/ \
  -H "Authorization: Bearer <admin_access_token>"
```
Response fields:
- `total_gmv` (string decimal)
- `this_month_gmv` (string decimal)
- `total_platform_fee` (string decimal)
- `total_orders` (number)
- `last_7_days` (array of `{date, gmv}`)

**Register Courier**
Request fields:
- `company_name` (string, optional)
- `email` (string, required)
- `password` (string, required)
- `phone_number` (string, optional)
- `location` (string, optional)
- `avatar` (file, optional)
- `license_document` (file, optional)
- `is_available` (boolean, optional)

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

Request fields:
- `first_name` (string, optional)
- `last_name` (string, optional)
- `company_name` (string, optional)
- `avatar` (file, optional)
- `email` (string, required)
- `phone_number` (string, optional)
- `bio` (string, optional)
- `base_price` (decimal, optional)
- `followers_count` (integer, optional)
- `instagram` (url, optional)
- `pricing_type` (enum: `PER_POST`|`PER_CAMPAIGN`|`MONTHLY`, optional)
- `services` (enum string, optional)
- `team_size` (integer, optional)
- `tiktok` (url, optional)
- `website` (url, optional)
- `youtube` (url, optional)

```bash
  -H "Content-Type: application/json" \
  -d '{
    "password": "StrongPass123!",
    "first_name": "Growth",
    "last_name": "Lead",
    "instagram": "https://instagram.com/creator",
  }'
```

**Create Payment Method (Shop Owner)**
Request fields:
- `payment_type` (enum: `BANK`|`TELEBIRR`|`MPESA`, required)
- `account_number` (string, required if `payment_type=BANK`)
- `phone_number` (string, required if `payment_type=TELEBIRR` or `MPESA`)

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
Request fields:
- `name` (string, required)
- `description` (string, optional)
- `domain` (string, optional)
- `theme_id` (uuid, optional)

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
Request fields:
- `name` (string, required)
- `slug` (string, required)
- `description` (string, optional)
- `preview_image` (file, required)
- `version` (string, required)
- `is_active` (boolean, optional)

```bash
curl -X POST http://127.0.0.1:8000/shops/themes/ \
  -H "Authorization: Bearer <access_token>" \
  -F "name=Classic" \
  -F "slug=classic" \
  -F "description=Classic layout" \
  -F "version=1.0.0" \
  -F "is_active=true" \
  -F "preview_image=@/path/to/theme-preview.png"
```

**Theme Settings**
Request fields:
- `primary_color` (string, optional)
- `secondary_color` (string, optional)
- `logo` (file, optional)
- `banner_image` (file, optional)
- `font_family` (string, optional)

`POST /shops/theme-settings/` creates settings once (if missing).
`GET /shops/theme-settings/` returns current settings.
`PATCH /shops/theme-settings/` updates existing settings.

```bash
curl -X POST http://127.0.0.1:8000/shops/theme-settings/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_color": "#111111",
    "secondary_color": "#ffffff",
    "font_family": "Arial"
  }'
```

```bash
curl -X PATCH http://127.0.0.1:8000/shops/theme-settings/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_color": "#1D4ED8",
    "secondary_color": "#F8FAFC",
    "font_family": "Poppins"
  }'
```

## Catalog
Base path: `/catalog/`

**Create Category**
Request fields:
- `name` (string, required)
- `description` (string, optional)
- `parent` (uuid, optional)
- `slug` (string, optional, auto-generated if omitted)

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
Request fields:
- `name` (string, required)
- `description` (string, optional)
- `price` (decimal, required)
- `supplier_price` (decimal, optional)
- `minimum_wholesale_quantity` (integer, optional)
- `shop_owner_price` (decimal, optional)
- `category_id` (uuid, optional)
- `is_active` (boolean, optional)
- `weight` (float, optional)
- `dimensions` (json, optional)
- `tags` (list of strings, optional)
- `supplier_id` (uuid, optional)
- `variants` (list, optional)
- `media` (list, optional)
- `stock` (integer >= 0, optional) if provided, sets default stock for variants without stock.
  If no variants are provided, a `Default` variant is created with this stock (or `1` if omitted).

`variants` item fields:
- `variant_name` (string, required)
- `price` (decimal, optional)
- `attributes` (json, optional)
- `stock` (integer, optional)

`media` item fields:
- `media_type` (enum: `IMAGE`|`VIDEO`|`DOCUMENT`, required)
- `file` (file path or upload, required)
- `caption` (string, optional)
- `is_primary` (boolean, optional)
- `order` (integer, optional)

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
Request fields:
- `rating` (integer 1-5, required)
- `title` (string, optional)
- `comment` (string, optional)

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

## Hub (Social Feed & Interactions)
Base path: `/hub/`

All Hub endpoints require JWT authentication.

**Get My Hub Profile**
`GET /hub/profiles/me/`

Automatically creates/updates a hub profile based on the authenticated user if missing.

```bash
curl -X GET http://127.0.0.1:8000/hub/profiles/me/ \
  -H "Authorization: Bearer <access_token>"
```

**Follow Seller Profile**
`POST /hub/profiles/<profile_id>/follow/`

Notes:
- You cannot follow yourself.
- Only seller profiles can be followed.

```bash
curl -X POST http://127.0.0.1:8000/hub/profiles/<profile_id>/follow/ \
  -H "Authorization: Bearer <access_token>"
```

**Unfollow Seller Profile**
`DELETE /hub/profiles/<profile_id>/follow/`

```bash
curl -X DELETE http://127.0.0.1:8000/hub/profiles/<profile_id>/follow/ \
  -H "Authorization: Bearer <access_token>"
```

**List Hub Posts**
`GET /hub/posts/`

Optional query params:
- `mine=true|false` (if true, returns only current user's posts)

```bash
curl -X GET "http://127.0.0.1:8000/hub/posts/?mine=true" \
  -H "Authorization: Bearer <access_token>"
```

**Create Hub Post**
`POST /hub/posts/`

Request fields:
- `title` (string, required)
- `caption` (string, required)
- `picture` (file, optional)

Only seller profiles can create posts.

```bash
curl -X POST http://127.0.0.1:8000/hub/posts/ \
  -H "Authorization: Bearer <access_token>" \
  -F "title=New Arrival" \
  -F "caption=Fresh stock just landed" \
  -F "picture=@/path/to/photo.jpg"
```

**Post Detail**
`GET /hub/posts/<post_id>/`

```bash
curl -X GET http://127.0.0.1:8000/hub/posts/<post_id>/ \
  -H "Authorization: Bearer <access_token>"
```

**Update Post (Owner Only)**
`PATCH /hub/posts/<post_id>/` or `PUT /hub/posts/<post_id>/`

```bash
curl -X PATCH http://127.0.0.1:8000/hub/posts/<post_id>/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"caption":"Updated caption"}'
```

**Delete Post (Owner Only)**
`DELETE /hub/posts/<post_id>/`

```bash
curl -X DELETE http://127.0.0.1:8000/hub/posts/<post_id>/ \
  -H "Authorization: Bearer <access_token>"
```

**List Post Comments**
`GET /hub/posts/<post_id>/comments/`

```bash
curl -X GET http://127.0.0.1:8000/hub/posts/<post_id>/comments/ \
  -H "Authorization: Bearer <access_token>"
```

**Create Post Comment**
`POST /hub/posts/<post_id>/comments/`

Request fields:
- `content` (string, required)

```bash
curl -X POST http://127.0.0.1:8000/hub/posts/<post_id>/comments/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"content":"Looks great!"}'
```

**Like Post**
`POST /hub/posts/<post_id>/like/`

```bash
curl -X POST http://127.0.0.1:8000/hub/posts/<post_id>/like/ \
  -H "Authorization: Bearer <access_token>"
```

**Unlike Post**
`DELETE /hub/posts/<post_id>/like/`

```bash
curl -X DELETE http://127.0.0.1:8000/hub/posts/<post_id>/like/ \
  -H "Authorization: Bearer <access_token>"
```

**Buyer Feed** (role: `CUSTOMER`)
`GET /hub/buyer/feed/`

Feed mix:
- 60% followed sellers' posts
- 30% trending posts
- 10% new/random posts

```bash
curl -X GET "http://127.0.0.1:8000/hub/buyer/feed/?limit=30" \
  -H "Authorization: Bearer <access_token>"
```

**Seller Feed** (roles: `SHOP_OWNER`, `SUPPLIER`)
`GET /hub/seller/feed/`

Feed mix:
- 40% trending products
- 30% new products
- 20% followed sellers activity
- 10% random/discovery

```bash
curl -X GET "http://127.0.0.1:8000/hub/seller/feed/?limit=30" \
  -H "Authorization: Bearer <access_token>"
```

**Seller Feed Buckets** (roles: `SHOP_OWNER`, `SUPPLIER`)
`GET /hub/seller/feed/buckets/`

Returns each seller feed bucket separately for sectioned UI rendering.

```bash
curl -X GET "http://127.0.0.1:8000/hub/seller/feed/buckets/?limit=30" \
  -H "Authorization: Bearer <access_token>"
```

## Orders & Cart
Base path: `/order/`

**Add to Cart**
Request fields:
- `shop_id` (uuid, required)
- `product_id` (uuid, required)
- `variant_id` (uuid, optional)
- `quantity` (integer >= 1, required)

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
Request fields:
- `delivery_address` (string, required)
- `payment_method` (string, required)
- `delivery_method` (enum: `courier`|`seller`, optional, default `courier`)

```bash
curl -X POST http://127.0.0.1:8000/order/cart/checkout/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "delivery_address": "123 Main St",
    "payment_method": "santimpay",
    "delivery_method": "courier"
  }'
```

**Buy Now (Create Order)**
Request fields:
- `shop_id` (uuid, required)
- `product_id` (uuid, required)
- `variant_id` (uuid, optional)
- `quantity` (integer, optional, default 1)
- `delivery_address` (string, required)
- `payment_method` (string, required)
- `delivery_method` (enum: `courier`|`seller`, optional, default `courier`)

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
    "payment_method": "santimpay",
    "delivery_method": "seller"
  }'
```

**List User Orders**
```bash
curl -X GET http://127.0.0.1:8000/order/orders/ \
  -H "Authorization: Bearer <access_token>"
```

**Shop Owner: Update Delivery Method**
`PATCH /order/orders/<order_id>/delivery-method/`

Request fields:
- `delivery_method` (enum: `courier`|`seller`, required)

Notes:
- Only the shop owner of that order can update it.
- It cannot be changed after shipment creation or terminal statuses.

Example:
```bash
curl -X PATCH http://127.0.0.1:8000/order/orders/<order_id>/delivery-method/ \
  -H "Authorization: Bearer <shop_owner_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "delivery_method": "seller"
  }'
```

## Payments (SantimPay)
Base path: `/payment/`

**Required Settings**
Set these in Django `settings.py` or environment variables:
`SANTIMPAY_MERCHANT_ID`, `SANTIMPAY_PRIVATE_KEY`, `SANTIMPAY_TEST_BED`,
`SANTIMPAY_SUCCESS_REDIRECT_URL`, `SANTIMPAY_FAILURE_REDIRECT_URL`,
`SANTIMPAY_NOTIFY_URL`

Notes:
- One platform merchant ID is used for all incoming payments and all outgoing payouts.
- Per-user `merchant_id` is no longer used.

**Direct Payment**
Request fields:
- `order_id` (uuid, required)
- `payment_method` (string, required)
- `phone_number` (string, required)
- `notify_url` (url, optional)

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
Request fields:
- `confirm` (boolean, optional, default true)

```bash
curl -X POST http://127.0.0.1:8000/payment/payouts/request/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

How payout amount is calculated:
- System sums `payment.Earning` rows where `user=<request.user>` and `status=AVAILABLE`.
- That total is paid out in one request.
- On success, those earnings are marked `PAID_OUT`.

**Payout History**
```bash
curl -X GET http://127.0.0.1:8000/payment/payouts/history/ \
  -H "Authorization: Bearer <access_token>"
```

**Request Refund**
Request fields:
- `payment_id` (uuid, required)
- `amount` (decimal, required)
- `reason` (string, optional)

```bash
curl -X POST http://127.0.0.1:8000/payment/refunds/request/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "<payment_id>",
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

## Logistics (Courier)
Base path: `/courier/` (legacy alias also available under `/logistics/`)

Shipment records are created automatically after successful payment webhook sync only for orders with `delivery_method = courier`.
Orders with `delivery_method = seller` are fulfilled by the seller and do not create courier shipments.
Shipments are internal and are auto-assigned to available couriers using round-robin order distribution.
If no courier is currently available, shipment remains `PENDING` until a courier becomes available.

**Courier Dashboard: List Assigned Shipments**
```bash
curl -X GET http://127.0.0.1:8000/courier/shipments/ \
  -H "Authorization: Bearer <courier_access_token>"
```

**Courier Dashboard: Shipment Detail**
```bash
curl -X GET http://127.0.0.1:8000/courier/shipments/<shipment_id>/ \
  -H "Authorization: Bearer <courier_access_token>"
```

**Courier Dashboard: Update Shipment Status**
```bash
curl -X POST http://127.0.0.1:8000/courier/shipments/<shipment_id>/status/ \
  -H "Authorization: Bearer <courier_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_TRANSIT",
    "payload": {
      "note": "Left pickup point"
    }
  }'
```

Supported status inputs include:
- `PENDING`
- `PICKED_UP`
- `IN_TRANSIT`
- `OUT_FOR_DELIVERY`
- `DELIVERED`
- `FAILED`
- `CANCELLED`

Order status mapping:
- `PICKED_UP` -> `confirmed`
- `IN_TRANSIT` -> `processing`
- `OUT_FOR_DELIVERY` -> `shipped`
- `DELIVERED` -> `delivered`
- `FAILED` / `CANCELLED` -> `cancelled` (if not delivered)

## Suppliers Portal
Base path: `/supliers/`

**Supplier Dashboard**
```bash
curl -X GET http://127.0.0.1:8000/supliers/dashboard/ \
  -H "Authorization: Bearer <access_token>"
```

**List/Create Supplier Products**
Request fields (create):
- `name` (string, required)
- `description` (string, optional)
- `price` (decimal, required)
- `supplier_price` (decimal, optional)
- `minimum_wholesale_quantity` (integer, optional)
- `shop_owner_price` (decimal, optional)
- `category_id` (uuid, optional)
- `is_active` (boolean, optional)
- `weight` (float, optional)
- `dimensions` (json, optional)
- `tags` (list of strings, optional)
- `variants` (list, optional)
- `media` (list, optional)
- `stock` (integer >= 0, optional) if provided, sets default stock for variants without stock.
  If no variants are provided, a `Default` variant is created with this stock (or `1` if omitted).

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
Request fields:
- `variant_name` (string, required)
- `price` (decimal, optional)
- `attributes` (json, optional)
- `stock` (integer, required)

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
Request fields:
- `media_type` (enum: `IMAGE`|`VIDEO`|`DOCUMENT`, required)
- `file` (file path or upload, required)
- `caption` (string, optional)
- `is_primary` (boolean, optional)
- `order` (integer, optional)

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
Request fields:
- `stock` (integer >= 0, required)

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
Base path: `/inventory/`

All inventory endpoints require JWT authentication.

**Locations**
```bash
# list
curl -X GET http://127.0.0.1:8000/inventory/locations/ \
  -H "Authorization: Bearer <access_token>"

# create
curl -X POST http://127.0.0.1:8000/inventory/locations/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main WH",
    "type": "WAREHOUSE",
    "contact": {"phone":"+251900000000"}
  }'
```

`GET/PATCH/DELETE /inventory/locations/<id>/`

**Inventory Items**
```bash
# list
curl -X GET http://127.0.0.1:8000/inventory/items/ \
  -H "Authorization: Bearer <access_token>"

# create
curl -X POST http://127.0.0.1:8000/inventory/items/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "variant_id": "<variant_id>",
    "location_id": 1,
    "quantity_available": 20,
    "quantity_reserved": 0
  }'
```

`GET/PATCH/DELETE /inventory/items/<id>/`

**Inventory Actions**
Endpoint: `POST /inventory/items/<id>/actions/`

Request fields:
- `action` (`reserve` | `release` | `confirm` | `adjust`)
- `quantity` (integer >= 1)
- `reason` (string, optional)

Examples:
```bash
curl -X POST http://127.0.0.1:8000/inventory/items/1/actions/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"action":"reserve","quantity":5,"reason":"Order Reserved"}'

curl -X POST http://127.0.0.1:8000/inventory/items/1/actions/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"action":"release","quantity":2,"reason":"Order Released"}'

curl -X POST http://127.0.0.1:8000/inventory/items/1/actions/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"action":"confirm","quantity":2,"reason":"Order Confirmed"}'

curl -X POST http://127.0.0.1:8000/inventory/items/1/actions/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"action":"adjust","quantity":3,"reason":"Manual stock in"}'
```

**Stock Movements**
```bash
# list all movements
curl -X GET http://127.0.0.1:8000/inventory/movements/ \
  -H "Authorization: Bearer <access_token>"

# filter by inventory id
curl -X GET "http://127.0.0.1:8000/inventory/movements/?inventory=1" \
  -H "Authorization: Bearer <access_token>"

# create movement (this also adjusts inventory quantity)
curl -X POST http://127.0.0.1:8000/inventory/movements/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"inventory_id":1,"quantity":-1,"reason":"Shrinkage"}'
```

**Flow Summary**
1. Create location.
2. Create inventory item for a product variant.
3. Reserve stock when order is allocated.
4. Release stock if order is cancelled/rolled back.
5. Confirm stock when order is completed.
6. Review stock movement history for audit.

## Notifications (FCM + In-App)
Base path: `/api/notifications/`

### Configuration
Set these in environment:
- `FCM_PROJECT_ID`
- `FCM_SERVICE_ACCOUNT_FILE` (path to Firebase service account JSON) or `FCM_SERVICE_ACCOUNT_JSON` (raw JSON string)

Install dependency:
`firebase-admin`

### Email Notifications (Optional)
To send the same notifications by email, configure:
- `EMAIL_NOTIFICATIONS_ENABLED=true`
- `EMAIL_BACKEND` (example: `django.core.mail.backends.smtp.EmailBackend`)
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS=true|false`
- `EMAIL_USE_SSL=true|false`
- `DEFAULT_FROM_EMAIL`
- `EMAIL_SEND_ORDER_SHIPPED=true|false` (optional event)
- `EMAIL_SEND_ORDER_DELIVERED=true|false` (optional event)
- `EMAIL_SEND_URGENT_LOW_STOCK=true|false` (urgent only policy)

Local development default is console backend (emails printed to server logs/stdout).

### Email Policy Matrix
| Event | Why Email is Essential | Delivery Rule |
| --- | --- | --- |
| New Order Received | Seller must act quickly | Always email + push |
| Payment Settled / Commission Credited | Seller accounting and audit | Always email + push |
| Order Confirmation / Payment Receipt | Buyer needs purchase record and proof | Always email + push |
| Shipment Delivered | Buyer may miss push | Optional email (toggle with `EMAIL_SEND_ORDER_DELIVERED`) |
| Order Canceled / Refund Completed | Legal, trust, and next steps | Always email + push |
| Low Stock / Inventory Alert | Seller may miss in-app alerts | Email only when urgent (`payload.urgent=true`) |

### Device Token APIs
**Register or update token (JWT required)**
`POST /api/notifications/device-token/`

Request fields:
- `token` (string, required, globally unique)
- `device_type` (enum: `web` | `android`, required)

**Deactivate token(s) (JWT required)**
`DELETE /api/notifications/device-token/`

Request fields:
- `token` (string, optional). If omitted, all active tokens of current user are deactivated.

### Notification Read APIs
**List notifications (paginated)**
`GET /api/notifications/`

**Mark one read**
`PATCH /api/notifications/{id}/read/`

**Mark all read**
`POST /api/notifications/mark-all-read/`

### Frontend Integration Flow
1. User logs in and your app gets a JWT access token.
2. App obtains an FCM token from Firebase SDK.
3. App registers that token:
`POST /api/notifications/device-token/` with `{ "token": "...", "device_type": "web|android" }`.
4. App loads notification inbox:
`GET /api/notifications/` (use pagination fields `count/next/previous/results`).
5. When user opens one notification, mark it read:
`PATCH /api/notifications/{id}/read/`.
6. For "mark all read", call:
`POST /api/notifications/mark-all-read/`.
7. On logout (or token refresh), deactivate old token:
`DELETE /api/notifications/device-token/`.

Frontend behavior notes:
- There is no public "send notification" API for clients.
- Notifications are triggered internally by backend business events (payment, shipping, commissions).
- Use the `payload` object (`type`, `entity_type`, `entity_id`, optional `order_id/commission_id/product_id`) for deep-link routing in the app.

### Trigger Events Implemented
- Customer:
  - `payment_success`
  - `order_shipped`
  - `order_delivered`
  - `order_cancelled`
  - `refund_completed`
- Shop Owner:
  - `new_order`
  - `payment_confirmed`
- Supplier:
  - `product_sold`
- Marketer:
  - `commission_created`
  - `commission_approved`

### Payload Standard
All notifications include payload with:
- `type`
- `entity_id`
- `entity_type` (`order`, `commission`, `refund`, or `product`)

Optional:
- `order_id`
- `commission_id`
- `product_id`
- `refund_id`


### New Features Added
- Commission lifecycle: `PENDING` on payment, `APPROVED` on delivery.
- Shop owner control to activate, pause, resume, or end contracts.

### How It Works (Flow)
2. **Activate contract**: shop owner activates it (only active contracts earn).
4. **Payment confirmed**: when order status becomes `PAID`, commission rows are created as `PENDING`.
5. **Delivery confirmed**: when order status becomes `DELIVERED`, commissions become `APPROVED`.

### Contracts
**Create Contract**
Request fields:
- `shop_id` (uuid, required)
- `commission_rate` (decimal percent, optional)
- `start_date` (date, optional)
- `end_date` (date, optional)
- `product_ids` (list of product UUIDs, optional)

```bash
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "shop_id": "<shop_id>",
    "commission_rate": "10.00",
    "product_ids": ["<product_id_1>", "<product_id_2>"]
  }'
```

**Update Contract (dates, rate, products)**
```bash
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "commission_rate": "12.50",
    "product_ids": ["<product_id_1>"]
  }'
```

**Contract Status Actions (Shop Owner)**
```bash
  -H "Authorization: Bearer <access_token>"

  -H "Authorization: Bearer <access_token>"

  -H "Authorization: Bearer <access_token>"

  -H "Authorization: Bearer <access_token>"
```

### Commissions
**List Commissions**
```bash
  -H "Authorization: Bearer <access_token>"
```

Filter by status:

### Dashboard
```bash
  -H "Authorization: Bearer <access_token>"
```

### Commission Flow Summary
- Contract status must be `ACTIVE`.
- Commissions are created when payment is confirmed (order status becomes `PAID`).
- Commissions are approved when order status becomes `DELIVERED`.

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
6. SantimPay webhook updates order/payment status and creates shipment for orders using `delivery_method = courier`, then system auto-assigns the next available courier in round-robin order.
7. Internal courier dashboard updates shipment and order delivery status (`/courier/shipments/<shipment_id>/status/`).

**3) Basic Frontend Data Screens**
Use these endpoints as your first screens:
1. Shop list: `GET /shops/`
2. Product list: `GET /catalog/products/` (your frontend can filter client-side)
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
    "payment_method": "santimpay",
    "delivery_method": "courier"
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



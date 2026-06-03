# Shikela Backend - Complete System Architecture & Guide

## Overview

**Shikela** is a multi-vendor e-commerce platform built with Django REST Framework. It's designed for managing multiple shops, products, orders, payments, and logistics all in one backend system.

**Key Tech Stack:**
- **Backend Framework:** Django 6.0.2 + Django REST Framework
- **Database:** PostgreSQL (with SQLite as dev fallback)
- **Cache/Message Broker:** Redis
- **Async Tasks:** Celery + Celery Beat
- **Authentication:** JWT (Simple JWT)
- **Payment Gateway:** SantimPay
- **Push Notifications:** Firebase Cloud Messaging (FCM)
- **API Documentation:** drf-spectacular (OpenAPI/Swagger)

---

## System Architecture

### 1. **Core Components**

```
shikela-backend/
├── core/              # Django project settings & URL routing
├── account/           # User management & authentication
├── shop/              # Shop/store management
├── catalog/           # Products, categories, variants
├── order/             # Shopping cart & orders
├── payment/           # Payment processing & earnings
├── courier/           # Shipping & delivery management
├── inventory/         # Stock management & locations
├── notifications/     # Email & push notifications
├── analytics/         # Order & sales analytics
├── marketer/          # Marketer contracts & commission
├── hub/               # Hub management
├── supliers/          # Supplier management
└── requirements.txt   # Python dependencies
```

### 2. **User Roles**

The system supports **5 different user roles**, each with different capabilities:

```python
ROLES:
- CUSTOMER      # Buys products from shops
- SHOP_OWNER    # Manages a shop & products
- SUPPLIER      # Supplies products to shops
- COURIER       # Handles order delivery
- MARKETER      # Promotes & sells products (commission-based)
```

---

## 3. **Data Models & Relationships**

### A. **User Model** (account/models.py)
```python
User (Custom Django User)
├── role: CUSTOMER | SHOP_OWNER | SUPPLIER | COURIER | MARKETER
├── email: unique
├── phone_number, location
├── is_verified: Boolean (email verification status)
├── badge: "none" | "verified" | "vip" | "trusted"
├── license_document: For shop owners/suppliers
├── avatar, company_name, policy
└── bank_account_type: For payouts (bank/mobile money)
```

### B. **Shop Model** (shop/models.py)
```python
Shop
├── owner: OneToOne(User with role=SHOP_OWNER)
├── name, description, domain
├── theme: ForeignKey(Theme) - visual customization
├── theme_settings: OneToOne(ShopThemeSettings)
│   ├── primary_color, secondary_color
│   ├── logo, banner_image
│   └── font_family
└── created_at, updated_at
```

### C. **Product Catalog** (catalog/models.py)
```python
Product
├── name, description
├── shop: ForeignKey(Shop) - which shop sells it
├── supplier: ForeignKey(User, role=SUPPLIER) - optional
├── category: ForeignKey(Category)
├── price, discount_price
├── images
└── variants: ProductVariant[] (sizes, colors, etc)

Category
├── name, slug
├── parent: Recursive self-relationship (subcategories)
└── subcategories: Reverse relation
```

### D. **Order & Cart** (order/models.py)
```python
Cart
├── user: ForeignKey(User)
├── shop: ForeignKey(Shop) - one cart per shop per user
└── items: CartItem[]

CartItem
├── cart: ForeignKey(Cart)
├── product: ForeignKey(Product)
├── variant: ForeignKey(ProductVariant, optional)
├── marketer_contract: ForeignKey(MarketerContract, optional)
└── quantity: Integer

Order
├── user: ForeignKey(User)
├── order_number: Unique string
├── status: pending|paid|confirmed|processing|shipped|delivered|cancelled|refunded
├── total_amount: Decimal
├── delivery_method: COURIER|PICKUP
├── shipping_address, note
├── items: OrderItem[]
└── shipment: Shipment (one-to-one)
```

### E. **Payment Processing** (payment/models.py)
```python
Payment
├── order: ForeignKey(Order)
├── user: ForeignKey(User)
├── amount: Decimal
├── status: PENDING|PROCESSING|COMPLETED|FAILED|REFUNDED
├── provider: "SANTIMPAY"
├── provider_reference: External transaction ID
├── is_verified: Boolean
└── metadata: JSONField

Earning
├── user: ForeignKey(User)
├── amount: Decimal
├── status: AVAILABLE|PENDING|WITHDRAWN
├── created_at, updated_at
```

### F. **Shipping & Logistics** (courier/models.py)
```python
CourierProfile
├── user: OneToOne(User with role=COURIER)
├── is_available: Boolean
├── vehicle_type: BIKE|CAR|VAN|TRUCK|OTHER
├── location, phone
└── created_at, updated_at

Shipment
├── order: OneToOne(Order)
├── courier: ForeignKey(User, role=COURIER)
├── status: PENDING|PICKED_UP|IN_TRANSIT|OUT_FOR_DELIVERY|DELIVERED|FAILED|CANCELLED
├── assigned_at: When courier was assigned
├── last_event, last_payload: Webhook tracking
└── metadata: JSONField
```

---

## 4. **API Endpoints Structure**

### Authentication (`/auth/`)
```
POST   /auth/register/              # Register customer
POST   /auth/register-shop-owner/   # Register shop owner
POST   /auth/login/                 # JWT login
POST   /auth/refresh/               # Refresh token
GET    /auth/user/{id}/             # Get user profile
PATCH  /auth/user/{id}/             # Update user profile
DELETE /auth/user/{id}/             # Delete user
```

### Shops (`/shops/`)
```
GET    /shops/                      # List all shops
POST   /shops/                      # Create shop (shop owner)
GET    /shops/{id}/                 # Get shop details
PATCH  /shops/{id}/                 # Update shop
GET    /shops/theme-settings/       # Get shop theme settings
PATCH  /shops/theme-settings/       # Update theme settings
```

### Catalog (`/catalog/`)
```
GET    /catalog/categories/         # List categories
POST   /catalog/categories/         # Create category
GET    /catalog/products/           # List products
POST   /catalog/products/           # Create product (shop owner)
GET    /catalog/products/{id}/      # Get product details
PATCH  /catalog/products/{id}/      # Update product
GET    /catalog/products/{id}/variants/  # Product variants
```

### Shopping & Orders (`/order/`)
```
POST   /order/cart/add/             # Add to cart
POST   /order/cart/remove/          # Remove from cart
GET    /order/cart/                 # View cart
POST   /order/checkout/             # Create order from cart
GET    /order/orders/               # List user's orders
GET    /order/orders/{id}/          # Order details
PATCH  /order/orders/{id}/          # Update order status
```

### Payments (`/payment/`)
```
POST   /payment/initiate/           # Start payment
GET    /payment/status/{id}/        # Check payment status
POST   /payment/webhook/santimpay/  # Webhook for payment updates
GET    /payment/earnings/           # User earnings summary
POST   /payment/withdraw/           # Request payout
```

### Shipping (`/courier/` or `/logistics/`)
```
GET    /courier/shipments/          # List shipments
GET    /courier/shipments/{id}/     # Shipment status
PATCH  /courier/shipments/{id}/     # Update shipment status
POST   /courier/assign/             # Assign courier to shipment
GET    /courier/profile/            # Courier's profile
```

### Analytics (`/analytics/`)
```
GET    /analytics/sales/            # Sales statistics
GET    /analytics/orders/           # Order analytics
GET    /analytics/revenue/          # Revenue reports
```

### Notifications (`/api/notifications/`)
```
POST   /api/notifications/subscribe/    # Subscribe to push
GET    /api/notifications/              # List notifications
POST   /api/notifications/mark-read/    # Mark as read
```

### Inventory (`/inventory/`)
```
GET    /inventory/locations/        # List inventory locations
GET    /inventory/items/            # List inventory items
POST   /inventory/items/            # Create inventory item
GET    /inventory/stock-movements/  # Stock movement history
POST   /inventory/actions/          # Record inventory action
```

---

## 5. **Request/Response Flow**

### Example: Customer Places Order

```
1. CUSTOMER REGISTRATION
   POST /auth/register/ 
   → User created with role=CUSTOMER
   → Email verification sent
   → JWT tokens returned

2. AUTHENTICATION
   POST /auth/login/
   → Access token (1 hour) returned in response
   → Refresh token (30 days) returned as HttpOnly cookie
   → Future requests include: Authorization: Bearer <access_token>

3. BROWSE PRODUCTS
   GET /catalog/categories/
   GET /catalog/products/?category=electronics
   GET /catalog/products/{id}/ (includes variant details)

4. ADD TO CART
   POST /order/cart/add/
   {
       "shop_id": "uuid",
       "product_id": "uuid",
       "variant_id": "uuid (optional)",
       "quantity": 2
   }
   → CartItem created, Cart auto-created if needed

5. CHECKOUT
   POST /order/checkout/
   {
       "shop_id": "uuid",
       "shipping_address": "...",
       "delivery_method": "COURIER",
       "payment_method": "SANTIMPAY"
   }
   → Order created with status=PENDING
   → Shipment created with status=PENDING
   → Cart items cleared

6. PAYMENT
   POST /payment/initiate/
   {
       "order_id": "uuid",
       "amount": 500.00
   }
   → Redirect to SantimPay checkout
   → SantimPay processes payment
   → Webhook received at /payment/webhook/santimpay/
   → Payment status updated to COMPLETED
   → Order status updated to PAID
   → Notification sent to customer & shop owner

7. FULFILLMENT
   Shop owner sees order in admin
   PATCH /order/orders/{id}/ → status=CONFIRMED
   → Notification sent to courier

8. DELIVERY
   Courier sees assigned shipment
   PATCH /courier/shipments/{id}/ → status=PICKED_UP
   PATCH /courier/shipments/{id}/ → status=IN_TRANSIT
   PATCH /courier/shipments/{id}/ → status=OUT_FOR_DELIVERY
   PATCH /courier/shipments/{id}/ → status=DELIVERED
   → Push notifications sent to customer at each step
   → Order status auto-updates to DELIVERED
   → Seller earnings recorded in payment.Earning

9. PAYOUT
   Shop owner views /payment/earnings/
   POST /payment/withdraw/
   {
       "amount": 450.00  (50.00 = platform fee)
   }
   → Payout request created
   → Bank transfer initiated
```

---

## 6. **Authentication System**

### JWT Token Flow

```
Access Token: 
- Lifetime: 60 minutes
- Stored: Response body
- Sent with every request: Authorization: Bearer <token>
- Contains: User ID, role, permissions

Refresh Token:
- Lifetime: 30 days
- Stored: HttpOnly cookie (secure, can't be accessed by JS)
- Used to: Get new access token when expired
- Auto-rotates: New refresh token issued on refresh
```

### Authorization

```python
# In REST Framework
DEFAULT_PERMISSION_CLASSES = (
    "rest_framework.permissions.IsAuthenticated",
)

# Most endpoints require login
# Some endpoints check user.role:
- Shop creation: only SHOP_OWNER
- Product creation: only SHOP_OWNER or SUPPLIER
- Courier assignment: only COURIER
```

---

## 7. **Payment Processing (SantimPay Integration)**

### Flow

```
1. Order created with total_amount
2. Payment.initiate endpoint called
3. System creates Payment record with:
   - status = PENDING
   - provider = "SANTIMPAY"
4. Redirect to SantimPay checkout
5. Customer completes payment on SantimPay
6. SantimPay sends POST to /payment/webhook/santimpay/
7. System verifies webhook signature
8. Payment status updated to COMPLETED
9. Order status updated to PAID
10. Seller earnings recorded
11. Push notification sent
```

### Config (core/settings.py)

```python
SANTIMPAY_TEST_BED = True  # Testnet by default
SANTIMPAY_MERCHANT_ID = "9e2dab64-..."  # Platform merchant
SANTIMPAY_PRIVATE_KEY = "..."  # EC private key
SANTIMPAY_SUCCESS_REDIRECT_URL = "http://localhost:8000/payment/success"
```

### Payout System

```
Earnings flow:
1. Customer pays Order → Payment.amount goes to seller
2. Earning record created with status=AVAILABLE
3. Shop owner can request withdrawal
4. Payout processed to bank account
5. Earning.status changes to WITHDRAWN
```

---

## 8. **Asynchronous Task Processing (Celery)**

### Task Examples

Celery processes long-running tasks in background:

```python
# Email notifications
- Send order confirmation emails
- Send payment receipts
- Send shipping notifications
- Email verification links

# Push notifications (FCM)
- Notify customer of order status changes
- Notify courier of new shipments
- Notify shop owner of new orders

# Scheduled tasks (Celery Beat)
- Clear expired sessions
- Send reminder notifications
- Generate analytics reports
- Process pending payouts
```

### Architecture

```
Worker Process (celery worker)
├── Listens to Redis queue
├── Picks up tasks
├── Executes task code
└── Stores result in Redis

Scheduler (celery beat)
├── Watches scheduled tasks
├── Enqueues tasks at intervals
└── Ensures tasks run on schedule

Redis
├── Holds message queue
├── Stores task results
└── Acts as cache backend
```

---

## 9. **Notifications System**

### Email Notifications

```python
# Configured in settings
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"  # Dev
# or SMTP for production

Triggers:
- User registration → verification email
- Order placed → confirmation email
- Payment completed → receipt email
- Order shipped → shipping email
- Order delivered → delivery email
```

### Push Notifications (FCM)

```python
# Firebase Cloud Messaging
FCM_PROJECT_ID = "your-project"
FCM_SERVICE_ACCOUNT_FILE = "path/to/firebase-adminsdk.json"

Notification lifecycle:
1. User subscribes via /api/notifications/subscribe/
2. FCM device token stored
3. Server sends notification to FCM
4. FCM delivers to mobile app
5. Notification saved in DB
6. User can mark as read
```

---

## 10. **Data Flow Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Web/Mobile)                      │
├─────────────────────────────────────────────────────────────┤
│  Authentication (JWT) → All requests include auth header   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Django REST API (Gunicorn)                     │
│  ┌─────────────────────────────────────────────────────────┤
│  │ URL Routing (core/urls.py)                             │
│  │ ├── /auth/        → account/views.py                   │
│  │ ├── /shops/       → shop/views.py                      │
│  │ ├── /catalog/     → catalog/views.py                   │
│  │ ├── /order/       → order/views.py                     │
│  │ ├── /payment/     → payment/views.py                   │
│  │ ├── /courier/     → courier/views.py                   │
│  │ └── /analytics/   → analytics/views.py                 │
│  └─────────────────────────────────────────────────────────┤
│  Views (DRF ViewSets) ↓ Serializers ↓ Models              │
└────────────┬──────────────────────────┬─────────────────────┘
             │                          │
             ▼ (SQL)                    ▼ (Background Tasks)
    ┌──────────────────┐        ┌──────────────────┐
    │   PostgreSQL     │        │  Redis Queue     │
    │   Database       │        │  (Celery Broker) │
    │                  │        └────────┬─────────┘
    │ Users            │                 │
    │ Shops            │                 ▼
    │ Products         │        ┌──────────────────┐
    │ Orders           │        │ Celery Worker    │
    │ Payments         │        │ (Background Job) │
    │ Shipments        │        └──────────────────┘
    │ Earnings         │
    └──────────────────┘
             ▲
             │ (Cache)
    ┌────────────────────┐
    │   Redis Cache      │
    │ (django-redis)     │
    └────────────────────┘

External Services:
├── SantimPay (payment processing)
├── Firebase (push notifications)
├── Email Server (SMTP)
└── SMS Provider (optional)
```

---

## 11. **Database Schema Relationships**

```
User (Custom Auth Model)
├── 1:1 → Shop (owner)
├── 1:M → Order (buyer)
├── 1:M → Payment (payer)
├── 1:M → Earning (seller)
├── 1:1 → CourierProfile (courier)
├── 1:M → Shipment (assigned courier)
└── 1:M → Product (supplier)

Shop
├── 1:M → Product (sold by)
├── 1:M → Cart (customer carts)
├── 1:M → Order
└── 1:1 → ShopThemeSettings

Product
├── M:1 → Shop
├── M:1 → Category
├── M:1 → User (supplier)
├── 1:M → ProductVariant
├── 1:M → CartItem
└── 1:M → OrderItem

Order
├── M:1 → User (buyer)
├── M:1 → Shop
├── 1:M → OrderItem
├── 1:M → Payment
└── 1:1 → Shipment

Shipment
├── 1:1 → Order
└── M:1 → User (courier)

Cart
├── M:1 → User
├── M:1 → Shop
└── 1:M → CartItem

CartItem
├── M:1 → Cart
├── M:1 → Product
└── M:1 → ProductVariant
```

---

## 12. **Running the Application**

### Development (Local)

```bash
# 1. Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with local settings

# 3. Initialize DB
python manage.py migrate

# 4. Create admin user
python manage.py createsuperuser

# 5. Run server
python manage.py runserver 0.0.0.0:8000

# 6. Run Celery (in separate terminal)
celery -A core worker -l info

# 7. Run Celery Beat (scheduled tasks)
celery -A core beat -l info
```

### Docker (Development)

```bash
# 1. Setup environment
cp .env.docker .env

# 2. Start all services
docker-compose up -d

# 3. Create admin user
docker-compose exec web python manage.py createsuperuser

# 4. Access API
# http://localhost:8000
# http://localhost:8000/admin
```

---

## 13. **Configuration & Environment Variables**

### Critical Settings

```env
# Django
DEBUG=False                          # Set to False in production
DJANGO_SECRET_KEY=your-secret-key   # Change this!
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Cache & Tasks
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Payment
SANTIMPAY_TEST_BED=true
SANTIMPAY_MERCHANT_ID=your-merchant-id
SANTIMPAY_PRIVATE_KEY="..."

# Notifications
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Firebase (optional)
FCM_PROJECT_ID=your-project-id
FCM_SERVICE_ACCOUNT_FILE=/path/to/firebase-adminsdk.json
```

---

## 14. **Common Operations**

### Creating a Shop

```bash
# 1. Register as shop owner
curl -X POST http://localhost:8000/auth/register-shop-owner/ \
  -d '{
    "email": "owner@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'

# 2. Login and get token
curl -X POST http://localhost:8000/auth/login/ \
  -d '{
    "email": "owner@example.com",
    "password": "SecurePass123!"
  }'

# 3. Create shop (requires token)
curl -X POST http://localhost:8000/shops/ \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "name": "My Electronics Store",
    "description": "Best electronics in town"
  }'

# 4. Customize shop theme
curl -X PATCH http://localhost:8000/shops/theme-settings/ \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "primary_color": "#FF5733",
    "secondary_color": "#FFFFFF"
  }'
```

### Adding Products

```bash
curl -X POST http://localhost:8000/catalog/products/ \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "name": "Laptop",
    "description": "High performance laptop",
    "category_id": "uuid",
    "price": 1500.00,
    "shop_id": "uuid"
  }'
```

### Processing Orders

```bash
# Shop owner view orders
curl -X GET http://localhost:8000/order/orders/ \
  -H "Authorization: Bearer <shop_owner_token>"

# Update order status
curl -X PATCH http://localhost:8000/order/orders/{id}/ \
  -H "Authorization: Bearer <shop_owner_token>" \
  -d '{"status": "CONFIRMED"}'
```

---

## 15. **Security Considerations**

```python
✓ JWT Authentication on all protected endpoints
✓ CSRF protection on state-changing operations
✓ Password hashing (Django's default PBKDF2)
✓ Email verification for accounts
✓ Role-based access control
✓ HTTPS/SSL recommended for production
✓ HttpOnly cookies for refresh tokens
✓ SQL injection protection (ORM)
✓ XSS protection (serializers)

⚠ TODO:
- Rate limiting on auth endpoints
- API key rotation
- Audit logging
- Payment encryption
```

---

## 16. **Troubleshooting**

### Common Issues

```
Issue: "No such table: account_user"
→ Run migrations: python manage.py migrate

Issue: "Connection refused" (Redis)
→ Check Redis is running: redis-cli ping

Issue: "Email not sending"
→ Check EMAIL_BACKEND and credentials in settings

Issue: "Payment webhook not received"
→ Check SantimPay configuration
→ Verify webhook URL in settings
→ Check firewall/routing

Issue: "Celery tasks not executing"
→ Check if worker is running: celery -A core worker
→ Check Redis connection: redis-cli
→ Check broker URL in settings
```

---

## 17. **Testing & Monitoring**

```bash
# Run tests
python manage.py test

# Check API
curl http://localhost:8000/auth/user/
# Should return 401 (Unauthorized) without token

# View logs
docker-compose logs -f web
docker-compose logs -f celery
docker-compose logs -f db

# Check Celery tasks
celery -A core inspect active

# Database admin
http://localhost:8000/admin/
```

---

## Summary

This is a **production-grade e-commerce backend** handling:
- Multi-vendor marketplace with shops
- Complex order management
- Payment processing
- Asynchronous tasks
- Real-time notifications
- Role-based access control
- Analytics & reporting

The system uses **modern Django best practices** with REST APIs, proper authentication, and background job processing for scalability.


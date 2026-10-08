# Project 3 Verification and Test Breakdown

## 1. Acceptance Test Suite (`acceptance.sh`)
Validates standard system lifecycle with authentication enabled (`AUTH_ENABLED=true`):
- **Account Registration (`POST /accounts`)**: Registers users `Alice` and `Bob` with initial balance 0 and role `user`.
- **Admin Credit Grant (`POST /accounts/Bob/credits`)**: Course admin grants 100 credits to `Bob`.
- **Create Listing (`POST /listings`)**: `Alice` lists a "Used textbook" for 25 credits with valid Bearer token.
- **Public Browse (`GET /listings`)**: Unauthenticated endpoint browses available listings.
- **Checkout / Order (`POST /orders`)**: `Bob` orders Alice's textbook with valid token; balance debited and credited.
- **Persistence Verification**: Services restart; order and balances remain intact.

---

## 2. Attack Test Suite (`attack.sh`) — 10 Rejection Tests

| Test | Description | Resulting Status | Rejecting Decision (File & Line) | Business Handler Runs? | Condition |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **Test 1** | Wrong-password login | `401 Unauthorized` | `login-service/login_service.go:149` | No | `verifyPassword` fails against Argon2id hash in `credentials`. |
| **Test 2** | Regular user cannot grant credits | `403 Forbidden` | `marketplace-service/authorization.go:100` | No | Caller has role `user`; `allowsRole("admin")` returns false at line 96. |
| **Test 3** | Admin cannot grant credits to admin account | `400 Bad Request` | `marketplace-service/marketplace/credits.go:27, 41` | **Yes** | SQL update filters out admin accounts; handler catches and returns `ErrCreditTargetNotUser`. |
| **Test 4** | Missing token cannot create a listing | `401 Unauthorized` | `marketplace-service/authorization.go:76` | No | `auth.Bearer` fails to extract token from `Authorization` header. |
| **Test 5** | Invalid token cannot create a listing | `401 Unauthorized` | `marketplace-service/authorization.go:81` | No | `auth.Verify` fails cryptographic verification against Ed25519 public key. |
| **Test 6** | Bob cannot create a listing for Alice | `403 Forbidden` | `marketplace-service/authorization.go:100` | No | `matchBody("seller_id")` fails because body (`Alice`) != token subject (`Bob`). |
| **Test 7** | Admin cannot create a listing | `403 Forbidden` | `marketplace-service/authorization.go:100` | No | Caller has role `admin`; `allowsRole("user")` returns false at line 96. |
| **Test 8** | Alice cannot place an order for Bob | `403 Forbidden` | `marketplace-service/authorization.go:100` | No | `matchBody("buyer_id")` fails because body (`Bob`) != token subject (`Alice`). |
| **Test 9** | Admin cannot place an order | `403 Forbidden` | `marketplace-service/authorization.go:100` | No | Caller has role `admin`; `allowsRole("user")` returns false at line 96. |
| **Test 10** | Alice cannot read Bob's account | `403 Forbidden` | `marketplace-service/authorization.go:100` | No | `matchPath("account_id")` fails because path (`Bob`) != token subject (`Alice`). |

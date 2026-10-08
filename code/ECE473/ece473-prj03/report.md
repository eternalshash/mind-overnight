# Project 3 Report

## Section II

1. **Explain the purpose of the package argon2 used in the login service. Why don't the login service store the password directly into the database?**
   Argon2 is a secure key derivation function used to hash passwords before storing them. The login service stores hashes instead of plaintext passwords to protect user credentials; if the database is ever compromised, the attackers cannot easily reverse the hashes to obtain the actual passwords.

2. **Explain why login holds the private signing key while marketplace has only the public verification key.**
   The login service is solely responsible for authenticating users and issuing JSON Web Tokens (JWTs), which requires the private signing key. The marketplace service only needs to verify the authenticity and integrity of those tokens, which is safely accomplished using the corresponding public key. This separation of concerns adheres to the principle of least privilege and prevents a compromise of the marketplace from allowing forged JWTs.

3. **Among stopping and restarting services, rotating secrets while retaining the database, and resetting everything, which operations invalidate existing JWTs? Which delete account data?**
   - Rotating secrets invalidates existing JWTs because the new signing and verification keys will no longer match the previously issued tokens.
   - Resetting everything (database reset) deletes all account data.
   - Simply stopping and restarting services does neither.

4. **How to update password for course-admin? How to update password for other users?**
   - The password for `course-admin` is updated by modifying the contents of `secrets/admin-password` and restarting the login service, which detects the account on startup and updates the password hash if it differs.
   - For other users, there is currently no implemented functionality to update passwords once they are registered.

## Section III

1. **Explain why we use the authorization wrapper instead of modify each RESTful handler.**
   Using a wrapper (decorator pattern) centralizes the authorization logic, separating it from the business logic. It promotes code reuse across multiple routes and avoids cluttering individual handlers with repetitive token extraction, verification, and role-checking code.

2. **Referring to 'marketplace-service/main.go' and 'marketplace-service/authorization.go', explain how 'allowRole', 'allowAny', 'matchBody', 'matchPath', 'matchAny' work. In particular, why 'POST /orders' should use 'matchBody' and 'GET /accounts/{account_id}' should use 'matchPath'?**
   - `allowRole`: Returns true if the token's role strictly matches a specified string.
   - `allowAny`: Always returns true, permitting any role.
   - `matchBody`: Extracts a specified field from the JSON request body and returns true if it matches the token's subject.
   - `matchPath`: Extracts a specified parameter from the request URL path and returns true if it matches the token's subject.
   - `matchAny`: Always returns true, permitting any token subject.
   - `POST /orders` uses `matchBody` because the buyer identity (`buyer_id`) is submitted as part of the JSON payload.
   - `GET /accounts/{account_id}` uses `matchPath` because the target account identity is provided directly in the URL path.

3. **Show the lines of code you have added for the authorization wrapper and the three protected routes. Explain each route's identity and role rules and how it is checked in the wrapper.**
   
   **main.go additions:**
   ```go
   mux.HandleFunc("POST /orders", requireAuthorization(
       public, matchBody("buyer_id"), allowRole("user"), createOrderHandler(store),
   ))
   mux.HandleFunc("GET /accounts/{account_id}", requireAuthorization(
       public, matchPath("account_id"), allowAny(), accountHandler(store),
   ))
   mux.HandleFunc("POST /accounts/{account_id}/credits", requireAuthorization(
       public, matchAny(), allowRole("admin"), grantCreditsHandler(store),
   ))
   ```

   **authorization.go additions:**
   ```go
   match, err := matchesID(r, identity.Subject)
   if err != nil {
       writeError(w, http.StatusBadRequest, "invalid identity field")
       return
   }
   if match && allowsRole(identity.Role) {
       next(w, r)
       return
   }
   writeError(w, http.StatusForbidden, "identity or role does not permit this operation")
   ```
   **Explanation:**
   - `POST /orders`: Ensures the `buyer_id` in the body matches the token subject and requires the `user` role.
   - `GET /accounts/{account_id}`: Ensures the URL path parameter matches the token subject and permits `allowAny` role.
   - `POST /accounts/{account_id}/credits`: Uses `matchAny` for identity since admins can grant credits to others, but strictly requires the `admin` role.
   The wrapper calls the provided `matchesID` and `allowsRole` filters; if `matchesID` throws an error, it returns HTTP 400. If both checks pass, it proceeds to the business handler. If not, it falls through and returns HTTP 403.

4. **Provide evidences of successful acceptance.sh and attack.sh runs. Show representative responses while redact passwords and JWTs from screenshots.**
   *(Note for user: Please capture screenshots of your terminal running `./acceptance.sh` and `./attack.sh` and insert them here, ensuring you redact passwords and JWTs as instructed.)*

5. **For each of attack tests 1 to 10, identify the file and line(s) containing the decision that rejects the request. Explain the condition, the resulting HTTP status, and whether the marketplace business handler runs, when applicable.**
   
   1. **Test 1 (Wrong-password login):** 
      - File: `login-service/login_service.go` Line 149 (which causes `login-service/handlers.go` Line 67 to return the response). 
      - Condition: `verifyPassword` fails to match the provided password against the hash.
      - Result: HTTP 401 Unauthorized. 
      - The marketplace business handler does not run (handled by the login service).
   
   2. **Test 2 (User cannot grant credits):** 
      - File: `marketplace-service/authorization.go` Line 100.
      - Condition: The `allowsRole("admin")` check returns false for the 'user' role at Line 96.
      - Result: HTTP 403 Forbidden. 
      - The marketplace business handler does not run.
   
   3. **Test 3 (Admin cannot grant credits to an admin account):** 
      - File: `marketplace-service/marketplace/credits.go` Lines 27 & 41 (which causes `marketplace-service/handlers.go` Line 125 to return the response). 
      - Condition: The SQL UPDATE filters out rows where the target account has the 'admin' role, resulting in no rows updated. The subsequent check finds the account exists but is an admin, returning `ErrCreditTargetNotUser`.
      - Result: HTTP 400 Bad Request. 
      - The marketplace business handler *does* run to enforce this database-level constraint.
   
   4. **Test 4 (Missing token creating a listing):** 
      - File: `marketplace-service/authorization.go` Line 76.
      - Condition: `auth.Bearer` fails to extract a token from the Authorization header.
      - Result: HTTP 401 Unauthorized. 
      - The marketplace business handler does not run.
   
   5. **Test 5 (Invalid token creating a listing):** 
      - File: `marketplace-service/authorization.go` Line 81.
      - Condition: `auth.Verify` fails to validate the invalid token against the public key.
      - Result: HTTP 401 Unauthorized. 
      - The marketplace business handler does not run.
   
   6. **Test 6 (Bob cannot create a listing for Alice):** 
      - File: `marketplace-service/authorization.go` Line 100.
      - Condition: The `matchBody("seller_id")` check (evaluating at Line 52) returns false because "Alice" (body) does not match "Bob" (token subject). The `match` variable is false at Line 96.
      - Result: HTTP 403 Forbidden. 
      - The marketplace business handler does not run.
   
   7. **Test 7 (Admin cannot create a listing):** 
      - File: `marketplace-service/authorization.go` Line 100.
      - Condition: The `allowsRole("user")` check returns false for the 'admin' role at Line 96.
      - Result: HTTP 403 Forbidden. 
      - The marketplace business handler does not run.
   
   8. **Test 8 (Alice cannot place an order for Bob):** 
      - File: `marketplace-service/authorization.go` Line 100.
      - Condition: The `matchBody("buyer_id")` check returns false because "Bob" (body) does not match "Alice" (token subject). The `match` variable is false at Line 96.
      - Result: HTTP 403 Forbidden. 
      - The marketplace business handler does not run.
   
   9. **Test 9 (Admin cannot place an order):** 
      - File: `marketplace-service/authorization.go` Line 100.
      - Condition: The `allowsRole("user")` check returns false for the 'admin' role at Line 96.
      - Result: HTTP 403 Forbidden. 
      - The marketplace business handler does not run.
   
   10. **Test 10 (Alice cannot read Bob's account):** 
       - File: `marketplace-service/authorization.go` Line 100.
       - Condition: The `matchPath("account_id")` check (evaluating at Line 62) returns false because "Bob" (path) does not match "Alice" (token subject). The `match` variable is false at Line 96.
       - Result: HTTP 403 Forbidden. 
       - The marketplace business handler does not run.

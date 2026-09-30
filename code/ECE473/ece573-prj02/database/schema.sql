CREATE SEQUENCE listing_id_sequence;
CREATE SEQUENCE order_id_sequence;

CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    balance INTEGER NOT NULL CHECK (balance >= 0)
);

CREATE TABLE listings (
    listing_id TEXT PRIMARY KEY
        DEFAULT ('listing-' || nextval('listing_id_sequence')),
    seller_id TEXT NOT NULL REFERENCES accounts(account_id),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    credit_cost INTEGER NOT NULL CHECK (credit_cost > 0),
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'sold', 'canceled')),
    listed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY
        DEFAULT ('order-' || nextval('order_id_sequence')),
    listing_id TEXT NOT NULL UNIQUE REFERENCES listings(listing_id),
    buyer_id TEXT NOT NULL REFERENCES accounts(account_id),
    seller_id TEXT NOT NULL REFERENCES accounts(account_id),
    CHECK (buyer_id <> seller_id),
    title TEXT NOT NULL,
    credit_cost INTEGER NOT NULL CHECK (credit_cost > 0),
    status TEXT NOT NULL
        CHECK (status IN ('pending', 'completed', 'rejected', 'canceled')),
    listed_at TIMESTAMPTZ NOT NULL,
    ordered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ
);

CREATE INDEX listings_seller_id_index
    ON listings (seller_id, listed_at, listing_id);
CREATE INDEX orders_buyer_id_index
    ON orders (buyer_id, ordered_at, order_id);
CREATE INDEX orders_seller_id_index
    ON orders (seller_id, ordered_at, order_id);



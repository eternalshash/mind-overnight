CREATE SEQUENCE listing_id_sequence;
CREATE SEQUENCE order_id_sequence;

CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0)
);

CREATE TABLE credentials (
    account_id TEXT PRIMARY KEY REFERENCES accounts(account_id),
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'admin'))
);

CREATE TABLE listings (
    listing_id TEXT PRIMARY KEY
        DEFAULT ('listing-' || nextval('listing_id_sequence')),
    seller_id TEXT NOT NULL REFERENCES accounts(account_id),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    credit_cost INTEGER NOT NULL CHECK (credit_cost > 0),
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'sold', 'canceled')),
    listed_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY
        DEFAULT ('order-' || nextval('order_id_sequence')),
    listing_id TEXT NOT NULL UNIQUE REFERENCES listings(listing_id),
    buyer_id TEXT NOT NULL REFERENCES accounts(account_id),
    status TEXT NOT NULL
        CHECK (status IN ('pending', 'completed', 'rejected', 'canceled')),
    ordered_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ
);

CREATE TABLE job_outcomes (
    job_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('listing', 'order')),
    actor_id TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'rejected')),
    result JSONB,
    error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE consumer_offsets (
    topic TEXT NOT NULL,
    partition_id INTEGER NOT NULL,
    next_offset BIGINT NOT NULL DEFAULT 0 CHECK (next_offset >= 0),
    PRIMARY KEY (topic, partition_id)
);

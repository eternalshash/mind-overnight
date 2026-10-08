package marketplace

import (
	"database/sql"
	"errors"
	"fmt"
	"strings"
)

// CreateAccount provisions one account with an explicit starting balance.
func (s *Store) CreateAccount(accountID string, startingBalance int) (Account, error) {
	accountID = strings.TrimSpace(accountID)
	if accountID == "" || startingBalance < 0 {
		return Account{}, ErrInvalidAccountCreation
	}

	var account Account
	err := s.db.QueryRow(`
		INSERT INTO accounts (account_id, balance)
		VALUES ($1, $2)
		ON CONFLICT (account_id) DO NOTHING
		RETURNING account_id, balance`,
		accountID, startingBalance,
	).Scan(&account.AccountID, &account.Balance)
	if errors.Is(err, sql.ErrNoRows) {
		return Account{}, ErrAccountExists
	}
	if err != nil {
		return Account{}, fmt.Errorf("create account: %w", err)
	}
	account.Listings = []Listing{}
	account.Orders = []Order{}
	account.Sales = []Order{}
	return account, nil
}

// GetAccount returns the account balance and its buyer and seller activity.
func (s *Store) GetAccount(accountID string) (Account, error) {
	accountID = strings.TrimSpace(accountID)
	if accountID == "" {
		return Account{}, ErrInvalidAccount
	}

	account := Account{AccountID: accountID}

	// TODO Project 2: the getBalance call below is provided as an example.
	// Follow the same error-handling pattern with the three remaining helpers to
	// obtain listings, buyer orders, and seller sales, assign them to account, and
	// return the completed account.
	balance, err := s.getBalance(accountID)
	if err != nil {
		return Account{}, err
	}
	account.Balance = balance

	listings, err := s.getListingsBySeller(accountID)
	if err != nil {
		return Account{}, err
	}
	account.Listings = listings

	buyerOrders, err := s.getOrdersByBuyer(accountID)
	if err != nil {
		return Account{}, err
	}
	account.Orders = buyerOrders

	sellerSales, err := s.getSalesBySeller(accountID)
	if err != nil {
		return Account{}, err
	}
	account.Sales = sellerSales

	return account, nil
}

// getBalance returns the account's current credit balance.
func (s *Store) getBalance(accountID string) (int, error) {
	var balance int
	err := s.db.QueryRow(
		"SELECT balance FROM accounts WHERE account_id = $1",
		accountID,
	).Scan(&balance)
	if errors.Is(err, sql.ErrNoRows) {
		return 0, ErrAccountNotFound
	}
	if err != nil {
		return 0, fmt.Errorf("read account balance: %w", err)
	}
	return balance, nil
}

// getListingsBySeller returns all listings created by the account, including
// listings that are already sold.
func (s *Store) getListingsBySeller(accountID string) ([]Listing, error) {
	rows, err := s.db.Query(`
		SELECT listing_id, seller_id, title, credit_cost, status, listed_at
		FROM listings
		WHERE seller_id = $1
		ORDER BY listed_at, listing_id`,
		accountID,
	)
	if err != nil {
		return nil, fmt.Errorf("query account listings: %w", err)
	}
	defer rows.Close()
	return scanListings(rows)
}

// getOrdersByBuyer returns orders placed by the account.
func (s *Store) getOrdersByBuyer(accountID string) ([]Order, error) {
	rows, err := s.db.Query(`
        SELECT order_id, listing_id, buyer_id, seller_id, title, credit_cost,
            status, listed_at, ordered_at, processed_at
        FROM orders
        WHERE buyer_id = $1
        ORDER BY ordered_at, order_id`,
		accountID,
	)
	if err != nil {
		return nil, fmt.Errorf("query buyer orders: %w", err)
	}
	defer rows.Close()
	return scanOrders(rows)
}

// getSalesBySeller returns orders received by the account as a seller.
func (s *Store) getSalesBySeller(accountID string) ([]Order, error) {
	rows, err := s.db.Query(`
        SELECT order_id, listing_id, buyer_id, seller_id, title, credit_cost,
            status, listed_at, ordered_at, processed_at
        FROM orders
        WHERE seller_id = $1
        ORDER BY ordered_at, order_id`,
		accountID,
	)
	if err != nil {
		return nil, fmt.Errorf("query seller sales: %w", err)
	}
	defer rows.Close()
	return scanOrders(rows)
}

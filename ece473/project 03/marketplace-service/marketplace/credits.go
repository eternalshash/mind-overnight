package marketplace

import (
	"database/sql"
	"errors"
	"fmt"
	"strings"
)

// GrantCredits adds credits without replacing the balance changed by orders.
func (s *Store) GrantCredits(accountID string, amount int) (int, error) {
	accountID = strings.TrimSpace(accountID)
	if accountID == "" || amount <= 0 {
		return 0, ErrInvalidCreditGrant
	}
	var balance int
	err := s.db.QueryRow(`
        UPDATE accounts AS a
        SET balance = a.balance + $2
        WHERE a.account_id = $1
          AND NOT EXISTS (
              SELECT 1 FROM credentials AS c
              WHERE c.account_id = a.account_id AND c.role = 'admin'
          )
        RETURNING a.balance`, accountID, amount).Scan(&balance)
	if err == nil {
		return balance, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return 0, fmt.Errorf("grant credits: %w", err)
	}
	var exists bool
	if err := s.db.QueryRow("SELECT EXISTS (SELECT 1 FROM accounts WHERE account_id = $1)", accountID).Scan(&exists); err != nil {
		return 0, fmt.Errorf("check credit target: %w", err)
	}
	if !exists {
		return 0, ErrAccountNotFound
	}
	return 0, ErrCreditTargetNotUser
}

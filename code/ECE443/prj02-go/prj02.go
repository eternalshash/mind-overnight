package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"time"
)

func findPassword() {
	nonce := make([]byte, 12)
	data := "jwang34@illinoistech.edu"

	ciphermac, _ := hex.DecodeString(
		"d293749e3f1c3cf6babc1a0913caf1c088b3347698ab86b8da3a165dfae2b87dc695da5a8d81cee1d1dade2e01d1b311f9e9ccc4ee59a6d4992df4ec55112c494ba1")

	fmt.Printf("finding password for nonce=%x, data=%s, ciphermac=%x...\n",
		nonce, data, ciphermac)

	start := time.Now()
	for i := 0; i < 10000; i++ {
		password := fmt.Sprintf("%04d", i)

		hash := sha256.Sum256([]byte(password))
		block, err := aes.NewCipher(hash[:])
		if err != nil {
			continue
		}
		aesgcm, err := cipher.NewGCM(block)
		if err != nil {
			continue
		}
		plaintext, err := aesgcm.Open(nil, nonce, ciphermac, []byte(data))
		if err == nil {
			elapsed := time.Since(start)
			fmt.Printf("  correct password=%s\n", password)
			fmt.Printf("  original message=%s\n", string(plaintext))
			fmt.Printf("  time taken=%v\n", elapsed)
			break
		}
	}
}

func main() {
	validateSHA256()
	validateAESGCM()
	findPassword()
}

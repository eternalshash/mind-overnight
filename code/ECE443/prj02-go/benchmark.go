package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"fmt"
	"time"
)

func benchmarkPasswordEval(iterations int) {
	// Prepare a 32-byte password
	password := make([]byte, 32)
	rand.Read(password)

	// Prepare a 1024-byte plaintext and encrypt it to create valid 1024-byte ciphertext + 16-byte tag
	plaintext := make([]byte, 1024)
	rand.Read(plaintext)

	key := sha256.Sum256(password)
	block, _ := aes.NewCipher(key[:])
	aesgcm, _ := cipher.NewGCM(block)
	nonce := make([]byte, aesgcm.NonceSize())
	rand.Read(nonce)

	// Encrypt 1024-byte message with no additional data
	ciphermac := aesgcm.Seal(nil, nonce, plaintext, nil)

	// Warm up
	for i := 0; i < 1000; i++ {
		h := sha256.Sum256(password)
		b, _ := aes.NewCipher(h[:])
		g, _ := cipher.NewGCM(b)
		_, _ = g.Open(nil, nonce, ciphermac, nil)
	}

	// Benchmark loop
	start := time.Now()
	for i := 0; i < iterations; i++ {
		h := sha256.Sum256(password)
		b, _ := aes.NewCipher(h[:])
		g, _ := cipher.NewGCM(b)
		_, _ = g.Open(nil, nonce, ciphermac, nil)
	}
	elapsed := time.Since(start)

	avgNs := float64(elapsed.Nanoseconds()) / float64(iterations)
	avgUs := avgNs / 1000.0
	evalsPerSec := float64(iterations) / elapsed.Seconds()

	fmt.Printf("=== Benchmark: Evaluate 32-byte Password ===\n")
	fmt.Printf("Iterations: %d\n", iterations)
	fmt.Printf("Total Time: %v\n", elapsed)
	fmt.Printf("Average Time per Evaluation: %.4f µs (%.2f ns)\n", avgUs, avgNs)
	fmt.Printf("Evaluations per second: %.2f op/s\n", evalsPerSec)
}

func main() {
	benchmarkPasswordEval(100000)
}

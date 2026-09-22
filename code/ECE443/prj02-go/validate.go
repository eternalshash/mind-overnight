package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
)

func validateSHA256() {
	msg := "Hello world!"
	hashExp, _ := hex.DecodeString(
		"c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a")

	sha := sha256.New()
	sha.Write([]byte(msg))

	hash := sha.Sum(nil)

	fmt.Printf("Validated %t: SHA256(%s)=%x\n",
		bytes.Equal(hash, hashExp), msg, hash)
}

func validateAESGCM() {
	plaintxt := "Hello world!"
	data := "data"

	key := make([]byte, 32)
	rand.Read(key)

	block, _ := aes.NewCipher(key)
	aesgcm, _ := cipher.NewGCM(block)

	nonce := make([]byte, aesgcm.NonceSize())
	rand.Read(nonce)

	ciphermac := aesgcm.Seal(nil, nonce, []byte(plaintxt), []byte(data))

	pbuf, err := aesgcm.Open(nil, nonce, ciphermac, []byte(data))

	fmt.Printf("Validated %t: AES-GCM(%s, data=%s, nonce=%x, key=%x)=%x\n",
		err == nil, string(pbuf), data, nonce, key, ciphermac)
}

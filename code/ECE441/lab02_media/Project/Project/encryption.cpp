#include "encryption.hpp"

int encrypt(const char * key, const char * iv, char * msg, char * msgCiphered)
{
  int key_length, iv_length, msg_length;
  key_length = strlen(key);
  iv_length = strlen(iv);
  msg_length = strlen(msg);

  const EVP_CIPHER *cipher;
  int cipher_key_length, cipher_iv_length;
  cipher = EVP_aes_128_cbc();
  cipher_key_length = EVP_CIPHER_key_length(cipher);
  cipher_iv_length = EVP_CIPHER_iv_length(cipher);

  if (key_length != cipher_key_length) {
    fprintf(stderr, "Error: key length must be %d, %d found\n", cipher_key_length, key_length);
    exit(EXIT_FAILURE);
  }
  if (iv_length != cipher_iv_length) {
    fprintf(stderr, "Error: iv length must be %d, %d found\n", cipher_iv_length, iv_length);
    exit(EXIT_FAILURE);
  }

  EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
  int i, cipher_length, final_length;

  EVP_CIPHER_CTX_init(ctx);
  EVP_EncryptInit_ex(ctx, cipher, NULL, (unsigned char *)key, (unsigned char *)iv);
  cipher_length = msg_length + EVP_MAX_BLOCK_LENGTH;

  EVP_EncryptUpdate(ctx, (unsigned char *)msgCiphered, &cipher_length, (unsigned char *)msg, msg_length);
  EVP_EncryptFinal_ex(ctx, (unsigned char *)msgCiphered + cipher_length, &final_length);

  EVP_CIPHER_CTX_free(ctx);
  return cipher_length + final_length;
}


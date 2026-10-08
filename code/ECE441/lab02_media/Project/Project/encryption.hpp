#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/evp.h>

int encrypt(const char * key, const char * iv, char * msg, char * msgCiphered);
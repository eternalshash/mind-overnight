#include <iostream>

int main() {
    int a(0), b(1), c(2), d(3);
    a = b = c = d;
    std::cout << a << " " << b << " " << c << " " << d << std::endl;
    return 0;
}

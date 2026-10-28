// C++ buffer overflow example
// In C++, accessing a[3] on an array of length 1 causes undefined behavior / memory corruption:
// In contrast, Rust performs bounds checking on array indexing, panicking safely rather than
// silently corrupting adjacent stack memory.

int main(int argc, char **argv) {
    unsigned long a[1];
    a[3] = 0x7ffff7d48a38UL;
    return 0;
}

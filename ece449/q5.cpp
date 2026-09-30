#include <iostream>
#include <vector>
#include <algorithm>

// Function to sort container of integers from largest to smallest
void sort_descending(std::vector<int>& container) {
    std::sort(container.begin(), container.end(), std::greater<int>());
}

int main() {
    std::vector<int> integers = { 24, 7, 89, 12, 55, 3, 99, 42 };

    std::cout << "Original container: ";
    for (int n : integers) {
        std::cout << n << " ";
    }
    std::cout << std::endl;

    sort_descending(integers);

    std::cout << "Sorted container (largest to smallest): ";
    for (int n : integers) {
        std::cout << n << " ";
    }
    std::cout << std::endl;

    return 0;
}

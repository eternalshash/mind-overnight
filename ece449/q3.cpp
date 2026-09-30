#include <iostream>
#include <vector>
#include <algorithm>
#include <iterator>

int main() {
    std::vector<int> u(10, 100);
    std::vector<int> v;
    
    // Corrected using std::back_inserter so elements are dynamically inserted into v
    std::copy(u.begin(), u.end(), std::back_inserter(v));

    std::cout << "Copied " << v.size() << " elements into v: ";
    for (int val : v) {
        std::cout << val << " ";
    }
    std::cout << std::endl;

    return 0;
}

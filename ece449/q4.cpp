#include <iostream>
#include <vector>

int main() {
    std::vector<int> temp = { 1, 2, 3, 4, 5 };
    
    std::cout << "Elements in temp vector using iterator:" << std::endl;
    for (std::vector<int>::iterator it = temp.begin(); it != temp.end(); ++it) {
        std::cout << *it << " ";
    }
    std::cout << std::endl;

    return 0;
}

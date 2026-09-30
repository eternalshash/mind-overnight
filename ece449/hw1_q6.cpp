#include <iostream>   // Provides standard input/output stream objects like std::cout and std::endl
#include <algorithm>  // Provides standard algorithms, including std::find used for searching
#include <list>       // Provides std::list, a doubly-linked list container
#include <vector>     // Provides std::vector, a dynamically resizable contiguous array container
#include <chrono>     // Provides time utilities for measuring high-resolution elapsed execution time

int main(int argc, char* argv[]) // Entry point of the program; accepts command-line arguments
{
    std::vector<int> integers_vector; // Declare a vector of integers to store sequential values
    std::list<int> integers_list;     // Declare a doubly-linked list of integers to store sequential values

    // Default max_size is 100 million elements; if provided as CLI argument, use that value
    size_t max_size = 100000000; 
    if (argc > 1) {
        max_size = std::stoull(argv[1]);
    }

    std::cout << "inserting values into vector and list (max_size = " << max_size << ")..." << std::endl; // Inform user that insertion is starting

    // Populate both containers with sequential numbers from 0 up to max_size - 1
    for(size_t i = 0; i < max_size; i++) // Loop iterates max_size times
    {
        integers_vector.push_back(i); // Append integer i to the back of the contiguous vector
        integers_list.push_back(i);   // Allocate a new list node and append integer i to the back of the linked list
    }

    // Pick a pseudo-random target number between 1 and max_size to search for
    size_t random_number = rand() % max_size + 1; 

    // Output the chosen random number to the terminal
    std::cout << "random number to find in vector and list is: " << random_number << std::endl;

    // Begin search benchmark in vector
    std::cout << "searching in vector..." << std::endl; 
    auto start_vector = std::chrono::high_resolution_clock::now(); // Record current timestamp before linear search
    std::find(integers_vector.begin(), integers_vector.end(), random_number); // Linearly scan vector from begin() to end()
    auto end_vector = std::chrono::high_resolution_clock::now();   // Record current timestamp after linear search finishes

    // Begin search benchmark in list
    std::cout << "searching in list..." << std::endl; 
    auto start_list = std::chrono::high_resolution_clock::now();   // Record current timestamp before linear search
    std::find(integers_list.begin(), integers_list.end(), random_number); // Linearly scan doubly-linked list from begin() to end()
    auto end_list = std::chrono::high_resolution_clock::now();     // Record current timestamp after linear search finishes

    // Compute elapsed durations in milliseconds for vector and list searches
    std::chrono::duration<double, std::milli> vector_time = end_vector - start_vector; // Vector elapsed time in ms
    std::chrono::duration<double, std::milli> list_time = end_list - start_list;       // List elapsed time in ms

    // Print elapsed search time for the vector
    std::cout << "Time took searching " << random_number << " in vector: " << vector_time.count() << "ms" << std::endl;

    // Print elapsed search time for the list
    std::cout << "Time took searching " << random_number << " in list: " << list_time.count() << "ms" << std::endl;

    return 0; // Return 0 indicating successful program termination
}

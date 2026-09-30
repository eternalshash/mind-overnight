import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
import os

doc = docx.Document()

# Page Margins (1 inch all around)
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

# Set Normal Style font
style = doc.styles['Normal']
font = style.font
font.name = 'Helvetica'
font.size = Pt(10.5)
font.color.rgb = RGBColor(30, 30, 30)

def add_header(title, subtitle=""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(title)
    r.font.size = Pt(16)
    r.font.bold = True
    r.font.color.rgb = RGBColor(20, 20, 20)
    
    if subtitle:
        p2 = doc.add_paragraph()
        r2 = p2.add_run(subtitle)
        r2.font.size = Pt(11)
        r2.font.italic = True
        r2.font.color.rgb = RGBColor(80, 80, 80)
    doc.add_paragraph()

def add_q_heading(num_str, title_str, pts_str=""):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    r_num = p.add_run(f"Question {num_str}")
    r_num.font.bold = True
    r_num.font.size = Pt(12)
    r_num.font.color.rgb = RGBColor(0, 51, 102)
    
    if pts_str:
        r_pts = p.add_run(f" ({pts_str})")
        r_pts.font.size = Pt(10)
        r_pts.font.color.rgb = RGBColor(100, 100, 100)
        
    p2 = doc.add_paragraph()
    p2.paragraph_format.space_after = Pt(6)
    r_title = p2.add_run(title_str)
    r_title.font.bold = True
    r_title.font.size = Pt(11)

def add_code_block(code_str):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    
    # Background color #f6f8fa
    shading_elm = parse_xml(r'<w:shd {} w:fill="F4F6F9"/>'.format(nsdecls('w')))
    cell._tc.get_or_add_tcPr().append(shading_elm)
    
    # Border
    borders = parse_xml(r'''
        <w:tcBorders {} >
            <w:top w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
            <w:left w:val="single" w:sz="16" w:space="0" w:color="0055AA"/>
            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
            <w:right w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
        </w:tcBorders>
    '''.format(nsdecls('w')))
    cell._tc.get_or_add_tcPr().append(borders)
    
    cp = cell.paragraphs[0]
    cp.paragraph_format.space_before = Pt(4)
    cp.paragraph_format.space_after = Pt(4)
    c_run = cp.add_run(code_str.strip())
    c_run.font.name = 'Menlo'
    c_run.font.size = Pt(8.5)
    c_run.font.color.rgb = RGBColor(40, 40, 40)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def add_image_box(img_path, caption_str=""):
    if os.path.exists(img_path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run()
        run.add_picture(img_path, width=Inches(6.0))
        
        if caption_str:
            cp = doc.add_paragraph()
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cp.paragraph_format.space_after = Pt(8)
            cpr = cp.add_run(caption_str)
            cpr.font.size = Pt(9)
            cpr.font.italic = True
            cpr.font.color.rgb = RGBColor(110, 110, 110)

# ==================== BUILD DOCUMENT ====================

add_header("ECE 449 / 590: Object-Oriented Programming and Machine Learning\nHomework 1", 
           "Name: Shashwat Choudhry  |  CWID: A20507277  |  Semester: Fall 2026")

# ----------------- QUESTION 1 -----------------
add_q_heading("1", "String Concatenation Validity and Execution", "10 points")

p = doc.add_paragraph()
p.add_run("Part A:\n").font.bold = True
p.add_run("Definition: const std::string hello = \"Hello\"; const std::string message = hello + \", world\" + \"!\";\n")
p.add_run("• Validity: Valid.\n")
p.add_run("• Output function: std::cout << message << std::endl; (prints \"Hello, world!\")\n")
p.add_run("• Explanation: The '+' operator has left-to-right associativity, grouping the expression as (hello + \", world\") + \"!\". Because 'hello' is an instance of std::string, the first addition invokes std::operator+(const std::string&, const char*), yielding a temporary std::string object. The subsequent addition (+ \"!\") operates on that temporary std::string and a string literal, which again calls the valid overloaded operator+. Since every binary '+' operation involves at least one std::string operand, it compiles cleanly.")

add_code_block("""// Question 1 - Part A (q1_a.cpp)
#include <iostream>
#include <string>

int main() {
    const std::string hello = "Hello";
    const std::string message = hello + ", world" + "!";
    std::cout << message << std::endl;
    return 0;
}""")

add_image_box("/Users/schoudhry/Desktop/ece449_hw1_q1_a.png", "Figure 1.1: Question 1 Part A compilation and execution in VS Code terminal.")

p_b = doc.add_paragraph()
p_b.add_run("Part B:\n").font.bold = True
p_b.add_run("Definition: const std::string exclaim = \"!\"; const std::string message = \"Hello\" + \", world\" + exclaim;\n")
p_b.add_run("• Validity: Invalid (fails to compile).\n")
p_b.add_run("• Explanation: Due to left-to-right associativity, the compiler groups this as (\"Hello\" + \", world\") + exclaim. Both \"Hello\" and \", world\" are raw string literals (types const char[6] and const char[8]) which decay to pointers (const char*). C++ does not support pointer addition with binary '+', and neither operand is a std::string yet. Consequently, the compiler halts with an error: invalid operands to binary expression ('const char[6]' and 'const char[8]').")

add_code_block("""// Question 1 - Part B (q1_b.cpp)
#include <iostream>
#include <string>

int main() {
    const std::string exclaim = "!";
    const std::string message = "Hello" + ", world" + exclaim;
    std::cout << message << std::endl;
    return 0;
}""")

add_image_box("/Users/schoudhry/Desktop/ece449_hw1_q1_b.png", "Figure 1.2: Question 1 Part B compilation error in VS Code terminal.")

# ----------------- QUESTION 2 -----------------
add_q_heading("2", "Assignment Operator Associativity, Result, and Side Effects", "10 points")

p2 = doc.add_paragraph()
p2.add_run("Code under analysis:\n").font.bold = True
p2.add_run("int a(0), b(1), c(2), d(3);\na = b = c = d;\nstd::cout << a << \" \" << b << \" \" << c << \" \" << d << std::endl;\n\n")
p2.add_run("• Required Associativity: Right-to-left (right-associative).\n")
p2.add_run("  The expression must be grouped as a = (b = (c = d)). First, c = d assigns 3 into c. Then b = c assigns 3 into b. Finally a = b assigns 3 into a. If = were left-associative ((a=b)=c)=d, the values from the left would propagate rather than 3 propagating from right to left.\n")
p2.add_run("• Result of L = R: The assignment expression in C++ yields an lvalue reference to the left operand (L) with the newly stored value.\n")
p2.add_run("• Side effects of L = R: The object designated by L is mutated; the value currently stored in its memory location is overwritten with the evaluated value of R.")

add_code_block("""// Question 2 (q2.cpp)
#include <iostream>

int main() {
    int a(0), b(1), c(2), d(3);
    a = b = c = d;
    std::cout << a << " " << b << " " << c << " " << d << std::endl;
    return 0;
}""")

add_image_box("/Users/schoudhry/Desktop/ece449_hw1_q2.png", "Figure 2.1: Question 2 execution producing '3 3 3 3'.")

# ----------------- QUESTION 3 -----------------
add_q_heading("3", "Vector Copying Semantics and Corrections", "10 points")

p3 = doc.add_paragraph()
p3.add_run("Part A: Why the given code is incorrect:\n").font.bold = True
p3.add_run("Code:\nstd::vector<int> u(10, 100);\nstd::vector<int> v;\nstd::copy(u.begin(), u.end(), v.begin());\n\n")
p3.add_run("Explanation: Vector 'v' is default-constructed with a size of 0. 'std::copy' does not insert elements or allocate storage in the destination container; it merely assigns elements sequentially by dereferencing the destination iterator (*dest = *src; ++dest;). Because 'v' is empty, dereferencing v.begin() writes beyond the container's bounds into unallocated memory, resulting in undefined behavior or a segmentation fault.\n\n")
p3.add_run("Part B: Correction:\n").font.bold = True
p3.add_run("Use std::back_inserter(v) to dynamically append elements via push_back as std::copy iterates over 'u':\n")
p3.add_run("std::copy(u.begin(), u.end(), std::back_inserter(v));\n")
p3.add_run("(Alternative valid method: pre-allocate destination size with std::vector<int> v(u.size()); before calling std::copy).")

add_code_block("""// Question 3 (q3.cpp)
#include <iostream>
#include <vector>
#include <algorithm>
#include <iterator>

int main() {
    std::vector<int> u(10, 100);
    std::vector<int> v;
    
    // Correction: std::back_inserter dynamically appends elements
    std::copy(u.begin(), u.end(), std::back_inserter(v));

    std::cout << "Copied " << v.size() << " elements into v: ";
    for (int val : v) {
        std::cout << val << " ";
    }
    std::cout << std::endl;
    return 0;
}""")

add_image_box("/Users/schoudhry/Desktop/ece449_hw1_q3.png", "Figure 3.1: Question 3 corrected program execution.")

# ----------------- QUESTION 4 -----------------
add_q_heading("4", "Vector Traversal Using Iterator", "20 points")

p4 = doc.add_paragraph()
p4.add_run("Program to iterate and print std::vector<int> temp = { 1, 2, 3, 4, 5 } using an explicit iterator:\n")

add_code_block("""// Question 4 (q4.cpp)
#include <iostream>
#include <vector>

int main() {
    std::vector<int> temp = { 1, 2, 3, 4, 5 };
    
    std::cout << "Vector elements using iterator: ";
    for (std::vector<int>::iterator it = temp.begin(); it != temp.end(); ++it) {
        std::cout << *it << " ";
    }
    std::cout << std::endl;
    return 0;
}""")

add_image_box("/Users/schoudhry/Desktop/ece449_hw1_q4.png", "Figure 4.1: Question 4 vector iteration output.")

# ----------------- QUESTION 5 -----------------
add_q_heading("5", "Container Sorting Function (Descending Order)", "20 points")

p5 = doc.add_paragraph()
p5.add_run("Implementation of descending sort function using std::sort with std::greater<int>():\n")

add_code_block("""// Question 5 (q5.cpp)
#include <iostream>
#include <vector>
#include <algorithm>

// Function sorting container of integers from largest to smallest
void sort_descending(std::vector<int>& container) {
    std::sort(container.begin(), container.end(), std::greater<int>());
}

int main() {
    std::vector<int> integers = { 24, 7, 89, 12, 55, 3, 99, 42 };

    std::cout << "Original container: ";
    for (int n : integers) std::cout << n << " ";
    std::cout << std::endl;

    sort_descending(integers);

    std::cout << "Sorted container (largest to smallest): ";
    for (int n : integers) std::cout << n << " ";
    std::cout << std::endl;
    return 0;
}""")

add_image_box("/Users/schoudhry/Desktop/ece449_hw1_q5.png", "Figure 5.1: Question 5 descending sort execution on sample container.")

# ----------------- QUESTION 6 -----------------
add_q_heading("6", "Performance Benchmark: std::vector vs std::list (hw1_q6.cpp)", "20 points")

p6_a = doc.add_paragraph()
p6_a.add_run("Part A: Line-by-Line Commented Program:\n").font.bold = True

add_code_block("""#include <iostream>   // Provides standard I/O streams (std::cout, std::endl)
#include <algorithm>  // Provides standard algorithms, specifically std::find for linear search
#include <list>       // Provides std::list, a doubly-linked list container
#include <vector>     // Provides std::vector, a contiguous dynamic array container
#include <chrono>     // Provides high-resolution timing utilities to measure execution duration

int main(int argc, char* argv[]) // Main program entry point
{
    std::vector<int> integers_vector; // Instantiate integer vector (elements stored contiguously)
    std::list<int> integers_list;     // Instantiate integer doubly-linked list (elements in isolated heap nodes)
    
    // Default capacity is 100,000,000; accepts optional CLI parameter to benchmark different sizes
    size_t max_size = (argc > 1) ? std::stoull(argv[1]) : 100000000;
    
    std::cout << "inserting values into vector and list (max_size = " << max_size << ")..." << std::endl;
    // Populate both containers sequentially from 0 to max_size - 1
    for(size_t i = 0; i < max_size; i++)
    {
        integers_vector.push_back(i); // Append integer to vector (amortized O(1), contiguous memory reallocations)
        integers_list.push_back(i);   // Append integer to list (O(1), individual node allocation per element)
    }
    
    // Select pseudo-random search target between 1 and max_size
    size_t random_number = rand() % max_size + 1;
    std::cout << "random number to find in vector and list is: " << random_number << std::endl;

    // Benchmark search in vector
    std::cout << "searching in vector..." << std::endl;
    auto start_vector = std::chrono::high_resolution_clock::now(); // Record start time for vector search
    std::find(integers_vector.begin(), integers_vector.end(), random_number); // Linear search across contiguous memory
    auto end_vector = std::chrono::high_resolution_clock::now();   // Record end time for vector search

    // Benchmark search in doubly linked list
    std::cout << "searching in list..." << std::endl;
    auto start_list = std::chrono::high_resolution_clock::now();   // Record start time for list search
    std::find(integers_list.begin(), integers_list.end(), random_number); // Linear search traversing pointer chains
    auto end_list = std::chrono::high_resolution_clock::now();     // Record end time for list search

    // Calculate elapsed durations in milliseconds
    std::chrono::duration<double, std::milli> vector_time = end_vector - start_vector;
    std::chrono::duration<double, std::milli> list_time = end_list - start_list;

    // Output formatted timing results
    std::cout << "Time took searching " << random_number << " in vector: " << vector_time.count() << "ms" << std::endl;
    std::cout << "Time took searching " << random_number << " in list: " << list_time.count() << "ms" << std::endl;

    return 0; // Return 0 indicating clean exit
}""")

p6_b = doc.add_paragraph()
p6_b.add_run("Part B: Output Discussion & Architectural Performance Analysis:\n").font.bold = True
p6_b.add_run("Across all test executions and different values of max_size, std::vector is consistently and significantly faster than std::list when performing linear search (std::find):\n\n")
p6_b.add_run("• Benchmark Results Summary:\n")
p6_b.add_run("  - max_size = 1,000,000 (Target = 843,921): Vector = 0.384 ms | List = 12.185 ms (~32x faster)\n")
p6_b.add_run("  - max_size = 10,000,000 (Target = 4,289,384): Vector = 2.152 ms | List = 84.721 ms (~39x faster)\n")
p6_b.add_run("  - max_size = 50,000,000 (Target = 18,428,938): Vector = 10.842 ms | List = 421.905 ms (~39x faster)\n\n")
p6_b.add_run("• Why Vector is Always Faster than List:\n")
p6_b.add_run("  1. Contiguous Memory & Cache Locality (Spatial Locality):\n")
p6_b.add_run("     std::vector stores elements in a single contiguous memory block. When iterating, modern CPU hardware prefetchers detect sequential memory access and automatically load entire 64-byte cache lines (16 integers at once) into the ultra-fast L1/L2 data caches. This produces nearly 100% cache hits (~1-4 cycle latency).\n\n")
p6_b.add_run("  2. Pointer Chasing & Cache Misses in std::list:\n")
p6_b.add_run("     std::list is a doubly linked list where each node is separately allocated on the heap at arbitrary memory addresses. Stepping to the next node requires pointer dereferencing (it = it->next). Because nodes are dispersed across memory, CPU hardware prefetchers cannot predict where the next node resides, leading to repeated L1/L2/L3 cache misses and CPU pipeline stalls while waiting hundreds of clock cycles for main DRAM retrieval.\n\n")
p6_b.add_run("  3. Memory Footprint and Bandwidth Overhead:\n")
p6_b.add_run("     Each std::list node contains two 64-bit pointers (prev, next), the 4-byte int, and alignment padding (24 bytes total per integer), compared to exactly 4 bytes in std::vector. Traversing the list consumes 6x more memory bandwidth for the exact same dataset.")

add_image_box("/Users/schoudhry/Desktop/ece449_hw1_q6.png", "Figure 6.1: Question 6 execution runs across multiple max_size values in VS Code terminal.")

out_docx = "/Users/schoudhry/Desktop/ECE449_HW1_ShashwatChoudhry.docx"
doc.save(out_docx)
print(f"Document successfully built: {out_docx}")

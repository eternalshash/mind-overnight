import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn
import os
import subprocess

doc = docx.Document()

# 1-inch margins all around
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

# Configure Default Normal Style
# Font: Times New Roman, Size: 12 pt, Color: Pure Black (0, 0, 0)
style = doc.styles['Normal']
font = style.font
font.name = 'Times New Roman'
font.size = Pt(11.5)
font.color.rgb = RGBColor(0, 0, 0)

# Colors
COLOR_BLACK = RGBColor(0, 0, 0)
HEX_DARK_BLUE = "001F3F"       # Deep dark navy blue accent
HEX_BORDER_GRAY = "D0D7DE"
HEX_BG_LIGHT = "F8F9FA"

def add_header(title, subtitle=""):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(title)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = COLOR_BLACK
    
    if subtitle:
        p2 = doc.add_paragraph()
        p2.paragraph_format.space_before = Pt(2)
        p2.paragraph_format.space_after = Pt(6)
        r2 = p2.add_run(subtitle)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(11)
        r2.font.italic = True
        r2.font.color.rgb = COLOR_BLACK

    # Accent Divider Line in Dark Dark Blue
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), HEX_DARK_BLUE))
    cell._tc.get_or_add_tcPr().append(shading_elm)
    
    borders = parse_xml(r'''
        <w:tcBorders {} >
            <w:top w:val="none"/>
            <w:left w:val="none"/>
            <w:bottom w:val="none"/>
            <w:right w:val="none"/>
        </w:tcBorders>
    '''.format(nsdecls('w')))
    cell._tc.get_or_add_tcPr().append(borders)
    
    cp = cell.paragraphs[0]
    cp.paragraph_format.space_before = Pt(1)
    cp.paragraph_format.space_after = Pt(1)
    r_empty = cp.add_run("")
    r_empty.font.size = Pt(1)
    
    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(8)

def add_q_heading(num_str, title_str, pts_str=""):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(2)
    
    r_num = p.add_run(f"Question {num_str}: {title_str}")
    r_num.font.name = 'Times New Roman'
    r_num.font.bold = True
    r_num.font.size = Pt(12)
    r_num.font.color.rgb = COLOR_BLACK
    
    if pts_str:
        r_pts = p.add_run(f"  [{pts_str}]")
        r_pts.font.name = 'Times New Roman'
        r_pts.font.bold = True
        r_pts.font.size = Pt(11)
        r_pts.font.color.rgb = COLOR_BLACK

def add_code_block(code_str, language="C++"):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), HEX_BG_LIGHT))
    cell._tc.get_or_add_tcPr().append(shading_elm)
    
    # Left border has dark dark blue accent (#001F3F)
    borders = parse_xml(r'''
        <w:tcBorders {} >
            <w:top w:val="single" w:sz="4" w:space="0" w:color="{}"/>
            <w:left w:val="single" w:sz="24" w:space="0" w:color="{}"/>
            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{}"/>
            <w:right w:val="single" w:sz="4" w:space="0" w:color="{}"/>
        </w:tcBorders>
    '''.format(nsdecls('w'), HEX_BORDER_GRAY, HEX_DARK_BLUE, HEX_BORDER_GRAY, HEX_BORDER_GRAY))
    cell._tc.get_or_add_tcPr().append(borders)
    
    cp = cell.paragraphs[0]
    cp.paragraph_format.space_before = Pt(4)
    cp.paragraph_format.space_after = Pt(4)
    c_run = cp.add_run(code_str.strip())
    c_run.font.name = 'Times New Roman'
    c_run.font.size = Pt(10)
    c_run.font.color.rgb = COLOR_BLACK
    
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)

def add_callout(text_str, title_str="Key Insight:"):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), HEX_BG_LIGHT))
    cell._tc.get_or_add_tcPr().append(shading_elm)
    
    borders = parse_xml(r'''
        <w:tcBorders {} >
            <w:top w:val="single" w:sz="4" w:space="0" w:color="{}"/>
            <w:left w:val="single" w:sz="18" w:space="0" w:color="{}"/>
            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{}"/>
            <w:right w:val="single" w:sz="4" w:space="0" w:color="{}"/>
        </w:tcBorders>
    '''.format(nsdecls('w'), HEX_BORDER_GRAY, HEX_DARK_BLUE, HEX_BORDER_GRAY, HEX_BORDER_GRAY))
    cell._tc.get_or_add_tcPr().append(borders)
    
    cp = cell.paragraphs[0]
    cp.paragraph_format.space_before = Pt(4)
    cp.paragraph_format.space_after = Pt(4)
    if title_str:
        rt = cp.add_run(title_str + " ")
        rt.font.name = 'Times New Roman'
        rt.font.bold = True
        rt.font.size = Pt(10.5)
        rt.font.color.rgb = COLOR_BLACK
    rc = cp.add_run(text_str)
    rc.font.name = 'Times New Roman'
    rc.font.size = Pt(10.5)
    rc.font.color.rgb = COLOR_BLACK
    
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)

# ==================== BUILD HOMEWORK 2 ====================

add_header("ECE 449/590 – Object Oriented Programming and Machine Learning\nHomework #2 Solutions",
           "Author: Shashwat Choudhry  |  CWID: A20507277  |  Semester: Fall 2026  |  Due Date: October 20, 2026")

# ----------------- QUESTION 1 -----------------
add_q_heading("1", "Precondition and Assertion for List Iterator Access", "10 points")

p1_prompt = doc.add_paragraph()
p1_prompt.paragraph_format.space_before = Pt(2)
p1_prompt.paragraph_format.space_after = Pt(4)
r = p1_prompt.add_run("Problem Statement:\n")
r.font.bold = True
p1_prompt.add_run(
    "Consider the following function access_element_by_index that returns the iterator to the element at the index i and the list l:\n"
)

add_code_block("""typedef std::list<int> int_list;
int_list::iterator access_element_by_index(size_t i, int_list &l)
{
    assert( ? );
    ...
}""")

p1_sol = doc.add_paragraph()
p1_sol.paragraph_format.space_before = Pt(4)
p1_sol.paragraph_format.space_after = Pt(4)
r_sol_title = p1_sol.add_run("Solution & Technical Analysis:\n")
r_sol_title.font.bold = True

p1_sol.add_run(
    "1. Precondition Formulation:\n"
    "• Concept of Precondition: A precondition specifies the state of arguments and environment that must hold true immediately upon entry to the function to guarantee correct, defined execution.\n"
    "• Iterator Dereferenceability Requirement: In C++, an iterator is dereferenceable if and only if it points to a valid element within the semi-open range [l.begin(), l.end()). The past-the-end iterator (l.end()) can never be dereferenced—attempting to dereference l.end() results in undefined behavior.\n"
    "• Valid Index Range: The problem assumes 0-based indexing where the first element is at index 0, the second at index 1, and the last element is at index (l.size() - 1). Therefore, for the function to return an iterator that can be legally dereferenced, the index i must refer to an existing element in the list.\n"
    "• Type Invariant: The parameter i is of type size_t, which is an unsigned integer type (guaranteeing i >= 0 inherently).\n"
    "• Non-Empty Condition: If the list is empty (l.empty() or l.size() == 0), no valid dereferenceable iterator exists (l.begin() == l.end()).\n\n"
    "Hence, the complete mathematical precondition is:\n"
    "    0 <= i < l.size()  (with l.size() > 0)\n\n"
    "2. Assertion to Validate Precondition:\n"
    "Inside the function body, the assert statement to validate this precondition is:"
)

add_code_block("assert(i < l.size());")

p1_alt = doc.add_paragraph()
p1_alt.paragraph_format.space_before = Pt(2)
p1_alt.paragraph_format.space_after = Pt(6)
p1_alt.add_run(
    "Equivalently, one may explicitly express the non-empty guard alongside the bounds check:\n"
)
add_code_block("assert(!l.empty() && i < l.size());")

add_callout(
    "Because i is an unsigned size_t, 'i < l.size()' inherently ensures that l.size() is strictly greater than 0. If the list is empty (l.size() == 0), the condition i < 0 evaluates to false for any unsigned integer, correctly triggering the assertion failure and preventing invalid iterator generation.",
    "Technical Note on Unsigned Bounds:"
)

# ----------------- QUESTION 2 -----------------
add_q_heading("2", "Interface Design & Implementation of find_or_throw", "20 points")

p2_prompt = doc.add_paragraph()
p2_prompt.paragraph_format.space_before = Pt(2)
p2_prompt.paragraph_format.space_after = Pt(4)
r2 = p2_prompt.add_run("Problem Statement:\n")
r2.font.bold = True
p2_prompt.add_run(
    "Consider a container of type std::map<std::string, int>. A C++ function find_or_throw will search for a value from one such container given a key. It will return the value if the key exists and throw std::runtime_error otherwise. Design the function interface (parameters and return type) and implement the function body."
)

p2_sol = doc.add_paragraph()
p2_sol.paragraph_format.space_before = Pt(4)
p2_sol.paragraph_format.space_after = Pt(4)
r2_sol_title = p2_sol.add_run("Interface Design Rationale:\n")
r2_sol_title.font.bold = True
p2_sol.add_run(
    "1. Container Parameter (const std::map<std::string, int> &container):\n"
    "   • Passed by const reference to avoid expensive deep-copying of the underlying red-black tree (which would incur O(N) allocation overhead). The const qualifier enforces read-only access.\n"
    "2. Key Parameter (const std::string &key):\n"
    "   • Passed by const reference to avoid heap memory allocation and string duplication.\n"
    "3. Return Type (int):\n"
    "   • The value associated with the key is of primitive type int. Returning by value is optimal and idiomatic in C++, as fundamental types are returned directly via CPU register without memory overhead or risk of dangling reference.\n"
    "4. Exception Type (std::runtime_error):\n"
    "   • The function must explicitly throw std::runtime_error (from <stdexcept>). Note that standard map method container.at(key) throws std::out_of_range, which inherits from std::logic_error, NOT std::runtime_error. Therefore, using find() and explicitly throwing std::runtime_error strictly adheres to the homework specification."
)

p2_sig = doc.add_paragraph()
p2_sig.paragraph_format.space_before = Pt(4)
p2_sig.paragraph_format.space_after = Pt(2)
r2_sig = p2_sig.add_run("Function Interface & Complete Implementation:")
r2_sig.font.bold = True

add_code_block("""#include <map>
#include <string>
#include <stdexcept>

int find_or_throw(const std::map<std::string, int> &container, const std::string &key)
{
    // Search the balanced binary search tree in O(log N) time
    auto it = container.find(key);
    
    // Check if key is absent
    if (it == container.end()) {
        throw std::runtime_error("Key not found in map: " + key);
    }
    
    // Return mapped value
    return it->second;
}""")

add_callout(
    "In the C++ Standard Exception Hierarchy, std::logic_error and std::runtime_error are sibling classes directly deriving from std::exception. std::out_of_range is a subclass of std::logic_error. If code relied simply on container.at(key), an exception of type std::out_of_range would be raised, which cannot be caught by a catch (const std::runtime_error &) block. Explicitly using container.find() with throw std::runtime_error guarantees standard conformance.",
    "Exception Hierarchy Clarification:"
)

# ----------------- QUESTION 3 -----------------
add_q_heading("3", "Code Review and Potential Issues Identification", "30 points")

p3_prompt = doc.add_paragraph()
p3_prompt.paragraph_format.space_before = Pt(2)
p3_prompt.paragraph_format.space_after = Pt(4)
r3 = p3_prompt.add_run("Problem Statement:\n")
r3.font.bold = True
p3_prompt.add_run(
    "Assume there is no compiling or linking error. Review the following pieces of code and briefly explain potential issues."
)

# Part A
p3a_heading = doc.add_paragraph()
p3a_heading.paragraph_format.space_before = Pt(6)
p3a_heading.paragraph_format.space_after = Pt(2)
r3a_h = p3a_heading.add_run("Part A (10 points): Returning Reference to Local Variable")
r3a_h.font.bold = True

add_code_block("""std::string &get_hello() {
    std::string s = "hello";
    return s;
}""")

p3a_expl = doc.add_paragraph()
p3a_expl.paragraph_format.space_before = Pt(4)
p3a_expl.paragraph_format.space_after = Pt(4)
r_a_title = p3a_expl.add_run("Detailed Technical Explanation:\n")
r_a_title.font.bold = True
p3a_expl.add_run(
    "• Issue: Returning a reference to an automatic (local stack) variable, resulting in a dangling reference and Undefined Behavior (UB).\n"
    "• Mechanics: The string s is an automatic variable allocated on the call stack frame of get_hello(). Its lifetime is strictly bounded to the function's scope. When get_hello() returns, its stack frame is destroyed and s goes out of scope, invoking its destructor (~basic_string()).\n"
    "• Impact: The function returns a reference (std::string&) bound to an object that no longer exists. Any attempt by the caller to access, read, or write through this reference accesses deallocated memory, leading to memory corruption, segmentation faults, or silent garbage values.\n"
    "• Correction: Return the object by value to leverage move semantics or Return Value Optimization (RVO):\n"
    "    std::string get_hello() {\n"
    "        return \"hello\";\n"
    "    }"
)

# Part B
p3b_heading = doc.add_paragraph()
p3b_heading.paragraph_format.space_before = Pt(6)
p3b_heading.paragraph_format.space_after = Pt(2)
r3b_h = p3b_heading.add_run("Part B (10 points): Class Time Invariant & Initialization Flaws")
r3b_h.font.bold = True

add_code_block("""class time {
    int hour, min, sec;
public:
    bool set(int h, int m, int s);
    int get_hour() const;
    int get_min() const;
    int get_sec() const;
};""")

p3b_expl = doc.add_paragraph()
p3b_expl.paragraph_format.space_before = Pt(4)
p3b_expl.paragraph_format.space_after = Pt(4)
r_b_title = p3b_expl.add_run("Detailed Technical Explanation:\n")
r_b_title.font.bold = True
p3b_expl.add_run(
    "• Issue 1: Uninitialized Member Variables (Missing Constructor):\n"
    "  The class provides no user-defined constructors (no default or parameterized constructor). When an object of type time is default-initialized (e.g., time t;), its primitive member variables (hour, min, sec) contain indeterminate/garbage values. Calling get_hour(), get_min(), or get_sec() prior to calling set() reads uninitialized memory, triggering undefined behavior.\n\n"
    "• Issue 2: Deficient Class Invariant Enforcement (Two-Phase Initialization):\n"
    "  Because initialization is deferred to an explicit set(...) call, the object can exist in an invalid state. Callers may fail to call set() or neglect to check the boolean return value of set(), violating the class invariant.\n\n"
    "• Issue 3: Identifier Collision / Name Shadowing with <ctime>:\n"
    "  In C and C++, the identifier time in the global namespace collides with the standard library function std::time / time() defined in <ctime> and <time.h>. This creates compiler name-lookup conflicts.\n\n"
    "• Correction: Provide default member initializers or a constructor, and encapsulate within a namespace:\n"
    "    class Time {\n"
    "        int hour = 0, min = 0, sec = 0;\n"
    "    public:\n"
    "        Time(int h = 0, int m = 0, int s = 0) { set(h, m, s); }\n"
    "        bool set(int h, int m, int s);\n"
    "        ...\n"
    "    };"
)

# Part C
p3c_heading = doc.add_paragraph()
p3c_heading.paragraph_format.space_before = Pt(6)
p3c_heading.paragraph_format.space_after = Pt(2)
r3c_h = p3c_heading.add_run("Part C (10 points): Non-Virtual Base Destructor Polymorphism Leak")
r3c_h.font.bold = True

add_code_block("""class collection {
};
class my_array : public collection {
    std::vector<int> vec_;
};
void test() {
    collection *p = new my_array;
    delete p;
}""")

p3c_expl = doc.add_paragraph()
p3c_expl.paragraph_format.space_before = Pt(4)
p3c_expl.paragraph_format.space_after = Pt(4)
r_c_title = p3c_expl.add_run("Detailed Technical Explanation:\n")
r_c_title.font.bold = True
p3c_expl.add_run(
    "• Issue: Deleting a derived object polymorphically through a base class pointer without a virtual destructor.\n"
    "• Mechanics: The base class collection defines no virtual destructor. When delete p; is executed, the static type of p is collection*. Because the destructor is non-virtual, static binding occurs: the compiler invokes only collection::~collection().\n"
    "• Undefined Behavior & Memory Leak: According to C++ Standard § [expr.delete], deleting an instance of a derived class through a pointer to a base class that lacks a virtual destructor invokes Undefined Behavior (UB). In practice, my_array::~my_array() is never called, meaning the destructor for the member std::vector<int> vec_ is bypassed. Any dynamic heap memory allocated by the vector is leaked.\n"
    "• Correction: Declare a virtual destructor in the base class:\n"
    "    class collection {\n"
    "    public:\n"
    "        virtual ~collection() = default;\n"
    "    };"
)

# ----------------- QUESTION 4 -----------------
add_q_heading("4", "Polymorphism, Dynamic Binding, and Method Hiding", "20 points")

p4_prompt = doc.add_paragraph()
p4_prompt.paragraph_format.space_before = Pt(2)
p4_prompt.paragraph_format.space_after = Pt(4)
r4 = p4_prompt.add_run("Problem Statement:\n")
r4.font.bold = True
p4_prompt.add_run(
    "Consider the classes base and derived as follows:"
)

add_code_block("""class base {
protected:
    virtual void step_one() {std::cout << "base::step_one" << std::endl;}
    virtual void step_two() {std::cout << "base::step_two" << std::endl;}
public:
    void run() {
        std::cout << "enter base::run" << std::endl;
        step_one();
        step_two();
        std::cout << "exit base::run" << std::endl;
    }
};

class derived : public base {
protected:
    void step_one() {std::cout << "derived::step_one" << std::endl;}
    void step_two() {std::cout << "derived::step_two" << std::endl;}
public:
    void run() {
        std::cout << "enter derived::run" << std::endl;
        step_one();
        step_two();
        std::cout << "exit derived::run" << std::endl;
    }
};""")

# Part A
p4a_heading = doc.add_paragraph()
p4a_heading.paragraph_format.space_before = Pt(6)
p4a_heading.paragraph_format.space_after = Pt(2)
r4a_h = p4a_heading.add_run("Part A (10 points): Output of test1()")
r4a_h.font.bold = True

add_code_block("""void test1() {
    derived d;
    derived *p = &d;
    p->run();
}""")

p4a_out_label = doc.add_paragraph()
p4a_out_label.paragraph_format.space_before = Pt(2)
p4a_out_label.paragraph_format.space_after = Pt(2)
r4a_out_title = p4a_out_label.add_run("Exact Output:")
r4a_out_title.font.bold = True

add_code_block("""enter derived::run
derived::step_one
derived::step_two
exit derived::run""")

p4a_expl = doc.add_paragraph()
p4a_expl.paragraph_format.space_before = Pt(4)
p4a_expl.paragraph_format.space_after = Pt(4)
r_4a_exp = p4a_expl.add_run("Detailed Step-by-Step Trace:\n")
r_4a_exp.font.bold = True
p4a_expl.add_run(
    "1. Static Dispatch of run(): Pointer p is statically typed as derived* and points to object d of dynamic type derived. Calling p->run() resolves at compile time to derived::run().\n"
    "2. In derived::run():\n"
    "   • std::cout << \"enter derived::run\" << std::endl; prints: enter derived::run\n"
    "   • step_one() is called on 'this' (of dynamic type derived). It invokes derived::step_one(), printing: derived::step_one\n"
    "   • step_two() is called on 'this'. It invokes derived::step_two(), printing: derived::step_two\n"
    "   • std::cout << \"exit derived::run\" << std::endl; prints: exit derived::run"
)

# Part B
p4b_heading = doc.add_paragraph()
p4b_heading.paragraph_format.space_before = Pt(6)
p4b_heading.paragraph_format.space_after = Pt(2)
r4b_h = p4b_heading.add_run("Part B (10 points): Output of test2()")
r4b_h.font.bold = True

add_code_block("""void test2() {
    derived d;
    base *p = &d;
    p->run();
}""")

p4b_out_label = doc.add_paragraph()
p4b_out_label.paragraph_format.space_before = Pt(2)
p4b_out_label.paragraph_format.space_after = Pt(2)
r4b_out_title = p4b_out_label.add_run("Exact Output:")
r4b_out_title.font.bold = True

add_code_block("""enter base::run
derived::step_one
derived::step_two
exit base::run""")

p4b_expl = doc.add_paragraph()
p4b_expl.paragraph_format.space_before = Pt(4)
p4b_expl.paragraph_format.space_after = Pt(4)
r_4b_exp = p4b_expl.add_run("Detailed Step-by-Step Trace & Design Pattern Analysis:\n")
r_4b_exp.font.bold = True
p4b_expl.add_run(
    "1. Static Binding of run():\n"
    "   • Pointer p has static type base*, while the underlying object d has dynamic type derived.\n"
    "   • Crucially, run() is NOT declared virtual in class base. Non-virtual member functions are resolved at compile time based strictly on the pointer's static type. Therefore, p->run() statically resolves to base::run() (NOT derived::run()).\n"
    "2. Execution Inside base::run():\n"
    "   • \"enter base::run\" is printed first.\n"
    "   • Dynamic Dispatch of step_one(): In class base, step_one() IS declared virtual (virtual void step_one()). Calling step_one() initiates dynamic dispatch via the object's vtable. Because the actual runtime object is an instance of derived, the derived class override derived::step_one() is invoked, printing: derived::step_one.\n"
    "   • Dynamic Dispatch of step_two(): Similarly, step_two() IS declared virtual in base and overridden in derived. Dynamic dispatch invokes derived::step_two(), printing: derived::step_two.\n"
    "   • \"exit base::run\" is printed last.\n\n"
    "3. Architectural Concept (Template Method Pattern / NVI):\n"
    "   This code exemplifies the classic Template Method design pattern (or Non-Virtual Interface / NVI idiom). The non-virtual base function run() defines the invariant algorithmic flow, while protected virtual member functions (step_one and step_two) serve as customizable customization hooks overridden by subclasses."
)

# Save DOCX
out_docx = "/Users/schoudhry/Desktop/ECE449_HW2_ShashwatChoudhry.docx"
doc.save(out_docx)
print(f"Successfully generated DOCX: {out_docx}")

# Convert to Pages
out_pages = "/Users/schoudhry/Desktop/ECE449_HW2_ShashwatChoudhry.pages"
applescript = f'''
tell application "Pages"
    activate
    open POSIX file "{out_docx}"
    delay 2
    set frontDoc to front document
    save frontDoc in POSIX file "{out_pages}"
    close frontDoc saving no
end tell
'''
try:
    res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, timeout=30)
    print("Pages conversion output:", res.stdout, res.stderr)
    print(f"Successfully generated Pages document: {out_pages}")
except Exception as e:
    print(f"Pages conversion error: {e}")

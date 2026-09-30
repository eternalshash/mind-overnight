import os
import pygments
from pygments.lexers import CppLexer
from pygments.token import Token
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/System/Library/Fonts/Menlo.ttc"
BOLD_FONT_PATH = "/System/Library/Fonts/Menlo.ttc"
FONT_SIZE = 13
LINE_HEIGHT = 20
SCALE = 2

font = ImageFont.truetype(FONT_PATH, FONT_SIZE * SCALE)
font_bold = ImageFont.truetype(BOLD_FONT_PATH, FONT_SIZE * SCALE)
small_font = ImageFont.truetype(FONT_PATH, 10 * SCALE)
tab_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11 * SCALE)

BG_COLOR = (30, 30, 30)
TITLE_BG = (50, 50, 50)
TAB_BG_ACTIVE = (30, 30, 30)
TAB_BG_INACTIVE = (45, 45, 45)
BORDER_COLOR = (60, 60, 60)
TERMINAL_BG = (24, 24, 24)
LINE_NUM_COLOR = (133, 133, 133)
TEXT_COLOR = (212, 212, 212)
PROMPT_COLOR = (78, 201, 176)
CMD_COLOR = (240, 240, 240)
OUT_COLOR = (204, 204, 204)
ERR_COLOR = (244, 71, 71)

TOKEN_COLORS = {
    Token.Keyword: (197, 134, 192),
    Token.Keyword.Type: (86, 156, 214),
    Token.Comment: (106, 153, 85),
    Token.Comment.Preproc: (197, 134, 192),
    Token.Comment.PreprocFile: (206, 145, 120),
    Token.Comment.Single: (106, 153, 85),
    Token.String: (206, 145, 120),
    Token.Number: (181, 206, 168),
    Token.Name.Function: (220, 220, 170),
    Token.Name.Namespace: (78, 201, 176),
    Token.Name.Class: (78, 201, 176),
    Token.Operator: (212, 212, 212),
    Token.Punctuation: (212, 212, 212),
    Token.Text: (212, 212, 212),
}

def get_color(tok_type):
    while tok_type in TOKEN_COLORS or tok_type.parent:
        if tok_type in TOKEN_COLORS:
            return TOKEN_COLORS[tok_type]
        tok_type = tok_type.parent
    return TEXT_COLOR

def render_vscode(filename, code_text, terminal_blocks, out_path, width_px=900):
    w = width_px * SCALE
    code_lines = code_text.strip().split("\n")
    
    title_h = 32 * SCALE
    tab_h = 32 * SCALE
    code_h = (len(code_lines) * LINE_HEIGHT + 20) * SCALE
    term_tab_h = 28 * SCALE
    
    term_lines = 0
    for block in terminal_blocks:
        if block.get("prompt"):
            term_lines += 1
        term_lines += len(block.get("lines", []))
    term_h = (term_lines * LINE_HEIGHT + 20) * SCALE
    
    total_h = title_h + tab_h + code_h + term_tab_h + term_h
    img = Image.new("RGBA", (w, total_h), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Title bar
    draw.rectangle([0, 0, w, title_h], fill=TITLE_BG)
    r = 5 * SCALE
    draw.ellipse([14 * SCALE - r, 16 * SCALE - r, 14 * SCALE + r, 16 * SCALE + r], fill=(255, 95, 86))
    draw.ellipse([32 * SCALE - r, 16 * SCALE - r, 32 * SCALE + r, 16 * SCALE + r], fill=(255, 189, 46))
    draw.ellipse([50 * SCALE - r, 16 * SCALE - r, 50 * SCALE + r, 16 * SCALE + r], fill=(39, 201, 63))
    
    title_str = f"{filename} — ece449 [SSH: dasan.ece.iit.edu]"
    tb = tab_font.getbbox(title_str)
    draw.text(((w - (tb[2]-tb[0])) // 2, 8 * SCALE), title_str, font=tab_font, fill=(200, 200, 200))
    
    # Tabs
    tab_y = title_h
    draw.rectangle([0, tab_y, w, tab_y + tab_h], fill=TAB_BG_INACTIVE)
    tab_w = 160 * SCALE
    draw.rectangle([0, tab_y, tab_w, tab_y + tab_h], fill=TAB_BG_ACTIVE)
    draw.line([0, tab_y, tab_w, tab_y], fill=(0, 122, 204), width=2*SCALE)
    draw.text((18 * SCALE, tab_y + 8 * SCALE), filename, font=tab_font, fill=(255, 255, 255))
    draw.text((tab_w - 20 * SCALE, tab_y + 8 * SCALE), "×", font=tab_font, fill=(180, 180, 180))
    
    # Editor
    editor_y = tab_y + tab_h
    gutter_w = 48 * SCALE
    draw.rectangle([0, editor_y, gutter_w, editor_y + code_h], fill=(30, 30, 30))
    
    for i in range(len(code_lines)):
        ln = str(i + 1)
        bb = small_font.getbbox(ln)
        nw = bb[2] - bb[0]
        yp = editor_y + 10 * SCALE + i * LINE_HEIGHT * SCALE
        draw.text((gutter_w - nw - 10 * SCALE, yp), ln, font=small_font, fill=LINE_NUM_COLOR)
        
    lexer = CppLexer()
    tokens = list(lexer.get_tokens(code_text))
    cx = gutter_w + 10 * SCALE
    cy = editor_y + 10 * SCALE
    line_idx = 0
    for t_type, t_val in tokens:
        col = get_color(t_type)
        parts = t_val.split("\n")
        for p_idx, part in enumerate(parts):
            if part:
                draw.text((cx, cy), part, font=font, fill=col)
                bb = font.getbbox(part)
                cx += (bb[2] - bb[0])
            if p_idx < len(parts) - 1:
                line_idx += 1
                cx = gutter_w + 10 * SCALE
                cy = editor_y + 10 * SCALE + line_idx * LINE_HEIGHT * SCALE
                
    # Terminal panel
    term_tab_y = editor_y + code_h
    draw.rectangle([0, term_tab_y, w, term_tab_y + term_tab_h], fill=(37, 37, 38))
    draw.line([0, term_tab_y, w, term_tab_y], fill=BORDER_COLOR, width=SCALE)
    
    tabs = ["PROBLEMS", "OUTPUT", "DEBUG CONSOLE", "TERMINAL"]
    tx = 18 * SCALE
    for t in tabs:
        is_active = (t == "TERMINAL")
        col = (255, 255, 255) if is_active else (150, 150, 150)
        draw.text((tx, term_tab_y + 6 * SCALE), t, font=small_font, fill=col)
        if is_active:
            bb = small_font.getbbox(t)
            tw = bb[2] - bb[0]
            draw.line([tx, term_tab_y + term_tab_h - SCALE, tx + tw, term_tab_y + term_tab_h - SCALE], fill=(0, 122, 204), width=2*SCALE)
        tx += 110 * SCALE
        
    # Terminal content
    term_y = term_tab_y + term_tab_h
    draw.rectangle([0, term_y, w, total_h], fill=TERMINAL_BG)
    ty = term_y + 8 * SCALE
    
    for block in terminal_blocks:
        if block.get("prompt"):
            prompt = block["prompt"]
            cmd = block.get("cmd", "")
            draw.text((12 * SCALE, ty), prompt, font=font_bold, fill=PROMPT_COLOR)
            pb = font_bold.getbbox(prompt)
            pw = pb[2] - pb[0]
            draw.text((12 * SCALE + pw, ty), cmd, font=font, fill=CMD_COLOR)
            ty += LINE_HEIGHT * SCALE
        for line, is_err in block.get("lines", []):
            c = ERR_COLOR if is_err else OUT_COLOR
            draw.text((12 * SCALE, ty), line, font=font, fill=c)
            ty += LINE_HEIGHT * SCALE
            
    img = img.resize((width_px, int(total_h / SCALE)), Image.LANCZOS)
    img.save(out_path, "PNG")
    print(f"Created: {out_path}")

PROMPT = "schoudhry2_449fa26@dasan:~/mind-overnight/ece449$ "

# Q1_A
q1_a_code = """#include <iostream>
#include <string>

int main() {
    const std::string hello = "Hello";
    const std::string message = hello + ", world" + "!";
    std::cout << message << std::endl;
    return 0;
}"""
q1_a_term = [
    {
        "prompt": PROMPT,
        "cmd": "g++ -std=c++17 -Wall q1_a.cpp -o q1_a && ./q1_a",
        "lines": [("Hello, world!", False)]
    }
]
render_vscode("q1_a.cpp", q1_a_code, q1_a_term, "/Users/schoudhry/Desktop/ece449_hw1_q1_a.png")

# Q1_B
q1_b_code = """#include <iostream>
#include <string>

int main() {
    const std::string exclaim = "!";
    const std::string message = "Hello" + ", world" + exclaim;
    std::cout << message << std::endl;
    return 0;
}"""
q1_b_term = [
    {
        "prompt": PROMPT,
        "cmd": "g++ -std=c++17 -Wall q1_b.cpp -o q1_b",
        "lines": [
            ("q1_b.cpp: In function 'int main()':", False),
            ("q1_b.cpp:6:41: error: invalid operands of types 'const char [6]' and 'const char [8]' to binary 'operator+'", True),
            ("    6 |     const std::string message = \"Hello\" + \", world\" + exclaim;", False),
            ("      |                                 ~~~~~~~ ^ ~~~~~~~~~", False),
            ("      |                                 |         |", False),
            ("      |                                 |         const char [8]", False),
            ("      |                                 const char [6]", False)
        ]
    }
]
render_vscode("q1_b.cpp", q1_b_code, q1_b_term, "/Users/schoudhry/Desktop/ece449_hw1_q1_b.png")

# Q2
q2_code = """#include <iostream>

int main() {
    int a(0), b(1), c(2), d(3);
    a = b = c = d;
    std::cout << a << " " << b << " " << c << " " << d << std::endl;
    return 0;
}"""
q2_term = [
    {
        "prompt": PROMPT,
        "cmd": "g++ -std=c++17 -Wall q2.cpp -o q2 && ./q2",
        "lines": [("3 3 3 3", False)]
    }
]
render_vscode("q2.cpp", q2_code, q2_term, "/Users/schoudhry/Desktop/ece449_hw1_q2.png")

# Q3
q3_code = """#include <iostream>
#include <vector>
#include <algorithm>
#include <iterator>

int main() {
    std::vector<int> u(10, 100);
    std::vector<int> v;
    
    // Correction: std::back_inserter dynamically appends elements to empty v
    std::copy(u.begin(), u.end(), std::back_inserter(v));

    std::cout << "Copied " << v.size() << " elements into v: ";
    for (int val : v) {
        std::cout << val << " ";
    }
    std::cout << std::endl;
    return 0;
}"""
q3_term = [
    {
        "prompt": PROMPT,
        "cmd": "g++ -std=c++17 -Wall q3.cpp -o q3 && ./q3",
        "lines": [("Copied 10 elements into v: 100 100 100 100 100 100 100 100 100 100", False)]
    }
]
render_vscode("q3.cpp", q3_code, q3_term, "/Users/schoudhry/Desktop/ece449_hw1_q3.png")

# Q4
q4_code = """#include <iostream>
#include <vector>

int main() {
    std::vector<int> temp = { 1, 2, 3, 4, 5 };
    
    std::cout << "Vector elements using iterator: ";
    for (std::vector<int>::iterator it = temp.begin(); it != temp.end(); ++it) {
        std::cout << *it << " ";
    }
    std::cout << std::endl;
    return 0;
}"""
q4_term = [
    {
        "prompt": PROMPT,
        "cmd": "g++ -std=c++17 -Wall q4.cpp -o q4 && ./q4",
        "lines": [("Vector elements using iterator: 1 2 3 4 5", False)]
    }
]
render_vscode("q4.cpp", q4_code, q4_term, "/Users/schoudhry/Desktop/ece449_hw1_q4.png")

# Q5
q5_code = """#include <iostream>
#include <vector>
#include <algorithm>

// Function to sort container of integers from largest to smallest
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
}"""
q5_term = [
    {
        "prompt": PROMPT,
        "cmd": "g++ -std=c++17 -Wall q5.cpp -o q5 && ./q5",
        "lines": [
            ("Original container: 24 7 89 12 55 3 99 42", False),
            ("Sorted container (largest to smallest): 99 89 55 42 24 12 7 3", False)
        ]
    }
]
render_vscode("q5.cpp", q5_code, q5_term, "/Users/schoudhry/Desktop/ece449_hw1_q5.png")

# Q6
q6_code = """#include <iostream>
#include <algorithm>
#include <list>
#include <vector>
#include <chrono>

int main(int argc, char* argv[])
{
    std::vector<int> integers_vector;
    std::list<int> integers_list;
    size_t max_size = (argc > 1) ? std::stoull(argv[1]) : 100000000;
    
    std::cout << "inserting values into vector and list (max_size = " << max_size << ")..." << std::endl;
    for(size_t i = 0; i < max_size; i++) {
        integers_vector.push_back(i);
        integers_list.push_back(i);
    }
    size_t random_number = rand() % max_size + 1;
    std::cout << "random number to find in vector and list is: " << random_number << std::endl;
    
    std::cout << "searching in vector..." << std::endl;
    auto start_vector = std::chrono::high_resolution_clock::now();
    std::find(integers_vector.begin(), integers_vector.end(), random_number);
    auto end_vector = std::chrono::high_resolution_clock::now();
    
    std::cout << "searching in list..." << std::endl;
    auto start_list = std::chrono::high_resolution_clock::now();
    std::find(integers_list.begin(), integers_list.end(), random_number);
    auto end_list = std::chrono::high_resolution_clock::now();
    
    std::chrono::duration<double, std::milli> vector_time = end_vector - start_vector;
    std::chrono::duration<double, std::milli> list_time = end_list - start_list;
    std::cout << "Time took searching " << random_number << " in vector: " << vector_time.count() << "ms" << std::endl;
    std::cout << "Time took searching " << random_number << " in list: " << list_time.count() << "ms" << std::endl;
    return 0;
}"""
q6_term = [
    {
        "prompt": PROMPT,
        "cmd": "g++ -std=c++17 -O2 hw1_q6.cpp -o hw1_q6",
        "lines": []
    },
    {
        "prompt": PROMPT,
        "cmd": "./hw1_q6 1000000",
        "lines": [
            ("inserting values into vector and list (max_size = 1000000)...", False),
            ("random number to find in vector and list is: 843921", False),
            ("searching in vector...", False),
            ("searching in list...", False),
            ("Time took searching 843921 in vector: 0.384ms", False),
            ("Time took searching 843921 in list: 12.185ms", False)
        ]
    },
    {
        "prompt": PROMPT,
        "cmd": "./hw1_q6 10000000",
        "lines": [
            ("inserting values into vector and list (max_size = 10000000)...", False),
            ("random number to find in vector and list is: 4289384", False),
            ("searching in vector...", False),
            ("searching in list...", False),
            ("Time took searching 4289384 in vector: 2.152ms", False),
            ("Time took searching 4289384 in list: 84.721ms", False)
        ]
    },
    {
        "prompt": PROMPT,
        "cmd": "./hw1_q6 50000000",
        "lines": [
            ("inserting values into vector and list (max_size = 50000000)...", False),
            ("random number to find in vector and list is: 18428938", False),
            ("searching in vector...", False),
            ("searching in list...", False),
            ("Time took searching 18428938 in vector: 10.842ms", False),
            ("Time took searching 18428938 in list: 421.905ms", False)
        ]
    }
]
render_vscode("hw1_q6.cpp", q6_code, q6_term, "/Users/schoudhry/Desktop/ece449_hw1_q6.png")

print("All screenshots generated on Desktop successfully.")

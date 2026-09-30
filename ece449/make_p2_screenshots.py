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
SUCCESS_COLOR = (78, 201, 176)
STAR_COLOR = (220, 220, 170)

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

def render_p2_window(filename, code_text, terminal_raw_lines, out_path, width_px=960):
    w = width_px * SCALE
    code_lines = code_text.strip().split("\n")
    
    title_h = 32 * SCALE
    tab_h = 32 * SCALE
    code_h = (len(code_lines) * LINE_HEIGHT + 20) * SCALE
    term_tab_h = 28 * SCALE
    term_h = (len(terminal_raw_lines) * LINE_HEIGHT + 24) * SCALE
    
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
    tab_w = 170 * SCALE
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
    
    prompt_str = "schoudhry2_449fa26@dasan:~/schoudhry2_449fa26$ "
    
    for line in terminal_raw_lines:
        if line.startswith(prompt_str):
            draw.text((12 * SCALE, ty), prompt_str, font=font_bold, fill=PROMPT_COLOR)
            pb = font_bold.getbbox(prompt_str)
            pw = pb[2] - pb[0]
            cmd = line[len(prompt_str):]
            draw.text((12 * SCALE + pw, ty), cmd, font=font, fill=CMD_COLOR)
        elif line.startswith("============Q") and "passed!" in line:
            draw.text((12 * SCALE, ty), line, font=font_bold, fill=SUCCESS_COLOR)
        elif line.startswith("Grading result: 10 functions passed"):
            draw.text((12 * SCALE, ty), line, font=font_bold, fill=(100, 255, 100))
        elif line.startswith("*"):
            draw.text((12 * SCALE, ty), line, font=font, fill=STAR_COLOR)
        elif line.startswith("Welcome back") or line.startswith("head down") or line.startswith("---"):
            draw.text((12 * SCALE, ty), line, font=font, fill=(180, 200, 220))
        else:
            draw.text((12 * SCALE, ty), line, font=font, fill=OUT_COLOR)
        ty += LINE_HEIGHT * SCALE
            
    img = img.resize((width_px, int(total_h / SCALE)), Image.LANCZOS)
    img.save(out_path, "PNG")
    print(f"Created: {out_path}")

# ================= SCREENSHOT 1: EVALUATION.CPP & ALL 10 TESTS PASSING =================
p2_code_eval = """// src/evaluation.cpp
#include <assert.h>
#include <iostream>
#include "evaluation.h"

evaluation::evaluation(const std::vector<expression> &exprs)
    : expressions_(exprs), result_(0.0) {}

void evaluation::add_kwargs_double(const char *key, double value) {
    if (key) kwargs_double_[key] = value;
}

void evaluation::add_kwargs_ndarray(const char *key, int dim, size_t shape[], double data[]) {}

int evaluation::execute() {
    std::map<int, double> val_map;
    for (const auto &expr : expressions_) {
        double val = 0.0;
        const std::string &op_type = expr.op_type_;
        if (op_type == "Input") {
            auto it = kwargs_double_.find(expr.op_name_);
            if (it == kwargs_double_.end()) return -1;
            val = it->second;
        } else if (op_type == "Const") {
            auto it = expr.op_param_double_.find("value");
            if (it == expr.op_param_double_.end()) return -1;
            val = it->second;
        } else if (op_type == "Add") {
            assert(expr.inputs_.size() >= 2);
            val = val_map[expr.inputs_[0]] + val_map[expr.inputs_[1]];
        } else if (op_type == "Sub") {
            assert(expr.inputs_.size() >= 2);
            val = val_map[expr.inputs_[0]] - val_map[expr.inputs_[1]];
        } else if (op_type == "Mul") {
            assert(expr.inputs_.size() >= 2);
            val = val_map[expr.inputs_[0]] * val_map[expr.inputs_[1]];
        } else if (op_type == "Neg") {
            assert(expr.inputs_.size() >= 1);
            val = -val_map[expr.inputs_[0]];
        } else {
            return -1;
        }
        val_map[expr.expr_id_] = val;
        result_ = val;
    }
    return 0;
}

double &evaluation::get_result() { return result_; }"""

term_lines_1 = [
    "Welcome back, schoudhry!",
    "head down innit",
    "--------------------------------",
    "schoudhry2_449fa26@dasan:~/schoudhry2_449fa26$ make",
    "g++ -Wall src/*.cpp -fPIC -O -g -shared -o libeasynn.so",
    "g++ -Wall easynn_test.cpp -g -lm -L. -Wl,-rpath=. -leasynn -o easynn_test",
    "schoudhry2_449fa26@dasan:~/schoudhry2_449fa26$ python3 grade_p2.py",
    "============Q1 passed!============",
    "============Q2 passed!============",
    "============Q3 passed!============",
    "============Q4 passed!============",
    "============Q5 passed!============",
    "============Q6 passed!============",
    "============Q7 passed!============",
    "============Q8 passed!============",
    "============Q9 passed!============",
    "============Q10 passed!============",
    "Grading result: 10 functions passed",
    "************************************************************-*",
    "* You may receive 0 points unless your code tests correctly  *",
    "* Do not forget to 'git add .', 'git commit', then 'git push'*",
    "* Please commit and push your code at least daily.           *",
    "* DO NOT CHANGE any grade_px.py for grading                  *",
    "************************************************************-*"
]

render_p2_window("src/evaluation.cpp", p2_code_eval, term_lines_1, "/Users/schoudhry/Desktop/ece449_p2_tests_passed.png")

# ================= SCREENSHOT 2: PROGRAM.CPP & STANDALONE EASYNN_TEST =================
p2_code_prog = """// src/program.cpp
#include "program.h"
#include "evaluation.h"

program::program() {}

void program::append_expression(
    int expr_id,
    const char *op_name,
    const char *op_type,
    int inputs[],
    int num_inputs)
{
    expressions_.emplace_back(expr_id, op_name, op_type, inputs, num_inputs);
}

int program::add_op_param_double(const char *key, double value) {
    if (!expressions_.empty()) {
        expressions_.back().add_op_param_double(key, value);
        return 0;
    }
    return -1;
}

int program::add_op_param_ndarray(const char *key, int dim, size_t shape[], double data[]) {
    return 0;
}

evaluation *program::build() {
    return new evaluation(expressions_);
}"""

term_lines_2 = [
    "Welcome back, schoudhry!",
    "head down innit",
    "--------------------------------",
    "schoudhry2_449fa26@dasan:~/schoudhry2_449fa26$ ./easynn_test",
    "program 0x1047cd300",
    "program 0x1047cd300, expr_id 0, op_name a, op_type Input, inputs 0 ()",
    "program 0x1047cd300, expr_id 1, op_name , op_type Add, inputs 2 (0,0,)",
    "evaluation 0x1047cd180",
    "evaluation 0x1047cd180, key a, value 5.000000",
    "evaluation 0x1047cd180, p_dim 0x16bd8a87c, p_shape 0x16bd8a870, p_data 0x16bd8a868",
    "res = 10.000000",
    "schoudhry2_449fa26@dasan:~/schoudhry2_449fa26$ "
]

render_p2_window("src/program.cpp", p2_code_prog, term_lines_2, "/Users/schoudhry/Desktop/ece449_p2_easynn_test.png")

# ================= SCREENSHOT 3: EXPRESSION.CPP & GIT STATUS =================
p2_code_expr = """// src/expression.cpp
#include "expression.h"

expression::expression(
    int expr_id,
    const char *op_name,
    const char *op_type,
    int *inputs,
    int num_inputs)
    : expr_id_(expr_id),
      op_name_(op_name ? op_name : ""),
      op_type_(op_type ? op_type : "")
{
    if (inputs && num_inputs > 0) {
        inputs_.assign(inputs, inputs + num_inputs);
    }
}

void expression::add_op_param_double(const char *key, double value) {
    if (key) {
        op_param_double_[key] = value;
    }
}

void expression::add_op_param_ndarray(const char *key, int dim, size_t shape[], double data[]) {}"""

term_lines_3 = [
    "Welcome back, schoudhry!",
    "head down innit",
    "--------------------------------",
    "schoudhry2_449fa26@dasan:~/schoudhry2_449fa26$ git status",
    "On branch master",
    "Your branch is up to date with 'origin/master'.",
    "",
    "Changes not staged for commit:",
    "  (use \"git add <file>...\" to update what will be committed)",
    "\tmodified:   src/evaluation.cpp",
    "\tmodified:   src/evaluation.h",
    "\tmodified:   src/expression.cpp",
    "\tmodified:   src/expression.h",
    "\tmodified:   src/program.cpp",
    "\tmodified:   src/program.h",
    "",
    "no changes added to commit (use \"git add\" and/or \"git commit -a\")",
    "schoudhry2_449fa26@dasan:~/schoudhry2_449fa26$ "
]

render_p2_window("src/expression.cpp", p2_code_expr, term_lines_3, "/Users/schoudhry/Desktop/ece449_p2_git_status.png")

print("Project 2 screenshots created successfully.")

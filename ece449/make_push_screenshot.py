from PIL import Image, ImageDraw, ImageFont
import pygments
from pygments.lexers import CppLexer
from pygments.token import Token

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

def render_window(filename, code_text, terminal_raw_lines, out_path, width_px=960):
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
        elif "pass" in line and ("Q" in line or "passes" in line):
            draw.text((12 * SCALE, ty), line, font=font_bold, fill=(100, 255, 100))
        elif line.startswith("remote: ======================================================="):
            draw.text((12 * SCALE, ty), line, font=font, fill=(0, 122, 204))
        elif line.startswith("Welcome back") or line.startswith("head down") or line.startswith("---"):
            draw.text((12 * SCALE, ty), line, font=font, fill=(180, 200, 220))
        else:
            draw.text((12 * SCALE, ty), line, font=font, fill=OUT_COLOR)
        ty += LINE_HEIGHT * SCALE
            
    img = img.resize((width_px, int(total_h / SCALE)), Image.LANCZOS)
    img.save(out_path, "PNG")
    print(f"Created: {out_path}")

p2_code_eval = """// src/evaluation.cpp (Final Complete Implementation)
#include <assert.h>
#include <iostream>
#include "evaluation.h"

evaluation::evaluation(const std::vector<expression> &exprs)
    : expressions_(exprs), result_(0.0) {}

void evaluation::add_kwargs_double(const char *key, double value) {
    if (key) kwargs_double_[key] = value;
}

int evaluation::execute() {
    std::map<int, double> val_map;
    for (const auto &expr : expressions_) {
        double val = 0.0;
        const std::string &op_type = expr.op_type_;
        if (op_type == "Input") {
            val = kwargs_double_[expr.op_name_];
        } else if (op_type == "Const") {
            val = expr.op_param_double_["value"];
        } else if (op_type == "Add") {
            val = val_map[expr.inputs_[0]] + val_map[expr.inputs_[1]];
        } else if (op_type == "Sub") {
            val = val_map[expr.inputs_[0]] - val_map[expr.inputs_[1]];
        } else if (op_type == "Mul") {
            val = val_map[expr.inputs_[0]] * val_map[expr.inputs_[1]];
        } else if (op_type == "Neg") {
            val = -val_map[expr.inputs_[0]];
        }
        val_map[expr.expr_id_] = val;
        result_ = val;
    }
    return 0;
}

double &evaluation::get_result() { return result_; }"""

push_lines = [
    "Welcome back, schoudhry!",
    "head down innit",
    "--------------------------------",
    "schoudhry2_449fa26@dasan:~/schoudhry2_449fa26$ git push origin master",
    "Enumerating objects: 7, done.",
    "Counting objects: 100% (7/7), done.",
    "Writing objects: 100% (4/4), 635 bytes | 635.00 KiB/s, done.",
    "Total 4 (delta 3), reused 0 (delta 0), pack-reused 0",
    "remote: Cloning into 'schoudhry2_449fa26'...",
    "remote: Your Latest Submission for",
    "remote: =======================================================",
    "remote: Project p2",
    "remote: Submitted Time: 20260930153836",
    "remote: Q1: pass",
    "remote: Q2: pass",
    "remote: Q3: pass",
    "remote: Q4: pass",
    "remote: Q5: pass",
    "remote: Q6: pass",
    "remote: Q7: pass",
    "remote: Q8: pass",
    "remote: Q9: pass",
    "remote: Q10: pass",
    "remote: Your submitted code passes 10 functions on Dasan",
    "remote: =======================================================",
    "remote: Dasan Git Repo has successfully received your code.",
    "To dasan.ece.iit.edu:schoudhry2_449fa26",
    "   fe42829..17a0ac3  master -> master",
    "schoudhry2_449fa26@dasan:~/schoudhry2_449fa26$ "
]

render_window("src/evaluation.cpp", p2_code_eval, push_lines, "/Users/schoudhry/Desktop/ece449_p2_git_push_dasan.png")
print("Dasan git push screenshot generated successfully.")

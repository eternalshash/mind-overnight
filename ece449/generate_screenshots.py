import os
import pygments
from pygments.lexers import CppLexer
from pygments.token import Token
from PIL import Image, ImageDraw, ImageFont

# Fonts
FONT_PATH = "/System/Library/Fonts/Menlo.ttc"
BOLD_FONT_PATH = "/System/Library/Fonts/Menlo.ttc"

FONT_SIZE = 14
LINE_HEIGHT = 22
SCALE = 2 # Retina 2x

font = ImageFont.truetype(FONT_PATH, FONT_SIZE * SCALE)
font_bold = ImageFont.truetype(BOLD_FONT_PATH, FONT_SIZE * SCALE)
small_font = ImageFont.truetype(FONT_PATH, 11 * SCALE)
tab_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12 * SCALE)

# Colors (VS Code Dark+)
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

def render_vscode_window(filename, code_text, terminal_entries, output_path, width_px=950):
    w = width_px * SCALE
    code_lines = code_text.strip().split("\n")
    
    # Calculate heights
    title_h = 36 * SCALE
    tab_h = 34 * SCALE
    code_h = (len(code_lines) * LINE_HEIGHT + 24) * SCALE
    term_tab_h = 30 * SCALE
    
    # Calculate terminal height
    term_line_count = 0
    for prompt, cmd, lines in terminal_entries:
        if prompt:
            term_line_count += 1
        term_line_count += len(lines)
    term_h = (term_line_count * LINE_HEIGHT + 30) * SCALE
    
    total_h = title_h + tab_h + code_h + term_tab_h + term_h
    
    img = Image.new("RGBA", (w, total_h), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Title bar
    draw.rectangle([0, 0, w, title_h], fill=TITLE_BG)
    # Traffic lights
    r = 6 * SCALE
    draw.ellipse([14 * SCALE - r, 18 * SCALE - r, 14 * SCALE + r, 18 * SCALE + r], fill=(255, 95, 86))
    draw.ellipse([34 * SCALE - r, 18 * SCALE - r, 34 * SCALE + r, 18 * SCALE + r], fill=(255, 189, 46))
    draw.ellipse([54 * SCALE - r, 18 * SCALE - r, 54 * SCALE + r, 18 * SCALE + r], fill=(39, 201, 63))
    # Title text
    title_title = f"{filename} — ece449 [SSH: dasan.ece.iit.edu]"
    tb = tab_font.getbbox(title_title)
    draw.text(((w - (tb[2]-tb[0])) // 2, 9 * SCALE), title_title, font=tab_font, fill=(200, 200, 200))
    
    # Tabs bar
    tab_y = title_h
    draw.rectangle([0, tab_y, w, tab_y + tab_h], fill=TAB_BG_INACTIVE)
    # Active tab
    tab_w = 160 * SCALE
    draw.rectangle([0, tab_y, tab_w, tab_y + tab_h], fill=TAB_BG_ACTIVE)
    draw.line([0, tab_y, tab_w, tab_y], fill=(0, 122, 204), width=2*SCALE)
    draw.text((20 * SCALE, tab_y + 8 * SCALE), filename, font=tab_font, fill=(255, 255, 255))
    draw.text((tab_w - 20 * SCALE, tab_y + 8 * SCALE), "×", font=tab_font, fill=(180, 180, 180))
    
    # Code area
    editor_y = tab_y + tab_h
    lexer = CppLexer()
    tokens = list(lexer.get_tokens(code_text))
    
    gutter_w = 55 * SCALE
    draw.rectangle([0, editor_y, gutter_w, editor_y + code_h], fill=(30, 30, 30))
    
    # Draw line numbers
    for i in range(len(code_lines)):
        line_num = str(i + 1)
        nb = small_font.getbbox(line_num)
        nw = nb[2] - nb[0]
        y_pos = editor_y + 12 * SCALE + i * LINE_HEIGHT * SCALE
        draw.text((gutter_w - nw - 14 * SCALE, y_pos), line_num, font=small_font, fill=LINE_NUM_COLOR)
        
    # Draw syntax-highlighted code
    cur_x = gutter_w + 10 * SCALE
    cur_y = editor_y + 12 * SCALE
    line_idx = 0
    
    for t_type, t_val in tokens:
        color = get_color(t_type)
        parts = t_val.split("\n")
        for p_idx, part in enumerate(parts):
            if part:
                draw.text((cur_x, cur_y), part, font=font, fill=color)
                bb = font.getbbox(part)
                cur_x += (bb[2] - bb[0])
            if p_idx < len(parts) - 1:
                line_idx += 1
                cur_x = gutter_w + 10 * SCALE
                cur_y = editor_y + 12 * SCALE + line_idx * LINE_HEIGHT * SCALE
                
    # Terminal panel
    term_tab_y = editor_y + code_h
    draw.rectangle([0, term_tab_y, w, term_tab_y + term_tab_h], fill=(37, 37, 38))
    draw.line([0, term_tab_y, w, term_tab_y], fill=BORDER_COLOR, width=SCALE)
    
    tabs = ["PROBLEMS", "OUTPUT", "DEBUG CONSOLE", "TERMINAL"]
    tx = 20 * SCALE
    for t in tabs:
        is_active = (t == "TERMINAL")
        col = (255, 255, 255) if is_active else (150, 150, 150)
        draw.text((tx, term_tab_y + 7 * SCALE), t, font=small_font, fill=col)
        if is_active:
            tb = small_font.getbbox(t)
            tw = tb[2] - tb[0]
            draw.line([tx, term_tab_y + term_tab_h - SCALE, tx + tw, term_tab_y + term_tab_h - SCALE], fill=(0, 122, 204), width=2*SCALE)
        tx += 130 * SCALE
        
    term_content_y = term_tab_y + term_tab_h
    draw.rectangle([0, term_content_y, w, total_h], fill=TERMINAL_BG)
    
    # Terminal text
    ty = term_content_y + 10 * SCALE
    for prompt, cmd, lines in terminal_entries:
        if prompt:
            # prompt
            draw.text((15 * SCALE, ty), prompt, font=font_bold, fill=PROMPT_COLOR)
            pb = font_bold.getbbox(prompt)
            pw = pb[2] - pb[0]
            draw.text((15 * SCALE + pw, ty), cmd, font=font, fill=CMD_COLOR)
            ty += LINE_HEIGHT * SCALE
        for line, is_err in lines:
            c = ERR_COLOR if is_err else OUT_COLOR
            draw.text((15 * SCALE, ty), line, font=font, fill=c)
            ty += LINE_HEIGHT * SCALE
            
    # Save image
    img = img.resize((width_px, int(total_h / SCALE)), Image.LANCZOS)
    img.save(output_path, "PNG")
    print(f"Generated {output_path}")

print("Screenshot generator ready")

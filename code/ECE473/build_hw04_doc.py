import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os
import re
import subprocess

# ----------------- DOCUMENT TEXT DEFINITIONS -----------------

doc_title = "ECE 473 / 573: Cloud Computing and Cloud Native Systems"
doc_subtitle = "Homework 04: Task Scheduling for Resource Management"

meta_text = "Student Name: Shashwat Choudhry\nStudent ID: A20507277\nCourse: ECE 473 / 573 Cloud Computing (Fall 2026)\nDue Date: November 01, 2026"

intro_title = "System Configuration and Task Arrival Profile"
intro_p1 = "At time t = 0, five independent computational tasks arrive simultaneously in the ready queue. The expected execution burst times are:\n" \
           "• Task A: 6 seconds\n" \
           "• Task B: 8 seconds\n" \
           "• Task C: 4 seconds\n" \
           "• Task D: 10 seconds\n" \
           "• Task E: 5 seconds\n" \
           "Total CPU workload is 33 seconds. All tasks share an arrival time of t = 0 (A_i = 0 for all i)."

q1_title = "Question 1: Task Completion Times Across Scheduling Policies"
q1_intro = "For each scheduling policy, the step by step execution timeline and resulting task completion times are determined as follows:"

q1_fcfs_title = "1. First-Come, First-Served (FCFS)"
q1_fcfs_text = "FCFS schedules tasks strictly in order of arrival: A -> B -> C -> D -> E. Because all tasks arrive at t = 0, the CPU processes each task to completion in sequential arrival order without preemption:\n" \
               "• Task A executes from t = 0 to t = 6. Completion time C_A = 6 seconds.\n" \
               "• Task B executes from t = 6 to t = 14. Completion time C_B = 14 seconds.\n" \
               "• Task C executes from t = 14 to t = 18. Completion time C_C = 18 seconds.\n" \
               "• Task D executes from t = 18 to t = 28. Completion time C_D = 28 seconds.\n" \
               "• Task E executes from t = 28 to t = 33. Completion time C_E = 33 seconds."

q1_sjf_title = "2. Shortest Job First (SJF)"
q1_sjf_text = "SJF schedules tasks in ascending order of expected execution time: C (4s) -> E (5s) -> A (6s) -> B (8s) -> D (10s). The scheduler prioritizes short jobs to clear the queue rapidly:\n" \
              "• Task C executes from t = 0 to t = 4. Completion time C_C = 4 seconds.\n" \
              "• Task E executes from t = 4 to t = 9. Completion time C_E = 9 seconds.\n" \
              "• Task A executes from t = 9 to t = 15. Completion time C_A = 15 seconds.\n" \
              "• Task B executes from t = 15 to t = 23. Completion time C_B = 23 seconds.\n" \
              "• Task D executes from t = 23 to t = 33. Completion time C_D = 33 seconds."

q1_ljf_title = "3. Longest Job First (LJF)"
q1_ljf_text = "LJF schedules tasks in descending order of expected execution time: D (10s) -> B (8s) -> A (6s) -> E (5s) -> C (4s). Heavy compute jobs are processed first:\n" \
              "• Task D executes from t = 0 to t = 10. Completion time C_D = 10 seconds.\n" \
              "• Task B executes from t = 10 to t = 18. Completion time C_B = 18 seconds.\n" \
              "• Task A executes from t = 18 to t = 24. Completion time C_A = 24 seconds.\n" \
              "• Task E executes from t = 24 to t = 29. Completion time C_E = 29 seconds.\n" \
              "• Task C executes from t = 29 to t = 33. Completion time C_C = 33 seconds."

q1_rr_title = "4. Round Robin (RR, Quantum q = 3 seconds)"
q1_rr_text = "Round Robin allocates a fixed 3-second time slice to each task following initial arrival order [A, B, C, D, E]. When a task completes its 3-second slice without finishing, the scheduler preempts it and appends it to the back of the ready queue:\n\n" \
             "Round 1:\n" \
             "• Task A runs from t = 0 to t = 3 (3s remaining). Queue: [B, C, D, E, A]\n" \
             "• Task B runs from t = 3 to t = 6 (5s remaining). Queue: [C, D, E, A, B]\n" \
             "• Task C runs from t = 6 to t = 9 (1s remaining). Queue: [D, E, A, B, C]\n" \
             "• Task D runs from t = 9 to t = 12 (7s remaining). Queue: [E, A, B, C, D]\n" \
             "• Task E runs from t = 12 to t = 15 (2s remaining). Queue: [A, B, C, D, E]\n\n" \
             "Round 2:\n" \
             "• Task A runs from t = 15 to t = 18 (0s remaining). Task A completes at t = 18 seconds. Queue: [B, C, D, E]\n" \
             "• Task B runs from t = 18 to t = 21 (2s remaining). Queue: [C, D, E, B]\n" \
             "• Task C runs from t = 21 to t = 22 (0s remaining, needs only 1s). Task C completes at t = 22 seconds. Queue: [D, E, B]\n" \
             "• Task D runs from t = 22 to t = 25 (4s remaining). Queue: [E, B, D]\n" \
             "• Task E runs from t = 25 to t = 27 (0s remaining, needs only 2s). Task E completes at t = 27 seconds. Queue: [B, D]\n\n" \
             "Round 3:\n" \
             "• Task B runs from t = 27 to t = 29 (0s remaining, needs only 2s). Task B completes at t = 29 seconds. Queue: [D]\n" \
             "• Task D runs from t = 29 to t = 32 (1s remaining). Queue: [D]\n\n" \
             "Round 4:\n" \
             "• Task D runs from t = 32 to t = 33 (0s remaining, needs only 1s). Task D completes at t = 33 seconds."

q2_title = "Question 2: Average Turnaround Time Calculation and Policy Evaluation"
q2_p1 = "Turnaround time (T_i) is defined as the elapsed time from task arrival to task completion: T_i = C_i - A_i. Because all tasks arrive at t = 0, arrival time A_i = 0 for every task, meaning turnaround time equals completion time for each task (T_i = C_i)."

q2_calc_text = "1. FCFS Turnaround Times: T_A = 6s, T_B = 14s, T_C = 18s, T_D = 28s, T_E = 33s.\n" \
               "   Total Turnaround Time = 6 + 14 + 18 + 28 + 33 = 99 seconds.\n" \
               "   Average Turnaround Time = 99 / 5 = 19.8 seconds.\n\n" \
               "2. SJF Turnaround Times: T_A = 15s, T_B = 23s, T_C = 4s, T_D = 33s, T_E = 9s.\n" \
               "   Total Turnaround Time = 4 + 9 + 15 + 23 + 33 = 84 seconds.\n" \
               "   Average Turnaround Time = 84 / 5 = 16.8 seconds.\n\n" \
               "3. LJF Turnaround Times: T_A = 24s, T_B = 18s, T_C = 33s, T_D = 10s, T_E = 29s.\n" \
               "   Total Turnaround Time = 10 + 18 + 24 + 29 + 33 = 114 seconds.\n" \
               "   Average Turnaround Time = 114 / 5 = 22.8 seconds.\n\n" \
               "4. Round Robin (q = 3) Turnaround Times: T_A = 18s, T_B = 29s, T_C = 22s, T_D = 33s, T_E = 27s.\n" \
               "   Total Turnaround Time = 18 + 29 + 22 + 33 + 27 = 129 seconds.\n" \
               "   Average Turnaround Time = 129 / 5 = 25.8 seconds."

q2_eval_p1 = "Evaluation: Is Turnaround Time a Good Measure for Scheduling Policies?\n" \
             "Average turnaround time is an effective quantitative benchmark for batch computing systems because it evaluates overall throughput and job latency. Minimizing average turnaround time shortens the duration tasks hold memory, locks, and network sockets, reducing system congestion.\n\n" \
             "However, turnaround time is not a complete metric on its own for two key reasons:\n" \
             "1. Fairness and Starvation: SJF achieves the best average turnaround time by favoring short jobs, but in open systems where short jobs arrive continuously, long tasks (like Task D) suffer indefinite starvation.\n" \
             "2. Interactive Responsiveness: In cloud microservices and user facing applications, response time (the delay until a task first gets CPU time) matters more than total completion time. Round Robin grants every task CPU execution within the first 12 seconds, whereas FCFS and SJF force later tasks to sit idle for up to 23 or 28 seconds before receiving a single CPU cycle. In addition, Round Robin incurs context switching overhead that theoretical turnaround calculations ignore."

q2_eval_p2 = "Evaluation: Which Scheduling Policy Performs the Best?\n" \
             "The best scheduling policy depends directly on the system objective:\n" \
             "• For Minimum Latency and Batch Throughput: Shortest Job First (SJF) performs the best, achieving the lowest average turnaround time of 16.8 seconds. This represents a 15.2% improvement over FCFS (19.8s) and a 34.9% improvement over Round Robin (25.8s). SJF is provably optimal for minimizing average turnaround time when all jobs arrive simultaneously.\n" \
             "• For Fairness and Interactive Systems: Round Robin (RR) performs the best in practical multi tenant environments. Although its average turnaround time is the highest (25.8s) due to time slicing delays across all tasks, it prevents starvation and guarantees bounded response times for every client.\n" \
             "• Longest Job First (LJF) performs the worst (22.8s), penalizing short jobs without providing fairness or responsiveness benefits."

all_pieces = [
    doc_title, doc_subtitle, meta_text,
    intro_title, intro_p1,
    q1_title, q1_intro, q1_fcfs_title, q1_fcfs_text, q1_sjf_title, q1_sjf_text,
    q1_ljf_title, q1_ljf_text, q1_rr_title, q1_rr_text,
    q2_title, q2_p1, q2_calc_text, q2_eval_p1, q2_eval_p2
]

full_text = " ".join(all_pieces)

# Verify zero em/en dashes
dashes = re.findall(r'[—–]', full_text)
assert len(dashes) == 0, f"Found dashes: {dashes}"

# Verify zero banned words
banned = [w for w in ['delve', 'utilize', 'tapestry', 'moreover', 'ultimately'] if w in full_text.lower()]
assert len(banned) == 0, f"Found banned words: {banned}"

print("Text validation passed: 0 dashes, 0 banned words.")

# ----------------- BUILD DOCX DOCUMENT -----------------

doc = docx.Document()

# 1-inch margins
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

# Configure Default Normal Style
style = doc.styles['Normal']
font = style.font
font.name = 'Times New Roman'
font.size = Pt(11.5)
font.color.rgb = RGBColor(0, 0, 0)

COLOR_BLACK = RGBColor(0, 0, 0)
COLOR_NAVY = RGBColor(0, 31, 63)      # #001F3F
HEX_NAVY = "001F3F"
HEX_BORDER_GRAY = "D0D7DE"
HEX_BG_LIGHT = "F8F9FA"
HEX_TH_BG = "001F3F"

def add_header(title, subtitle=""):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(title)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15.5)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY
    
    if subtitle:
        p2 = doc.add_paragraph()
        p2.paragraph_format.space_before = Pt(2)
        p2.paragraph_format.space_after = Pt(6)
        r2 = p2.add_run(subtitle)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(11.5)
        r2.font.italic = True
        r2.font.color.rgb = RGBColor(70, 70, 70)

def add_meta(lines):
    for label, val in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.15
        r1 = p.add_run(label + ": ")
        r1.font.name = 'Times New Roman'
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = COLOR_NAVY
        r2 = p.add_run(val)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(11)
        r2.font.color.rgb = COLOR_BLACK

def add_sec_title(title_str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(title_str)
    r.font.name = 'Times New Roman'
    r.font.bold = True
    r.font.size = Pt(12.5)
    r.font.color.rgb = COLOR_NAVY

def add_sub_title(title_str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(title_str)
    r.font.name = 'Times New Roman'
    r.font.bold = True
    r.font.size = Pt(11.5)
    r.font.color.rgb = COLOR_NAVY

def add_para(text_str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text_str)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(11.5)
    r.font.color.rgb = COLOR_BLACK

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def style_table(table, col_widths, headers, data_rows):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], HEX_TH_BG)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.runs[0]
        r.font.name = 'Times New Roman'
        r.font.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(255, 255, 255)
    
    # Data rows
    for r_idx, row_data in enumerate(data_rows):
        row_cells = table.add_row().cells
        bg_col = "F8F9FA" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_col)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            p = row_cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            if len(p.runs) > 0:
                p.runs[0].font.name = 'Times New Roman'
                p.runs[0].font.size = Pt(9.5)
                p.runs[0].font.color.rgb = COLOR_BLACK

    # Set column widths
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = Inches(width)

# Assemble Document
add_header(doc_title, doc_subtitle)
meta_items = [
    ("Student Name", "Shashwat Choudhry"),
    ("Student ID", "A20507277"),
    ("Course", "ECE 473 / 573: Cloud Computing and Cloud Native Systems (Fall 2026)"),
    ("Assignment", "Homework 04: Task Scheduling for Resource Management"),
    ("Due Date", "November 01, 2026 (Sunday, end of day Chicago time)")
]
add_meta(meta_items)

add_sec_title(intro_title)
add_para(intro_p1)

# Task Table
task_headers = ["Task Name", "Arrival Time (t)", "Expected Execution Time (Burst)", "Initial Queue Position"]
task_rows = [
    ["Task A", "0 seconds", "6 seconds", "Position 1"],
    ["Task B", "0 seconds", "8 seconds", "Position 2"],
    ["Task C", "0 seconds", "4 seconds", "Position 3"],
    ["Task D", "0 seconds", "10 seconds", "Position 4"],
    ["Task E", "0 seconds", "5 seconds", "Position 5"]
]
t_table = doc.add_table(rows=1, cols=4)
style_table(t_table, [1.5, 1.5, 2.0, 1.5], task_headers, task_rows)

add_sec_title(q1_title)
add_para(q1_intro)

add_sub_title(q1_fcfs_title)
add_para(q1_fcfs_text)

add_sub_title(q1_sjf_title)
add_para(q1_sjf_text)

add_sub_title(q1_ljf_title)
add_para(q1_ljf_text)

add_sub_title(q1_rr_title)
add_para(q1_rr_text)

# Summary Completion Time Table
comp_headers = ["Task Name", "Burst Time", "FCFS Completion", "SJF Completion", "LJF Completion", "Round Robin (q = 3)"]
comp_rows = [
    ["Task A", "6 seconds", "6 seconds", "15 seconds", "24 seconds", "18 seconds"],
    ["Task B", "8 seconds", "14 seconds", "23 seconds", "18 seconds", "29 seconds"],
    ["Task C", "4 seconds", "18 seconds", "4 seconds", "33 seconds", "22 seconds"],
    ["Task D", "10 seconds", "28 seconds", "33 seconds", "10 seconds", "33 seconds"],
    ["Task E", "5 seconds", "33 seconds", "9 seconds", "29 seconds", "27 seconds"]
]
c_table = doc.add_table(rows=1, cols=6)
style_table(c_table, [1.1, 1.0, 1.1, 1.1, 1.1, 1.1], comp_headers, comp_rows)

add_sec_title(q2_title)
add_para(q2_p1)
add_para(q2_calc_text)

# Summary Turnaround Time Table
tt_headers = ["Scheduling Policy", "Task Turnaround Times (A, B, C, D, E)", "Sum of Turnaround Times", "Average Turnaround Time", "Performance Rank"]
tt_rows = [
    ["Shortest Job First (SJF)", "A: 15s, B: 23s, C: 4s, D: 33s, E: 9s", "84 seconds", "16.8 seconds", "Rank 1 (Best Turnaround)"],
    ["First-Come, First-Served (FCFS)", "A: 6s, B: 14s, C: 18s, D: 28s, E: 33s", "99 seconds", "19.8 seconds", "Rank 2"],
    ["Longest Job First (LJF)", "A: 24s, B: 18s, C: 33s, D: 10s, E: 29s", "114 seconds", "22.8 seconds", "Rank 3"],
    ["Round Robin (RR, q = 3)", "A: 18s, B: 29s, C: 22s, D: 33s, E: 27s", "129 seconds", "25.8 seconds", "Rank 4 (Worst Turnaround)"]
]
tt_table = doc.add_table(rows=1, cols=5)
style_table(tt_table, [1.5, 2.0, 1.0, 1.0, 1.0], tt_headers, tt_rows)

add_para(q2_eval_p1)
add_para(q2_eval_p2)

# Save files
out_docx = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473/ECE473_HW04_ShashwatChoudhry.docx"
desktop_docx = "/Users/schoudhry/Desktop/ECE473_HW04_ShashwatChoudhry.docx"

doc.save(out_docx)
doc.save(desktop_docx)
print(f"Saved DOCX: {desktop_docx}")

# Convert to Apple Pages using AppleScript
desktop_pages = "/Users/schoudhry/Desktop/ECE473_HW04_ShashwatChoudhry.pages"
out_pages = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473/ECE473_HW04_ShashwatChoudhry.pages"

applescript_pages = f'''
tell application "Pages"
    activate
    open POSIX file "{desktop_docx}"
    delay 2
    set frontDoc to front document
    save frontDoc in POSIX file "{desktop_pages}"
    delay 1
    save frontDoc in POSIX file "{out_pages}"
end tell
'''
try:
    res = subprocess.run(["osascript", "-e", applescript_pages], capture_output=True, text=True, timeout=40)
    print("Pages output:", res.stdout, res.stderr)
    print(f"Generated Pages: {desktop_pages}")
except Exception as e:
    print(f"Pages error: {e}")

# Export PDF
desktop_pdf = "/Users/schoudhry/Desktop/ECE473_HW04_ShashwatChoudhry.pdf"
out_pdf = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473/ECE473_HW04_ShashwatChoudhry.pdf"

applescript_pdf = f'''
tell application "Pages"
    activate
    set frontDoc to front document
    export frontDoc to POSIX file "{desktop_pdf}" as PDF
    delay 1
    export frontDoc to POSIX file "{out_pdf}" as PDF
end tell
'''
try:
    res_pdf = subprocess.run(["osascript", "-e", applescript_pdf], capture_output=True, text=True, timeout=40)
    print("PDF output:", res_pdf.stdout, res_pdf.stderr)
    print(f"Generated PDF: {desktop_pdf}")
except Exception as e:
    print(f"PDF error: {e}")

print("ECE473 Homework 04 solution built successfully and active in Pages!")

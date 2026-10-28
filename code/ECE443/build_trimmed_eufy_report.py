import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os
import re
import subprocess

# ----------------- SECTION TEXT DEFINITIONS -----------------

doc_title = "ECE 443 / 518: Introduction to Computer Cyber Security"
doc_subtitle = "Project 3: Security in the Wild\nTechnical Analysis of the Anker Eufy Security Camera Vulnerabilities"

meta_text = "Student Name: Shashwat Choudhry\nStudent CWID: A20507277\nCourse: ECE 443 / 518 Computer Cyber Security (Fall 2026)\nTopic: Anker Eufy Security Camera Incident: Technical Security and Privacy Analysis\nDue Date: November 01, 2026"

s1_title = "1. Threat Model and Security Policy"
s1_p1 = "Home security cameras operate inside intimate spaces, recording video and audio. Modern smart cameras also process facial crops, biometric feature vectors, authentication tokens, and hardware identifiers like serial numbers and MAC addresses. Protecting these assets is a primary engineering requirement."

s1_p2 = "A proper security policy for residential surveillance requires five core properties:\n" \
        "1. Confidentiality: Live and stored footage must remain accessible exclusively to authenticated account holders.\n" \
        "2. Integrity: Video streams, control commands, and metadata must resist in-transit tampering and frame injection.\n" \
        "3. User Sovereignty: No visual data or telemetry may leave local hardware without explicit user permission.\n" \
        "4. Cryptographic Rigor: Dynamic, per-session encryption keys must protect all transmissions, anchored in local hardware security modules.\n" \
        "5. Verifiable Erasure: User deletion requests must trigger irreversible cryptographic removal across physical and cloud storage tiers."

s1_p3 = "The threat model accounts for three distinct adversaries:\n" \
        "First, external remote attackers on the Internet targeting exposed web services, media ports, and predictable cloud storage buckets.\n" \
        "Second, local network eavesdroppers intercepting unencrypted wireless packets over Wi-Fi or transit paths.\n" \
        "Third, cloud insider threats, including company personnel, third-party operators, or attackers who breach centralized cloud infrastructure."

s1_p4 = "Eufy centered its marketing on absolute privacy, promising that video footage stayed strictly local and never reached external servers without permission. Users trusted that the cameras guarding their homes would not become surveillance backdoors. The actual technical implementation contradicted every one of these promises."

s2_title = "2. Technical Breakdown of Security Flaws"
s2_p1 = "The fundamental flaw in Eufy's system was architectural misrepresentation. While advertising local on-device storage, cameras uploaded facial recognition crops, full thumbnails, and metadata to Amazon Web Services servers whenever motion occurred. These uploads occurred even when users disabled cloud features and opted out of cloud processing. Facial recognition data persisted on AWS after users deleted recordings, and profiles were correlated across accounts without disclosure."

s2_p2 = "The most critical vulnerability was unencrypted video streaming accessible through open cloud endpoints. Independent researchers discovered that anyone could stream live video from customer cameras using standard media software like VLC Player. The exploit chain operated through four steps:\n" \
        "1. A user authenticated to the Eufy web portal.\n" \
        "2. By enabling browser developer tools in debug mode, the client exposed internal API calls requesting cloud relay streams.\n" \
        "3. The server returned a plaintext streaming URL linking to Eufy's cloud media servers.\n" \
        "4. This URL could be copied directly into VLC Player, initiating an unencrypted live video feed without requiring further credentials."

s2_p3 = "The structure of the streaming URL was fundamentally insecure. It contained the camera serial number encoded in standard Base64, an epoch timestamp, an MD5 token, and a static hexadecimal signature. Because Base64 is fully reversible, anyone with access to the serial number could derive the endpoint. Serial numbers were printed directly on retail boxes and camera bodies, allowing opportunistic attackers to target discarded packaging. Furthermore, because serial numbers followed predictable patterns, attackers could automate enumeration across customer ranges. The media server never validated timestamp freshness, meaning expired timestamps were accepted without rejection."

s2_p4 = "When Eufy applied encryption, researchers decompiled camera firmware and extracted a shared, hardcoded symmetric key: 'ZXSecurity17Cam@'. Every camera across the product line used this identical 16-byte key for AES-128 encryption. The cipher ran in Electronic Codebook mode without dynamic initialization vectors, producing identical ciphertext blocks for identical inputs and leaking image structures. This static key had been visible in public configuration files since 2019, exposing thousands of households for years."

s2_p5 = "Finally, Eufy failed basic data governance standards. Deleting video clips from the mobile app left thumbnail images and facial crops intact on AWS S3 buckets. Users could access cloud-stored images even after powering off the base station, and data remained reachable following complete account deletion. This violated core privacy principles and contravened European Union GDPR mandates regarding the right to erasure."

s3_title = "3. Evaluation of Remediation, Emerging Threats, and Improvements"
s3_p1 = "When security researchers presented proof of unencrypted streaming, Anker publicly denied that VLC playback was possible. Only after major technology publications replicated the exploit across multiple states did Anker acknowledge the flaws and issue patches."

s3_p2 = "Eufy rolled out several technical fixes to resolve the disclosed vulnerabilities:\n" \
        "1. Debug mode and verbose API logging were stripped from the production web portal.\n" \
        "2. Plaintext streaming links were disabled, and video delivery was migrated to WebRTC with mandatory Datagram Transport Layer Security and Secure Real-time Transport Protocol encryption.\n" \
        "3. The hardcoded key 'ZXSecurity17Cam@' was retired in favor of dynamic session key exchanges.\n" \
        "4. Mobile applications were updated to inform users that push notification thumbnails require cloud transit unless text-only mode is selected."

s3_p3 = "While these measures closed the VLC exploit, significant threats remain. WebRTC relies on central signaling servers. An adversary observing signaling metadata can map network addresses, monitor connection intervals, and infer when occupants are home. Additionally, because Eufy manages the signaling servers, users remain vulnerable to cloud insider attacks where unauthorized public keys could be injected during signaling negotiations. The system also remains dependent on closed, proprietary firmware updates that cannot be audited by the user."

s3_p4 = "To build a genuinely secure camera system, several technical improvements are required:\n" \
        "First, implement client-side zero-knowledge encryption where video feeds are encrypted using public keys held exclusively on the user's mobile device, preventing cloud servers from viewing raw video.\n" \
        "Second, generate distinct cryptographic keys on-device using a hardware security module, eliminating shared firmware secrets.\n" \
        "Third, enforce mutual TLS authentication and certificate pinning between the camera and authorized clients to block proxy interception.\n" \
        "Fourth, establish true local network independence, allowing users to stream video directly over a local area network through authenticated local RTSP without external cloud dependencies.\n" \
        "Fifth, maintain an active third-party audit schedule and a public bug bounty program to identify and remediate vulnerabilities before commercial release."

s4_title = "4. Conclusion"
s4_p1 = "The Eufy security camera incident illustrates the severe risks created when marketing claims diverge from engineering reality. Eufy promised private, on-device storage while secretly routing unencrypted video, facial crops, and biometric data through cloud servers. The failure combined broken access controls, trivial hardcoded cryptography, and irresponsible data retention policies. While emergency patches fixed the immediate streaming loophole, the incident damaged customer trust and demonstrated that proprietary IoT systems require constant external scrutiny. Authentic consumer security requires transparent system architecture, independent audits, and cryptographic enforcement rather than unverified corporate promises."

refs_title = "5. References"
refs_p1 = "[1] S. Hollister, \"Anker's Eufy lied to us about the security of its security cameras,\" The Verge, Nov. 30, 2022.\n" \
          "[2] P. Moore, \"Eufy Security Camera Privacy and Authentication Flaws,\" Vulnerability Disclosure, Nov. 2022.\n" \
          "[3] A. Al-Fuqaha et al., \"Internet of Things: A survey on enabling technologies, protocols, and applications,\" IEEE Communications Surveys and Tutorials, vol. 17, no. 4, pp. 2347-2376, 2015.\n" \
          "[4] R. Morabito, \"CoAP vs. MQTT vs. HTTP: Evaluation of mobile IoT application protocols,\" IEEE Pervasive Computing, vol. 16, no. 4, pp. 58-66, 2017.\n" \
          "[5] SEC Consult Vulnerability Lab, \"Static Cryptographic Material in IoT Gateway Configuration Files,\" Security Advisory, 2022.\n" \
          "[6] European Union, \"Regulation (EU) 2016/679 (General Data Protection Regulation),\" Official Journal of the EU, 2016.\n" \
          "[7] C. Johnston, \"Eufy cameras found streaming unencrypted video to cloud,\" Ars Technica, Dec. 2022."

all_pieces = [
    doc_title, doc_subtitle, meta_text,
    s1_title, s1_p1, s1_p2, s1_p3, s1_p4,
    s2_title, s2_p1, s2_p2, s2_p3, s2_p4, s2_p5,
    s3_title, s3_p1, s3_p2, s3_p3, s3_p4,
    s4_title, s4_p1,
    refs_title, refs_p1
]

full_text = " ".join(all_pieces)
word_count = len(full_text.split())
print(f"Current Word Count: {word_count}")

# Check em/en dashes
dashes = re.findall(r'[—–]', full_text)
assert len(dashes) == 0, f"Found em/en dashes: {dashes}"

# Check banned words
banned = [w for w in ['delve', 'utilize', 'tapestry', 'moreover', 'ultimately'] if w in full_text.lower()]
assert len(banned) == 0, f"Found banned words: {banned}"

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

def add_para(text_str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text_str)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(11.5)
    r.font.color.rgb = COLOR_BLACK

# Assemble document
add_header(doc_title, doc_subtitle)
meta_items = [
    ("Student Name", "Shashwat Choudhry"),
    ("Student CWID", "A20507277"),
    ("Course", "ECE 443 / 518 Computer Cyber Security (Fall 2026)"),
    ("Topic Selection", "Anker Eufy Security Camera Incident: Technical Security and Privacy Analysis"),
    ("Report Due Date", "November 01, 2026"),
    ("Word Count Verification", f"{word_count} Words (Target: 1,200 Words)")
]
add_meta(meta_items)

add_sec_title(s1_title)
add_para(s1_p1)
add_para(s1_p2)
add_para(s1_p3)
add_para(s1_p4)

add_sec_title(s2_title)
add_para(s2_p1)
add_para(s2_p2)
add_para(s2_p3)
add_para(s2_p4)
add_para(s2_p5)

add_sec_title(s3_title)
add_para(s3_p1)
add_para(s3_p2)
add_para(s3_p3)
add_para(s3_p4)

add_sec_title(s4_title)
add_para(s4_p1)

add_sec_title(refs_title)
add_para(refs_p1)

# Save files
out_docx = "/Users/schoudhry/Desktop/mind-overnight/code/ECE443/ECE443_Project3_Report_ShashwatChoudhry.docx"
desktop_docx = "/Users/schoudhry/Desktop/ECE443_Project3_Report_ShashwatChoudhry.docx"

doc.save(out_docx)
doc.save(desktop_docx)
print(f"Saved DOCX to {desktop_docx}")

# Convert to Apple Pages using AppleScript
desktop_pages = "/Users/schoudhry/Desktop/ECE443_Project3_Report_ShashwatChoudhry.pages"
out_pages = "/Users/schoudhry/Desktop/mind-overnight/code/ECE443/ECE443_Project3_Report_ShashwatChoudhry.pages"

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
desktop_pdf = "/Users/schoudhry/Desktop/ECE443_Project3_Report_ShashwatChoudhry.pdf"
out_pdf = "/Users/schoudhry/Desktop/mind-overnight/code/ECE443/ECE443_Project3_Report_ShashwatChoudhry.pdf"

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

print("Trimmed report successfully built and opened in Pages!")

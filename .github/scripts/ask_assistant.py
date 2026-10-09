#!/usr/bin/env python3
"""
Smart HVAC Assistant for GitHub Issues and Pull Requests.
Powered by Gemini API (google-genai SDK).
"""

import os
import sys
import json
import urllib.request
import urllib.error

# Project context files to include in LLM context
IMPORTANT_FILES = [
    "CONTRIBUTING.md",
    "code/ECE441/SmartHVAC_Sim/README.md",
    "code/ECE441/SmartHVAC_Sim/platformio.ini",
    "code/ECE441/SmartHVAC_Sim/wokwi.toml",
    "code/ECE441/SmartHVAC_Sim/diagram.json",
    "code/ECE441/SmartHVAC_Sim/include/config.h",
    "code/ECE441/SmartHVAC_Sim/include/hal_sensors.h",
    "code/ECE441/SmartHVAC_Sim/include/thermal_comfort.h",
    "code/ECE441/SmartHVAC_Sim/src/main.cpp",
    "code/ECE441/SmartHVAC_Sim/simulation/advanced_env_sim.py",
    "code/ECE441/SmartHVAC_Sim/simulation/thermal_sim.py",
]

SYSTEM_PROMPT = """You are the technical AI assistant for the ECE 441 (Smart and Connected Systems) Smart HVAC Control project.
Your team members are:
- Andy Tran (Hardware & Power Engineer): Schematics, 12V/3.3V/5V power rails, MOSFET gate drivers, heatsink calculations.
- Shashwat Choudhry (Firmware & Control Engineer): ESP32 embedded C++, discrete PID control algorithm, PWM duty cycle modulation, I2C drivers (BME280, FS3000), calibration offsets.
- Haron Abuelhija (Cloud & IoT Architect): Wi-Fi, MQTT over TLS, HiveMQ telemetry, BLE provisioning, mobile/cloud dashboard.
- Kaleb Cowgur (Systems & Test Engineer): Duct aerodynamics, XPS insulation chamber, anemometer flow verification, thermal stress validation.

Guidelines:
1. Answer the user's question accurately based on the provided codebase, circuit schematics, pin mappings, and contribution guidelines.
2. Provide concise, clear, and actionable responses.
3. Include code snippets, wiring tables, or terminal commands where relevant.
4. Do NOT use emojis in your response.
5. If something is not yet implemented or specified, state that clearly and propose a recommended design adhering to the project architecture.
"""


def get_repo_context():
    """Gathers contents of key project files into markdown blocks."""
    context_chunks = []
    base_dir = os.getcwd()

    for rel_path in IMPORTANT_FILES:
        full_path = os.path.join(base_dir, rel_path)
        if os.path.isfile(full_path):
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                context_chunks.append(f"### File: `{rel_path}`\n```\n{content}\n```")
            except Exception as e:
                context_chunks.append(f"### File: `{rel_path}` (Error reading: {e})")
    
    return "\n\n".join(context_chunks)


def post_github_comment(repo, issue_number, comment_body, token):
    """Posts a comment to the GitHub issue or pull request."""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "SmartHVAC-Assistant-Bot",
    }
    payload = json.dumps({"body": comment_body}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            print(f"Successfully posted comment. Status code: {response.status}")
    except urllib.error.HTTPError as e:
        error_text = e.read().decode("utf-8")
        print(f"Failed to post comment to GitHub. HTTP {e.code}: {error_text}", file=sys.stderr)
        sys.exit(1)


def main():
    comment_body = os.environ.get("COMMENT_BODY", "").strip()
    issue_number = os.environ.get("ISSUE_NUMBER", "").strip()
    comment_author = os.environ.get("COMMENT_AUTHOR", "collaborator").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    # Dry-run / CLI test mode support
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Running in local test mode...")
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "What are the pin assignments for the heater and fan PWM?"
        context = get_repo_context()
        print(f"Loaded context from {len(IMPORTANT_FILES)} files ({len(context)} characters).")
        print(f"Sample query: {query}")
        return

    # Check if comment triggers the assistant
    if not comment_body.startswith("/ask"):
        print("Comment does not start with /ask. Exiting.")
        return

    question = comment_body[len("/ask"):].strip()
    if not question:
        reply = f"Hello @{comment_author}. Please provide a question after `/ask`, for example:\n`/ask How does the ESP32 PID controller map to the PWM duty cycle?`"
        if repo and issue_number and github_token:
            post_github_comment(repo, issue_number, reply, github_token)
        return

    if not gemini_api_key:
        error_msg = (
            f"Hello @{comment_author}. The `GEMINI_API_KEY` secret is not configured in this repository.\n\n"
            "To enable this assistant:\n"
            "1. Generate an API key from Google AI Studio (https://aistudio.google.com/).\n"
            "2. In GitHub, go to **Settings > Secrets and variables > Actions > New repository secret**.\n"
            "3. Name the secret `GEMINI_API_KEY` and paste your key."
        )
        print(error_msg, file=sys.stderr)
        if repo and issue_number and github_token:
            post_github_comment(repo, issue_number, error_msg, github_token)
        return

    # Call Gemini via google-genai SDK
    try:
        from google import genai
        client = genai.Client(api_key=gemini_api_key)
        
        repo_context = get_repo_context()
        full_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"## Repository Codebase Context:\n\n{repo_context}\n\n"
            f"## Question from @{comment_author}:\n{question}\n"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
        )

        answer_text = response.text.strip()
        formatted_reply = (
            f"### Response for @{comment_author}\n\n"
            f"> **Question:** {question}\n\n"
            f"{answer_text}\n\n"
            "---\n"
            "*Smart HVAC Assistant powered by Gemini 2.5 Flash*"
        )

        if repo and issue_number and github_token:
            post_github_comment(repo, issue_number, formatted_reply, github_token)
        else:
            print("Response generated:")
            print(formatted_reply)

    except Exception as e:
        error_msg = f"An error occurred while generating a response: `{str(e)}`"
        print(error_msg, file=sys.stderr)
        if repo and issue_number and github_token:
            post_github_comment(repo, issue_number, error_msg, github_token)
        sys.exit(1)


if __name__ == "__main__":
    main()

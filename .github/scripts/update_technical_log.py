#!/usr/bin/env python3
"""
Automated Engineering Technical Log Generator for Smart HVAC Control (ECE 441).
Analyzes Git commits touching code/ECE441/SmartHVAC_Sim and maintains TECHNICAL_LOG.md.
"""

import os
import sys
import subprocess
import argparse

LOG_PATH = "code/ECE441/SmartHVAC_Sim/TECHNICAL_LOG.md"
TARGET_DIR = "code/ECE441/SmartHVAC_Sim"

HEADER = """# Smart HVAC Control - Engineering Technical Log

This technical log is automatically maintained to record engineering implementations, hardware pinout configurations, closed-loop control algorithms, physical thermodynamic simulations, and cloud telemetry updates across all team members.

---
"""

# Technical summaries for historical backfill
HISTORICAL_SUMMARIES = {
    "b4bbad5": "Expanded contribution guidelines in Step 7 with detailed usage examples for the /ask AI assistant across hardware, firmware, cloud, and test domains, including live issue verification links.",
    "2dd8a4a": "Implemented GitHub Actions issue and PR automated technical assistant powered by Gemini 2.5/3.8 Flash, packaging system headers and configurations into an automated engineering Q&A pipeline.",
    "d067281": "Removed physical hardware breadboard and telemetry photos from the contribution guidelines to streamline the document focus on embedded software and Wokwi simulation.",
    "255e215": "Updated contribution guide with complete toolchain specifications, required PlatformIO libraries (PubSubClient, BME280, PID), and step-by-step Wokwi VS Code hardware emulation setup.",
    "118b61f": "Corrected actuator lockout logic and controller recovery routines in the digital twin simulation to ensure immediate restoration of baseline PID setpoints upon fault clearance.",
    "4c070bd": "Implemented automatic toggle deactivation for simulated fault injections in the digital twin UI once the dual-ESP32 supervisory logic mitigates the incident.",
    "0f8385c": "Added an automated Git commit staggering script (`stagger_commits.py`) to systematically structure incremental feature additions into discrete version-controlled checkpoints.",
    "cabe107": "Added headless Puppeteer test suites (`run_headless.js`, `run_headless2.js`, `run_headless3.js`) to validate simulation DOM rendering, canvas lifecycle, and error handlers.",
    "73770ee": "Initialized npm package definition (`package.json`, `package-lock.json`) configuring Puppeteer dependencies for automated headless simulation testing.",
    "645d65c": "Configured GitHub Pages deployment settings and updated documentation links for live web execution of the residential digital twin blueprint simulation.",
    "71b7778": "Refactored simulation documentation and updated asset CDNs to ensure stable web rendering across all browser clients.",
    "01cdf29": "Synchronized simulation live preview URL references across project documentation to target the main production branch.",
    "34caa90": "Created project README document specifying the residential digital twin architecture, multi-zone CAD blueprint layout, telemetry tabs, and hardware fault injection options.",
    "0d7164f": "Created alias synchronization between `blueprint_sim.html` and `index.html` to guarantee identical simulation runtime entry points.",
    "4c4182a": "Added visual fault highlighting overlays on the 2D CAD blueprint and integrated the primary simulation step loop linking physics updates to rendering routines.",
    "c3fabf2": "Rendered ceiling supply and return ductwork in HTML5 Canvas, animating particle diffusers for conditioned air and overlaying dynamic particulate matter/smoke hazes.",
    "2962dc3": "Engineered 2D architectural blueprint layout rendering structural envelope walls, bed zone, and workstation boundaries using scaled Canvas 2D primitives.",
    "347824b": "Built Canvas 2D context setup, responsive viewport scaling, and architectural coordinate helper functions for the digital twin CAD view.",
    "6b6502e": "Implemented bottom-right ESP32 status and diagnostic log panel displaying real-time PWM duty cycles, failover states, and firmware mitigation event feeds.",
    "4b7b9aa": "Integrated Chart.js telemetry charts displaying real-time power consumption, temperature forecasts, thermal mass, air velocity, and air quality indices.",
    "892d50b": "Built dual-MCU diagnostic reporting engine simulating heartbeat monitoring and automated MCU-A to MCU-B hot-standby failover sequences.",
    "2f14023": "Formulated indoor air quality (IAQ) dynamics, simulating VOC/CO2 accumulation curves, duct static pressure increases from filter loading, and demand load shedding.",
    "8342218": "Implemented continuous split-range PID control algorithm regulating heating and cooling effort with anti-windup clamping and deadband thresholds.",
    "9b9345a": "Constructed UI notification toast system and dual-microcontroller supervisor simulating primary ESP32 watchdog monitoring and secondary failover.",
    "5276236": "Implemented core thermodynamic engine calculating room heat capacity, envelope thermal resistance, and an exhaustive catalogue of physical HVAC hardware faults.",
    "a82acd3": "Scaffolded 2D CAD blueprint simulation layout and dark-mode architectural CSS styling with responsive telemetry grid containers.",
    "920401d": "Updated Wokwi simulation circuit (`diagram.json`) mapping GPIO 34 ADC to an interactive potentiometer to emulate dynamic ambient temperature fluctuations.",
    "b09b7bc": "Constructed WebGL 3D digital twin room interface (`3D_Digital_Twin.html`) for interactive spatial visualization of airflow vectors and temperature zones.",
    "50fbaaa": "Generated high-resolution performance response plots (`thermal_response.png`, `advanced_scenarios.png`) verifying transient PID stability and multi-variable tracking.",
    "ed4f183": "Developed multi-zone environmental simulation (`advanced_env_sim.py`) evaluating outdoor weather disturbances, solar gain, and infiltration losses.",
    "dad04b1": "Developed baseline Python thermal dynamics simulator (`thermal_sim.py`) modeling envelope heat leakage and room thermal mass differential equations.",
    "5cd9434": "Implemented ESP32 main firmware loop (`src/main.cpp`) integrating FreeRTOS dual-core tasks, discrete PID control, and non-blocking sensor acquisition.",
    "a95ba88": "Implemented Fanger thermal comfort equations (`include/thermal_comfort.h`) computing apparent Feels Like temperature, PMV, and PPD indices.",
    "2c968fa": "Implemented sensor hardware abstraction layer (`include/hal_sensors.h`) supporting I2C Bosch BME280 acquisition with mock FS3000 airflow fallbacks.",
    "e522e37": "Defined hardware GPIO pinouts, PWM frequency (5 kHz), timer channels, and HiveMQ MQTT topics in `include/config.h`.",
    "52b3dbd": "Designed Wokwi virtual hardware schematic (`diagram.json`) connecting ESP32 DevKit C v4, heater PWM LED (GPIO 25), and fan PWM LED (GPIO 26).",
    "07c3912": "Added VS Code workspace configuration (`.vscode/extensions.json`) recommending PlatformIO IDE and C/C++ extension toolchains.",
    "c4c4fe4": "Initialized PlatformIO project structure and configuration (`platformio.ini`) targeting ESP32 DevKit with Arduino framework and Wokwi simulation metadata.",
}


def run_cmd(cmd):
    """Executes a shell command and returns trimmed stdout."""
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return res.stdout.strip()


def summarize_commit_with_gemini(author, message, diff, api_key):
    """Uses Gemini to summarize a commit into a 1-2 sentence engineering description."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = (
            "You are a technical documentation assistant for the Smart HVAC engineering project.\n"
            f"Commit Author: {author}\n"
            f"Commit Message: {message}\n"
            f"Git Diff:\n{diff[:4000]}\n\n"
            "Write a concise 1 to 2 sentence technical summary of this commit. "
            "Focus specifically on the engineering changes (e.g. circuits, pinouts, PID parameters, "
            "sensors, MQTT topics, simulation physics, or firmware loops). "
            "Do NOT use emojis. Output ONLY the 1-2 sentences."
        )
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        summary = response.text.strip()
        if summary:
            return summary
    except Exception as e:
        print(f"Gemini summarization warning: {e}", file=sys.stderr)

    # Fallback: clean the commit message
    return f"{message[0].upper() + message[1:] if message else 'Codebase update'}. Modified files in the Smart HVAC subsystem."


def format_entry(date_str, author, commit_hash, summary):
    """Formats a single technical log entry."""
    return (
        f"### [{date_str}] {author}\n"
        f"* **Commit:** `{commit_hash}`\n"
        f"* **Technical Summary:** {summary}\n\n"
        "---\n\n"
    )


def generate_backfill():
    """Generates the full historical log from all commits touching the HVAC directory."""
    raw_log = run_cmd([
        "git", "log", "--pretty=format:%h|%an|%ad|%s", "--date=short", "--", TARGET_DIR
    ])

    entries = []
    lines = raw_log.splitlines()

    for line in lines:
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        commit_hash, author, date_str, message = parts
        
        # Use curated historical summary if available, else clean message
        summary = HISTORICAL_SUMMARIES.get(commit_hash)
        if not summary:
            summary = f"{message[0].upper() + message[1:]}. Modified Smart HVAC subsystem files."

        entries.append(format_entry(date_str, author, commit_hash, summary))

    content = HEADER + "\n" + "".join(entries)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Successfully generated backfill with {len(entries)} entries at {LOG_PATH}")


def update_incremental(before_commit, after_commit, api_key):
    """Appends new commits from a push event to the top of the technical log."""
    if not os.path.exists(LOG_PATH):
        generate_backfill()
        return

    # Check commits between before and after
    cmd = ["git", "log", "--pretty=format:%h|%an|%ad|%s", "--date=short"]
    if before_commit and before_commit != "0000000000000000000000000000000000000000":
        cmd.append(f"{before_commit}..{after_commit}")
    else:
        cmd.extend(["-n", "1", after_commit])
    cmd.extend(["--", TARGET_DIR])

    try:
        raw_log = run_cmd(cmd)
    except Exception as e:
        print(f"Error reading git log: {e}", file=sys.stderr)
        return

    if not raw_log.strip():
        print("No commits affecting Smart HVAC in this push range.")
        return

    new_entries = []
    for line in raw_log.splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        commit_hash, author, date_str, message = parts

        # Read diff for this commit
        try:
            diff = run_cmd(["git", "show", "--stat", "-p", commit_hash, "--", TARGET_DIR])
        except Exception:
            diff = ""

        if api_key:
            summary = summarize_commit_with_gemini(author, message, diff, api_key)
        else:
            summary = f"{message[0].upper() + message[1:]}. Updated Smart HVAC engineering files."

        new_entries.append(format_entry(date_str, author, commit_hash, summary))

    if not new_entries:
        print("No valid entries to add.")
        return

    # Read existing content
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        existing_content = f.read()

    # Insert after HEADER
    if HEADER in existing_content:
        rest = existing_content[len(HEADER):].lstrip("\n")
        updated_content = HEADER + "\n" + "".join(new_entries) + rest
    else:
        updated_content = HEADER + "\n" + "".join(new_entries) + existing_content

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print(f"Successfully prepended {len(new_entries)} new entries to {LOG_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Update Smart HVAC Technical Log.")
    parser.add_argument("--backfill", action="store_true", help="Generate full historical log.")
    parser.add_argument("--range", nargs=2, metavar=("BEFORE", "AFTER"), help="Process commits between BEFORE and AFTER.")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "")

    if args.backfill:
        generate_backfill()
    elif args.range:
        update_incremental(args.range[0], args.range[1], api_key)
    else:
        # Default to backfill if file does not exist, otherwise update latest
        if not os.path.exists(LOG_PATH):
            generate_backfill()
        else:
            update_incremental("HEAD~1", "HEAD", api_key)


if __name__ == "__main__":
    main()

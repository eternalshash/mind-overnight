# Mind Overnight

This repo is a collection of a caffeinated mind. It includes various investment reports, code snippets, engineering design lessons, and technical explorations.

---

## Repository Structure

* **`analysis.prac/`** — Quantitative equity research, financial modeling, and investment valuation studies.
  * **`Oura/`** — Investment research and financial valuation models for Oura Health's potential IPO.
    * **`charts/`** — Visualizations of unit economics, valuation sensitivity distributions, moat radar, and backtests.
    * **`code/`** — Python modeling modules for unit economics, DCF/multiples valuation, NLP review sentiment analysis, and moat scoring.
    * **`docs/`** — In-depth equity research report and investment memo for Oura.
    * **`pdfs/`** — Exported investment research reports and documentation.
  * **`PSUS/`** — Pre-IPO equity research and financial valuation analysis on Pegasus/PSUS.
    * **`code/`** — Financial modeling and data preparation routines for PSUS.
      * **`Modeling.Prac/`** — Jupyter notebooks for data ingestion, financial modeling, and metric forecasting.
    * **`pdfs/`** — Research publications and valuation reports.
      * **`Findings/`** — Comprehensive equity research findings and investment memos on PSUS.
  * **`charts/`** — Cross-asset quantitative charts and comparative backtest visualizations (e.g., Oura vs. Garmin).

* **`assets/`** — Repository-wide static media, icons, and graphic resources.

* **`code/`** — Academic coursework, hardware/software implementations, simulations, and project prototypes.
  * **`ECE441/`** — Smart and Connected Systems coursework, embedded IoT lab exercises, and digital twin simulations.
    * **`SmartHVAC_Sim/`** — Residential Digital Twin simulation and dual-ESP32 HVAC control prototype featuring continuous split-range PID/PWM modulation, indoor air quality (IAQ) modeling, interactive blueprint GUI, Wokwi hardware simulation, and automated fault injection testing.
    * **`lab01SC/`** — Microcontroller and sensor interfacing lab with Wokwi and PlatformIO simulation configurations.
      * **`src/`** — Embedded C firmware source code for the lab implementation.
    * **`lab02_media/`** — Oscilloscope captures, logic analyzer traces, circuit wiring setups, and hardware validation recordings for Lab 2.
    * **`lab03/`** — Wireless data acquisition and Bluetooth telemetry lab interfacing an Arduino UNO R4 WiFi, DHT22 sensor, HC-06 Bluetooth module, Raspberry Pi Python gateway daemon, ThingSpeak cloud telemetry, and Bleak BLE client.
  * **`ECE443/`** — Computer Architecture and Parallel Processing coursework in Go.
    * **`prj02-go/`** — Parallel computing algorithms, concurrency benchmarking suites, and execution validation.
  * **`ECE473/`** — Cloud Computing and Distributed Systems projects and assignments.
    * **`ece473-prj01/`** — Containerized distributed marketplace microservice platform in Go with baseline and transaction testing.
      * **`marketplace-service/`** — Go microservice managing product listings, order transactions, and Docker containerization.
      * **`scripts/`** — Automation scripts for service startup, endpoint verification, and lifecycle management.
    * **`ece473-prj02/`** — Persistent distributed marketplace microservice backed by SQLite/PostgreSQL with Docker Compose, automated acceptance testing, and container scaling.
    * **`ece473-prj03/`** — Multi-tier microservice architecture with independent Authentication Service (JWT authentication, PBKDF2 password hashing), Marketplace Service, SQLite database, Docker Compose orchestration, and automated vulnerability/attack penetration tests.
    * **`hw3/`** — Distributed systems coursework implementations in Go.
  * **`ECE485proj2/`** — Advanced Computer Architecture: 32-bit single-cycle MIPS CPU designed in VHDL with comprehensive verification testbenches.
  * **`fraud-footy/`** — Full-stack web application evaluating footballer performance against opponent defender difficulty.
    * **`backend/`** — FastAPI and Python scraping service for processing player and match data.
      * **`cache/`** — Cached player match performance JSON datasets.
    * **`public/`** — Static web assets, favicons, and vector icons for the frontend.
    * **`src/`** — React frontend source code styled with Tailwind CSS and Vite.
      * **`assets/`** — Frontend UI images and SVG graphics.
      * **`components/`** — Modular React UI components including scorecards, pitch visuals, and defender tables.
  * **`futbolV1/`** — Statistical analysis scripts and datasets analyzing European soccer players against active defenders.
  * **`general programming/`** — Foundational Java object-oriented programming exercises and algorithm implementations.
  * **`missile_interception_sim/`** — Multi-phase kinetic trajectory simulations and 3D visual models of theater ballistic missile defense.
    * Analytical physics engine (`physics_engine.py`), GNC guidance algorithms (`gnc_engine.py`), defensive multi-battery allocation (`defense_system.py`), and saturation swarm modeling (`attack_sim.py`).
    * Desktop PySide interface (`desktop_gui.py`, `run_desktop.py`) with weapons catalog, mapping utilities, and interactive web twins.
  * **`Modeling.Prac/`** — Statistical and financial data modeling workspace.
  * **`rust_v1/`** — Systems programming practice and learning exercises in Rust.
    * **`hello/`** — Cargo project exploring Rust syntax, ownership, and memory safety.
      * **`src/`** — Daily practice source files and algorithm exercises.
    * **`src/`** — Additional experimental Rust and C++ implementations.
  * **Coursework & Data Files:**
    * **`cpu_comp.v`** — Verilog structural CPU hardware component implementation.
    * **`ECE473HW02.go`** — Distributed systems Go coursework implementation.
    * **`epl_match_details.csv`** — Comprehensive historical Premier League match dataset.

* **`docs/`** — Interactive browser-based simulation visualizations and documentation artifacts hosted via GitHub Pages:
  * **`theater_engagement_duel.html`** — Interactive 3D ballistic missile duel and air defense engagement visualization.
  * **`attack_sim_theater.html`** — Interactive theater saturation attack and multi-battery defensive simulation.

* **`ece449/`** — Neural Networks and Deep Learning coursework (Illinois Tech ECE 449).
  * **`project2/`** — Custom deep learning computational graph framework (`EasyNN`) in C++ and Python implementing dynamic expression graphs, automatic differentiation, gradient descent, and MNIST classification benchmarks.
  * **`project3/`** — Advanced neural network architecture extensions in `EasyNN` featuring modular layer abstractions, loss evaluation routines, and model optimization.
  * **Problem Sets & Tooling** — C++ algorithmic implementations (`hw1_q6.cpp`, `q1_a.cpp` through `q5.cpp`) and automated LaTeX/documentation generation pipelines.

* **`pdfs/`** — Compiled project reports, engineering documentation, and academic deliverables.
  * **`Engineering/`** — Digital systems and hardware architecture project reports (e.g., ECE 485 CPU design report).
  * **`Findings/`** — Research memos, case study writeups, and analytical findings.
  * **`Choudhry_Shashwat proj 1 (1).pdf`** — Academic engineering report deliverable.

* **Root Utilities & Documentation:**
  * **`CONTRIBUTING.md`** — Team development guide covering PlatformIO/Wokwi configuration, FreeRTOS tasks, coding standards, and PR workflows.
  * **`ece485CaseStudy1&2.zip`** — Advanced Computer Architecture case studies and test data archive.
  * **`index.html`** — GitHub Pages interactive portfolio portal linking to live web-based digital twin simulations.

---

## About Me
I am an engineer and researcher focused on solving complex problems across embedded systems, hardware-software integration, and defense technologies. My academic background spans data driven modeling of complex systems and engineering at the Illinois Institute of Technology. Next year, I will be stepping into the aerospace and defense sector to work on mission critical systems and advanced engineering solutions.

Outside the lab and classroom, you will catch me in the gym or out on a hike.

---

## Reach Out
[![website](https://img.shields.io/badge/my_portfolio-000?style=for-the-badge&logo=ko-fi&logoColor=white)](https://choudhryshashwat29.wixstudio.com/my-site)
[![linkedin](https://img.shields.io/badge/linkedin-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/schoudhry/)

# ECE 441: Smart and Connected Systems / Internet of Things
## Experiment No. 04: Human-Machine Interface: Cloud Database and Mobile Device

**Author:** Shashwat Choudhry  
**Laboratory Partners:** Andy Tran, Kaleb Cowgur, Haron Abuelhija (Group 2)  
**Course:** ECE 441 Fall 2026  
**Instructors:** Dr. Jafar Saniie & Prof. Tianyang Fang  
**Department:** Electrical and Computer Engineering, Illinois Institute of Technology  
**Experiment Date:** October 08, 2026 – October 09, 2026  
**Report Due Date:** October 22, 2026  

---

## 1. Directory Overview

```
lab04/
├── lab04ECE441.pages              # Native Apple Pages Formal Engineering Report
├── ECELabReport04441.pdf          # Formal Laboratory Report (Exported PDF)
├── lab04ECE441.docx               # MS Word / Intermediate DOCX format
├── README.md                      # Experiment summary and reproduction guide
├── Experiment 4/                  # Lab manual, demo video, and slides from instructors
│   ├── ECE 441 Experiment 4 Cloud Database and Mobile Device.docx
│   ├── ECE 441 Experiment 4 Cloud Database and Mobile Device.pdf
│   ├── ECE441 Lab 4 Codes.zip
│   ├── ECE441Lab4Demo.mp4
│   └── GromovLab4Slides.pptx
└── Lab04_Media/                   # Laboratory empirical data, photos, video & codes
    ├── 20261009_151847000_iOS.MOV # Demonstration video of live end-to-end telemetry
    ├── processed/                 # High-resolution normalized photos embedded in report
    └── ECE441 Lab 4 Codes/        # Android Studio client project (Java, Gradle 8.9)
```

---

## 2. Multi-Tier System Architecture

1. **Edge Sensing Tier:** An **Adafruit AHT20** digital temperature and relative humidity sensor wired to the hardware I2C bus (`/dev/i2c-1` @ `0x38`) of a **Raspberry Pi 4**.
2. **Edge Telemetry Daemon:** `lab04.py` (Python 3) samples the sensor every 2.0 seconds (0.5 Hz) and synchronizes a JSON record to Google Firebase.
3. **Cloud Database Tier:** **Google Firebase Realtime Database** project `ece441lab04` (`https://ece441lab04-default-rtdb.firebaseio.com`), persisting data at `/SensorDatabase`.
4. **Mobile HMI Tier:** An **Android Application** (`com.example.group2_ece441_lab4_firebase_client`) utilizing the Firebase Realtime Database SDK `ValueEventListener` to reactively render live temperature, humidity, and timestamp cards with sub-second latency.

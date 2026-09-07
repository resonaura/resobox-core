# ResoBox Core

[![Python](https://img.shields.io/badge/Python-3.x-3776AB.svg?logo=python&logoColor=white)](#)
[![JACK Audio](https://img.shields.io/badge/Audio-JACK%20%7C%20PortAudio-8A2BE2.svg)](#)
[![DSP Framework](https://img.shields.io/badge/DSP-Spotify%20Pedalboard-1DB954.svg?logo=spotify&logoColor=white)](#)
[![OS](https://img.shields.io/badge/OS-Alpine%20Linux%20(RT)-0D597F.svg?logo=alpinelinux&logoColor=white)](#)
[![Hardware](https://img.shields.io/badge/Hardware-Raspberry%20Pi%20%2B%20HiFiBerry-C51A4A.svg?logo=raspberrypi&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor%20on%20GitHub-EA4AAA?logo=github-sponsors&logoColor=white)](https://github.com/sponsors/resonaura)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/resonaura)

**ResoBox Core** is the real-time audio processing software daemon and DSP engine for **ResoBox**, a custom standalone guitar pedalboard appliance. It pairs studio-grade I/O hardware with an ultra-minimal, real-time Linux operating system to deliver low-latency audio effects and live stage performance.

<p align="center">
  <img src="https://raw.githubusercontent.com/resonaura/resobox-core/main/media/resobox-hardware.jpg" width="800" alt="ResoBox Hardware Prototype" />
</p>

---

## 🛠️ Architecture & Hardware Stack

- **Raspberry Pi + HiFiBerry Studio Sound Card**: Connects a high-definition HiFiBerry DAC+ ADC HAT directly to the Raspberry Pi 40-pin GPIO header via the I2S digital audio bus. Dedicated onboard Burr-Brown converters and dual low-jitter crystal oscillators ensure clean, low-latency audio capture and analog playback.
- **Custom Alpine Linux Appliance Build**: A tailor-made, minimal Alpine Linux distribution stripped of unnecessary background services, optimized specifically for real-time audio scheduling, zero CPU throttling, and instant cold-boot readiness.
- **JACK Audio Connection Kit**: Audio streaming runs directly through a lightweight JACK audio daemon at low buffer sizes (64/128 samples) with zero intermediate ALSA mixer overhead.
- **Modular Python DSP Engine (`pedalboard`)**: Audio frames are ingested via `jack-client` into NumPy arrays and routed through a modular DSP chain powered by Spotify's `pedalboard` framework:
  - NoiseGate and dynamic suppression
  - Multi-stage overdrive and high-gain distortion
  - Impulse Response (IR) speaker cabinet convolution (`cab.wav`)
  - Analog tape delay and tempo-synced feedback
  - Algorithmic and convolution reverberation
  - Modulation effects (chorus, flanger, stereo panning)
  - Parametric EQ and highpass/lowpass shelving
- **Live Telemetry & RMS Metering**: Continuous moving-average root-mean-square (RMS) calculation provides live dBFS levels for input and output channels without audio thread stalls.
- **Asynchronous IPC & Control**:
  - **WebSocket Server (`:8765`)**: Streams live VU telemetry and real-time effect parameters to the [ResoBox UI](https://github.com/resonaura/resobox-ui) companion dashboard.
  - **REST API (`aiohttp`)**: Handles dynamic preset loading, parameter adjustments, and bypass toggles.

---

## 📂 Project Structure

```
resobox-core/
├── audio.py            # JACK client setup, audio callback loop, and DSP execution
├── config.py           # Pedalboard FX chain configuration and plugin parameters
├── realtime.py         # Async WebSocket server for live telemetry broadcast
├── webhost.py          # aiohttp HTTP REST API for remote control
├── graphics.py         # OLED display driver and hardware UI rendering
├── main.py             # Process coordinator and daemon startup
├── plugins/            # Custom audio DSP plugins and utilities
├── assets/             # Speaker cabinet impulse responses (IRs) and presets
├── requirements.txt    # Python dependencies (pedalboard, sounddevice, jack-client, aiohttp)
└── media/              # Hardware and system photos
```

---

## 🚀 Getting Started

### Prerequisites

- Raspberry Pi (3B+, 4, or newer) running Alpine Linux with JACK Audio installed
- HiFiBerry DAC+ ADC (or compatible I2S audio HAT)
- Python 3.10+

### Installation

```bash
# Install system dependencies on Alpine Linux
apk add jack jack-dev python3 py3-pip py3-numpy build-base

# Install Python packages
pip install -r requirements.txt
```

### Running the Core Daemon

```bash
# Start JACK audio daemon
jackd -R -d alsa -d hw:sndrpihifiberry -p 128 -n 2 -r 44100 &

# Start ResoBox Core
python3 main.py
```

Companion frontend interface: [resonaura/resobox-ui](https://github.com/resonaura/resobox-ui)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

 <div align="center">

# RAM REDUCT LINUX

### Lightweight Memory Cleaner for Linux

A lightweight Linux memory management utility with a modern dark GUI.

[![Linux](https://img.shields.io/badge/OS-Linux-orange?style=for-the-badge&logo=linux&logoColor=white)](https://www.kernel.org/)
[![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Debian%20%7C%20Ubuntu-red?style=for-the-badge&logo=debian&logoColor=white)](https://www.debian.org/)

<br>

<a href="https://github.com/junior-dior/ramreduct-linux/releases">
  <img src="https://img.shields.io/badge/⬇_DOWNLOAD-RELEASES-238636?style=for-the-badge" alt="Download Releases">
</a>
&nbsp;
<a href="https://github.com/junior-dior/ramreduct-linux">
  <img src="https://img.shields.io/badge/VIEW-SOURCE-30363d?style=for-the-badge&logo=github&logoColor=white" alt="View Source">
</a>

</div>

---

## Overview

**RAM Reduct Linux** is a lightweight memory cleaning utility designed for Linux desktops. It provides a graphical interface for monitoring and managing system memory.

Inspired by memory cleaning utilities on Windows, this project brings memory management features to Linux with a clean, dark-themed interface.

## Features

- 🧠 **Memory Management** — Manage system memory and reclaim available resources.
- ⚡ **Cache Cleaning** — Drop eligible Linux filesystem caches.
- 🔧 **Process Memory Management** — Trim process memory where supported.
- 🔄 **Automatic Cleaning** — Configure automatic memory cleaning.
- 🎨 **Dark GUI** — A simple, modern graphical interface.
- 🖥️ **Desktop Integration** — Launch the application from your desktop menu.
- 📦 **DEB Package** — Build a Debian installation package from source.

## Download

<div align="center">

### Get RAM Reduct Linux

Download available packages from the GitHub Releases page.

<a href="https://github.com/junior-dior/ramreduct-linux/releases">
  <img src="https://img.shields.io/badge/Download%20Latest%20Release-Click%20Here-2ea44f?style=for-the-badge&logo=github" alt="Download Latest Release">
</a>

</div>

> **Note:** Downloadable release assets will be available when a release package has been published.

## Build from Source

### Requirements

- Debian or Ubuntu-based Linux distribution
- Python 3
- GTK 3 and Python GObject dependencies
- `dpkg-deb` and standard build utilities

### 1. Clone the repository

```bash
git clone https://github.com/junior-dior/ramreduct-linux.git
cd ramreduct-linux
```

### 2. Build the DEB package

```bash
chmod +x build-deb.sh
./build-deb.sh
```

### 3. Install the package

```bash
sudo apt install ./build/ramreduct-linux_2.0.0_all.deb
```

### 4. Launch the application

```bash
ramreduct
```

You can also launch the application from your desktop application menu if desktop integration is available.

## Quick Build

Build the `.deb` package with a single command:

```bash
git clone https://github.com/junior-dior/ramreduct-linux.git && cd ramreduct-linux && chmod +x build-deb.sh && ./build-deb.sh
```

## Project Structure

```text
ramreduct-linux/
├── README.md
├── build-deb.sh
├── org.ramreduct.policy
├── ramreduct-helper
├── ramreduct.desktop
├── ramreduct.py
└── ramreduct.svg
```

| File | Description |
|---|---|
| `ramreduct.py` | Main application |
| `build-deb.sh` | Build the Debian package |
| `ramreduct-helper` | Privileged helper |
| `org.ramreduct.policy` | PolicyKit authorization |
| `ramreduct.desktop` | Desktop launcher |
| `ramreduct.svg` | Application icon |

## Important Notes

- Memory cleaning does not increase the physical RAM installed in your computer.
- Linux uses available memory for filesystem caching to improve performance. Clearing caches may not always improve performance.
- Some operations require elevated privileges.
- Review scripts and permissions before running software with administrator privileges.

## Contributing

Contributions, bug reports, and feature suggestions are welcome.

- [Report a bug](https://github.com/junior-dior/ramreduct-linux/issues)
- [View source code](https://github.com/junior-dior/ramreduct-linux)
- [Download releases](https://github.com/junior-dior/ramreduct-linux/releases)

## License

See the repository for licensing information.

---

<div align="center">

**RAM REDUCT LINUX**

*Lightweight. Simple. Linux.*

Made for Linux users 🐧

</div>

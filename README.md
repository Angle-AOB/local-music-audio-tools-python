# Local Music Audio Tools Python | 本地音乐音频管理Python工具集

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/) [![FFmpeg](https://img.shields.io/badge/ffmpeg-required-orange.svg)](https://ffmpeg.org/)

<div align="center">

**[English](#english)** | **[简体中文](#简体中文)**

</div>

---

<a name="english"></a>
# 🎯 Project Overview

This is a lightweight audio management toolkit designed specifically for **local music enthusiasts**, helping you better manage and maintain your personal music library.

> ⚠️ **Note**: This is not professional audio editing software, but a convenient tool for users who prefer local music, especially adept at handling audio conversion with metadata.

### ✨ Key Features

- 🎵 **Complete Metadata Preservation**: Retains cover art, title, artist, and other information during format conversion
- 🔍 **Smart Format Detection**: Identifies "fake lossless" files and low-quality audio
- 🛠️ **Embedded Image Repair Tool**: May fix issues where some files contain images that don't display in players
- 💻 **Local Processing**: All operations are performed locally to protect privacy
- 🚀 **Easy to Use**: Simply drag and drop files or folders to start processing

---

## 📦 Tool List

### 1. toOpus-beta.py - Audio to OPUS Converter

Batch convert MP3, WAV, FLAC and other formats to efficient OPUS format while fully preserving metadata and cover art.

**Main Features:**
- ✅ Supports multiple input formats (MP3/WAV/FLAC/OGG/M4A, etc.)
- ✅ Multi-threaded accelerated processing
- ✅ Automatically copies cover art and tag information
- ✅ Optional WebP cover compression to reduce file size
- ✅ Customizable bitrate (64-512 kbps)

**Usage Example:**
```bash
python toOpus-beta.py
# Then follow the prompts to enter parameters, or drag and drop files/folders into the program window
```

---

### 2. flac_wav_detector-beta.py - True/False Lossless Detector

Detects whether FLAC/WAV files are truly lossless or converted from lossy formats (such as MP3).

**Main Features:**
- 🔎 Analyzes actual encoding format
- 🏷️ Detects suspicious identifiers in filenames
- 📊 Displays detailed audio parameters (bitrate, sample rate, bit depth, etc.)
- 🔄 Automatically renames mislabeled files

**Usage Example:**
```bash
python flac_wav_detector-beta.py
# Drag and drop FLAC/WAV files or folders containing these files
```

---

### 3. fix_mp3_cover_mime-beta.py - MP3 Cover MIME Type Fixer

Fixes MIME type errors in embedded cover art in MP3 files, resolving issues where some players cannot properly display covers.

**Main Features:**
- 🔧 Automatically detects the true format of cover images
- 📝 Corrects MIME type declarations in ID3 tags
- 📁 Supports batch processing of entire folders
- ⚡ Optional automatic mode without individual confirmation

**Usage Example:**
```bash
python fix_mp3_cover_mime-beta.py
# Drag and drop MP3 files or folders for batch processing
```

---

### 4. low_bitrate_detector.py - Low Bitrate MP3 Detector

Scans MP3 files and marks those with bitrates below 300kbps, helping you identify low-quality audio.

**Main Features:**
- 📉 Precisely detects audio bitrate
- 🚩 Marks files below threshold (default 300kbps)
- 📂 Supports recursive folder scanning
- 📋 Generates detection reports

**Usage Example:**
```bash
python low_bitrate_detector.py
# Enter file or folder path, or use drag-and-drop method
```

---

## 🚀 Quick Start

### System Requirements

- Tested only on Windows, but should also support macOS and Linux
- [Python](https://www.python.org/downloads/) 3.7+
- [FFmpeg](https://ffmpeg.org/download.html) (must be installed and added to system PATH)
- Optional Python dependencies:
mutagen (for metadata-related operations),
psutil (for detecting CPU physical core count, but can detect logical cores without it to reasonably adjust thread count)

### Installation Steps

1. **Clone Repository or Download ZIP**
```bash
git clone https://github.com/yourusername/LocalAudio-Toolkit.git
cd LocalAudio-Toolkit
```

2. **Install FFmpeg**
   
   **Windows:**
   - Download from [FFmpeg Official Website](https://ffmpeg.org/download.html)
   - After extracting, add the `bin` directory to system PATH
   
   **macOS:**
   ```bash
   brew install ffmpeg
   ```
   
   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get install ffmpeg
   ```

3. **Install Python Dependencies**
```bash
pip install mutagen psutil
```

### Running the Tools

Simply run any script:
```bash
python toOpus-beta.py
python flac_wav_detector-beta.py
python fix_mp3_cover_mime-beta.py
python low_bitrate_detector.py
```

Supports **drag-and-drop operation**: Simply drag files or folders to the program window!

---

## 💡 Use Cases

### Scenario 1: Optimize Music Library Storage Space
```
Original MP3 Library → Convert using toOpus → Save 50-70% space + Preserve all metadata
However, lossy to lossy conversion will definitely reduce quality, but if converting from lossless sources to Opus, it can replace MP3
```

### Scenario 2: Clean Up "Fake Lossless" Files
```
Mixed Format Library → Scan using flac_wav_detector → Identify and rename pseudo-lossless files
```

### Scenario 3: Fix Player Cover Art Issues
```
Cover Display Problems → Fix using fix_mp3_cover_mime → Normal display in all players
```

### Scenario 4: Filter High-Quality Audio
```
Large MP3 Collection → Detect using low_bitrate_detector → Mark low-quality files for replacement
```

---

## ❓ FAQ

### Q: Why do I need these tools?
A: It's hard to find tools online that can **fully preserve metadata and cover art during format conversion**, especially lightweight solutions for personal local music libraries. That's why this toolkit was created.

### Q: What are the advantages of OPUS format?
A: OPUS offers better audio quality than MP3/AAC at the same bitrate, with smaller file sizes. 128kbps OPUS quality is close to 256kbps MP3, making it ideal for storing large music collections.

### Q: Will I lose audio quality after conversion?
A: Converting from lossy formats (like MP3) won't improve quality; it will slightly reduce existing quality while reducing file size. When converting from lossless formats (FLAC/WAV), it's recommended to use higher bitrates (≥192kbps).

### Q: Are these tools safe?
A: Completely safe! All processing is done locally without uploading any data. If concerned, create backups and test with small samples first.

---

## 🤝 Contributing

Issues and Pull Requests are welcome! If you have other practical audio management ideas, feel free to discuss.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

- [FFmpeg](https://ffmpeg.org/) - Powerful multimedia framework
- [Mutagen](https://mutagen.readthedocs.io/) - Python audio metadata processing library
- [Lingma](https://lingma.aliyun.com/) - Assisting in code development and improvement

---

<div align="center">

**If this project helps you, please give it a ⭐!**

</div>

---

<a name="简体中文"></a>
<div align="center">

**[↑ Back to English](#english)**

</div>

---

## 🎯 项目简介

这是一套专为**本地音乐爱好者**设计的轻量级音频管理工具集，帮助你更好地管理和维护个人音乐资源库。

> ⚠️ **提示**：这不是专业的音频编辑软件，只是为偏好本地音乐的用户提供的便捷工具，特别擅长处理带元数据的音频转换。

### ✨ 核心特色

- 🎵 **完整的元数据保留**：转换格式时能保留封面、标题、艺术家等信息
- 🔍 **智能格式检测**：识别"假无损"文件和低质量音频
- 🛠️ **内嵌图片修复工具**：可能修正某些文件含有图片但是播放器不显示的问题
- 💻 **本地化处理**：所有操作在本地完成，保护隐私
- 🚀 **简单易用**：拖拽文件或文件夹即可开始处理

---

## 📦 工具列表

### 1. toOpus-beta.py - 音频转OPUS转换器

将MP3、WAV、FLAC等格式批量转换为高效的OPUS格式，同时完整保留元数据和封面。

**主要功能：**
- ✅ 支持多种输入格式（MP3/WAV/FLAC/OGG/M4A等）
- ✅ 多线程加速处理
- ✅ 自动复制封面和标签信息
- ✅ 可选WebP封面压缩以减小文件大小
- ✅ 自定义比特率（64-512 kbps）

**使用示例：**
```bash
python toOpus-beta.py
# 然后按提示输入参数，或拖拽文件/文件夹到程序窗口
```

---

### 2. flac_wav_detector-beta.py - 真假无损检测器

检测FLAC/WAV文件是否为真正的无损格式，还是从有损格式（如MP3）转换而来。

**主要功能：**
- 🔎 分析实际编码格式
- 🏷️ 检测文件名中的可疑标识
- 📊 显示详细的音频参数（码率、采样率、位深度等）
- 🔄 自动重命名误标文件

**使用示例：**
```bash
python flac_wav_detector-beta.py
# 拖拽FLAC/WAV文件或包含这些文件的文件夹
```

---

### 3. fix_mp3_cover_mime-beta.py - MP3封面MIME类型修复

修复MP3文件中嵌入封面的MIME类型错误，解决某些播放器无法正确显示封面的问题。

**主要功能：**
- 🔧 自动检测封面图片的真实格式
- 📝 修正ID3标签中的MIME类型声明
- 📁 支持批量处理整个文件夹
- ⚡ 可选自动模式无需逐一确认

**使用示例：**
```bash
python fix_mp3_cover_mime-beta.py
# 拖拽MP3文件或文件夹进行批量修复
```

---

### 4. low_bitrate_detector.py - 低码率MP3检测器

扫描MP3文件并标记比特率低于300kbps的文件，帮助你识别低质量音频。

**主要功能：**
- 📉 精确检测音频比特率
- 🚩 标记低于阈值的文件（默认300kbps）
- 📂 支持递归扫描文件夹
- 📋 生成检测报告

**使用示例：**
```bash
python low_bitrate_detector.py
# 输入文件或文件夹路径，或使用拖拽方式
```

---

## 🚀 快速开始

### 系统要求

- 仅在Windows测试使用过，但应该也支持macOS和Linux
- [Python](https://www.python.org/downloads/) 3.7+
- [FFmpeg](https://ffmpeg.org/download.html)（必须安装并添加到系统PATH）
- 可选依赖python库：
mutagen (用于元数据相关)、
psutil (用于检测CPU物理核心数，但没有它也能检测逻辑核心数，用以合理调整线程数)

### 安装步骤

1. **克隆仓库 或 下载ZIP**
```bash
git clone https://github.com/yourusername/LocalAudio-Toolkit.git
cd LocalAudio-Toolkit
```

2. **安装FFmpeg**
   
   **Windows:**
   - 从 [FFmpeg官网](https://ffmpeg.org/download.html) 下载
   - 解压后将`bin`目录添加到系统PATH
   
   **macOS:**
   ```bash
   brew install ffmpeg
   ```
   
   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get install ffmpeg
   ```

3. **安装Python依赖**
```bash
pip install mutagen psutil
```

### 运行工具

直接运行任意脚本即可：
```bash
python toOpus-beta.py
python flac_wav_detector-beta.py
python fix_mp3_cover_mime-beta.py
python low_bitrate_detector.py
```

支持**拖拽操作**：直接将文件或文件夹拖到程序窗口即可！

---

## 💡 使用场景

### 场景1：优化音乐库存储空间
```
原始MP3库 → 使用toOpus转换 → 节省50-70%空间 + 保留所有元数据
不过有损再有损，音质肯定是会更低，但如果从无损音源转到opus，可以替代mp3
```

### 场景2：清理"假无损"文件
```
混合格式库 → 使用flac_wav_detector扫描 → 识别并重命名伪无损文件
```

### 场景3：修复播放器封面问题
```
封面显示异常 → 使用fix_mp3_cover_mime修复 → 所有播放器正常显示
```

### 场景4：筛选高质量音频
```
大型MP3集合 → 使用low_bitrate_detector检测 → 标记低质量文件以便替换
```

---

## ❓ 常见问题

### Q: 为什么需要这些工具？
A: 网上很难找到能**在转换格式时完整保留元数据和封面**的工具，特别是针对个人本地音乐库的轻量级解决方案。这就是创建这个工具集的原因。

### Q: OPUS格式有什么优势？
A: OPUS在相同比特率下音质优于MP3/AAC，且文件更小。128kbps的OPUS音质接近256kbps的MP3，非常适合存储大量音乐。

### Q: 转换后会丢失音质吗？
A: 从有损格式（如MP3）转换不会提升音质，会降低一点现有质量的同时减小文件大小。从无损格式（FLAC/WAV）转换时，建议使用较高比特率（≥192kbps）。

### Q: 这些工具安全吗？
A: 完全安全！所有处理都在本地进行，不会上传任何数据。若不放心可建副本并建小样本测试。

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request！如果你有其他实用的音频管理想法，也欢迎讨论。

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [FFmpeg](https://ffmpeg.org/) - 强大的多媒体框架
- [Mutagen](https://mutagen.readthedocs.io/) - Python音频元数据处理库
- [Lingma](https://lingma.aliyun.com/) - 协助开发和完善代码

---

<div align="center">

**如果这个项目对你有帮助，请给个⭐支持一下！**

</div>

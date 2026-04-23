#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量转换音频文件到OPUS编码器
支持MP3、WAV、FLAC、OGG、M4A等格式，保留封面和元信息，多线程处理
"""

# 需要安装的第三方库:
# 确保系统已安装FFmpeg并添加至PATH中
# pip install mutagen
# pip install psutil # 可选，用于更准确的CPU信息检测

import os
import sys
import subprocess
import threading
import time
from pathlib import Path
from queue import Queue
import queue
from typing import List, Optional, Any
import base64
import json

# 尝试导入mutagen库
try:
    from mutagen.id3 import ID3
    from mutagen.id3._frames import APIC
    from mutagen.oggopus import OggOpus
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC, Picture
    from mutagen.oggvorbis import OggVorbis
    from mutagen.mp4 import MP4
    from mutagen.easyid3 import EasyID3
except ImportError:
    pass

class ProgressBar:
    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self.lock = threading.Lock()
        self.current_file = ""
        self.finished = False
    
    def update(self, increment: int = 1):
        with self.lock:
            if not self.finished:  # 只有在未完成时才更新
                self.current += increment
                self._draw()
    
    def update_current_file(self, filename: str):
        with self.lock:
            if not self.finished:  # 只有在未完成时才更新显示
                self.current_file = filename
                self._draw()
    
    def _draw(self):
        if self.total > 0 and not self.finished:
            # 进度条显示格式: 已处理/总共 百分比 当前文件：xxx.mp3
            percent = (self.current / self.total) * 100
            progress_text = f'{self.current}/{self.total} ({percent:.1f}%) 当前文件：{self.current_file}'
            print(progress_text)
    
    def finish(self):
        with self.lock:
            if not self.finished:
                self.finished = True
                # 完成后换行
                print()


def find_audio_files(folder_path: str) -> List[Path]:
    """查找文件夹内所有支持的音频文件"""
    folder = Path(folder_path)
    audio_files = []
    
    # 支持的音频格式
    supported_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.ape', '.alac'}
    
    for file_path in folder.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            audio_files.append(file_path)
    
    return sorted(audio_files)


def find_single_audio_file(file_path: str) -> List[Path]:
    """处理单个音频文件"""
    path = Path(file_path)
    supported_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.ape', '.alac'}
    if path.is_file() and path.suffix.lower() in supported_extensions:
        return [path]
    return []


def copy_metadata_with_mutagen(input_path: Path, output_path: Path, enable_webp: bool, mutagen_available: bool) -> bool:
    """
    使用mutagen库复制元数据和封面到OPUS文件
    
    Args:
        input_path: 输入音频文件路径
        output_path: 输出OPUS文件路径
        enable_webp: WebP质量参数，None表示不转换，数值表示转换质量
        mutagen_available: mutagen库是否可用
    """
    if not mutagen_available:
        return True  # 如果没有mutagen库，则跳过元数据复制
    
    try:
        # 根据文件类型选择合适的读取方式
        file_ext = input_path.suffix.lower()
        tags_dict: dict[str, Any] = {}
        cover_data = None
        cover_mime = None
        
        if file_ext == '.mp3':
            mp3_file = MP3(input_path, ID3=ID3)
            if not mp3_file.tags:
                print(f" 没有元数据: {input_path.name}")
                return True
            
            try:
                tags_length = len(mp3_file.tags)
                if tags_length == 0:
                    print(f" 元数据为空: {input_path.name}")
                    return True
            except Exception:
                pass
            
            # 提取标签字典
            id3_to_vorbis_mapping = {
                'TIT2': 'TITLE',
                'TPE1': 'ARTIST',
                'TALB': 'ALBUM',
                'TDRC': 'DATE',
                'TRCK': 'TRACKNUMBER',
                'TCON': 'GENRE',
                'TCOM': 'COMPOSER',
                'TPE2': 'ALBUMARTIST',
                'TBPM': 'BPM',
                'TCOP': 'COPYRIGHT',
                'TSSE': 'ENCODER_SETTINGS',
                'TLAN': 'LANGUAGE'
            }
            
            for id3_frame, vorbis_key in id3_to_vorbis_mapping.items():
                if id3_frame in mp3_file:
                    frame = mp3_file[id3_frame]
                    if hasattr(frame, 'text') and frame.text:
                        text_list = []
                        if isinstance(frame.text, list):
                            items = list(frame.text)
                            for item in items:
                                text_list.append(str(item))
                        else:
                            try:
                                if (hasattr(frame.text, '__iter__') and 
                                    not isinstance(frame.text, (str, bytes))):
                                    items = list(frame.text)
                                    for item in items:
                                        text_list.append(str(item))
                                else:
                                    text_list = [str(frame.text)]
                            except Exception:
                                text_list = [str(frame.text)]
                        
                        tags_dict[vorbis_key] = text_list
            
            # 提取封面
            for key, value in mp3_file.items():
                if isinstance(value, APIC):
                    cover_data = value.data
                    cover_mime = value.mime
                    break
                    
        elif file_ext == '.flac':
            flac_file = FLAC(input_path)
            if not flac_file.tags:
                print(f" 没有元数据: {input_path.name}")
                return True
            
            # FLAC直接使用vorbis注释
            tags_dict = dict(flac_file)
            
            # 提取封面
            if flac_file.pictures:
                picture = flac_file.pictures[0]
                cover_data = picture.data
                cover_mime = picture.mime
            
        elif file_ext in ['.ogg']:
            ogg_file = OggVorbis(input_path)
            if not ogg_file.tags:
                print(f" 没有元数据: {input_path.name}")
                return True
            
            tags_dict = dict(ogg_file)
            
        elif file_ext in ['.m4a', '.aac']:
            try:
                mp4_file = MP4(input_path)
                if not mp4_file.tags:
                    print(f" 没有元数据: {input_path.name}")
                    return True
                
                # MP4到Vorbis的映射
                mp4_to_vorbis = {
                    '\xa9nam': 'TITLE',
                    '\xa9ART': 'ARTIST',
                    '\xa9alb': 'ALBUM',
                    '\xa9day': 'DATE',
                    'trkn': 'TRACKNUMBER',
                    '\xa9gen': 'GENRE',
                    '\xa9wrt': 'COMPOSER',
                    '\xa9too': 'ENCODER',
                }
                
                for mp4_key, vorbis_key in mp4_to_vorbis.items():
                    if mp4_key in mp4_file:
                        value: Any = mp4_file[mp4_key]
                        # 处理MP4标签值，确保可迭代
                        if value is not None:
                            if isinstance(value, list):
                                # 构建列表，避免类型推断问题
                                result_list: List[str] = []
                                for item in value:
                                    if item is not None:
                                        result_list.append(str(item))
                                tags_dict[vorbis_key] = result_list
                            else:
                                tags_dict[vorbis_key] = [str(value)]
                # 提取封面
                if 'covr' in mp4_file:
                    cover_data_list = mp4_file['covr']
                    if cover_data_list:
                        cover_data = cover_data_list[0]
                        # 检测MIME类型
                        cover_mime = detect_image_mime(cover_data)
                        if not cover_mime:
                            cover_mime = 'image/jpeg'
                            
            except Exception as e:
                print(f"\n    {input_path.name} M4A/AAC元数据读取失败: {str(e)}")
                return True
        else:
            # 其他格式尝试通用方法
            print(f"\n    {input_path.name} 暂不支持该格式的元数据读取，将跳过元数据复制")
            return True
        
        # 写入元数据到OPUS文件
        opus_file = OggOpus(output_path)
        
        # 复制文本标签
        for key, value in tags_dict.items():
            if value is not None:  # 确保值不为None
                if isinstance(value, list):
                    # 构建列表，避免类型推断问题
                    result_list: List[str] = []
                    for item in value:
                        if item is not None:
                            item_str = str(item)
                            if item_str.strip():
                                result_list.append(item_str)
                    opus_file[key.upper()] = result_list
                else:
                    opus_file[key.upper()] = [str(value)]
        
        # 保存元数据
        opus_file.save()
        
        # 处理封面
        if cover_data:
            original_cover_mime = cover_mime
            
            # 强制检测MIME类型
            detected_mime = detect_image_mime(cover_data)
            
            if detected_mime:
                cover_mime = detected_mime
                if original_cover_mime != cover_mime:
                    print(f"\n    {input_path.name} 检测到的MIME类型: {cover_mime}\n")
            else:
                cover_mime = "image/jpeg"
                print(f"\n    {input_path.name} 无法检测MIME类型，使用默认值: {cover_mime}\n")
            
            # 根据用户设置决定是否转换为WebP
            webp_data = None
            if enable_webp is not None:
                webp_data = convert_image_to_webp(cover_data, enable_webp, input_path.name)
            
            if webp_data:
                cover_data = webp_data
                cover_mime = 'image/webp'
            
            # 创建Picture对象并写入
            picture = Picture()
            picture.data = cover_data
            picture.mime = cover_mime
            picture.type = 3  # Cover (front)
            picture.desc = 'Cover (front)'
            
            opus_file = OggOpus(output_path)
            picture_data = picture.write()
            encoded_data = base64.b64encode(picture_data).decode('ascii')
            opus_file['METADATA_BLOCK_PICTURE'] = [encoded_data]
            opus_file.save()
                
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if "can't sync to mpeg frame" in error_msg or "mpeg frame" in error_msg:
            print(f"\n    文件可能不是有效的MP3文件: {input_path.name}")
            print("    提示: 文件可能是AAC或其他格式但被错误地重命名为.mp3")
            analyze_file_format(input_path)
            return False
        else:
            print(f"\n    元数据复制失败 {input_path.name}: {str(e)}")
            return False


def detect_image_mime(image_data):
    """
    检测图像数据的MIME类型
    
    Args:
        image_data: 图像二进制数据
        
    Returns:
        MIME类型字符串，如果无法识别则返回None
    """
    if len(image_data) < 12:  # 数据太短，无法检测
        return None
    
    # 检查常见的图像格式签名
    signatures = [
        (b'\xFF\xD8\xFF', 'image/jpeg'),
        (b'\x89PNG\r\n\x1a\n', 'image/png'),
        (b'GIF87a', 'image/gif'),
        (b'GIF89a', 'image/gif'),
        (b'RIFF', 'image/webp'),  # RIFF头，需要进一步确认
        (b'BM', 'image/bmp'),
    ]
    
    for signature, mime in signatures:
        if image_data.startswith(signature):
            # 特殊处理WebP，因为它的RIFF容器中应该包含'WEBP'
            if mime == 'image/webp':
                if len(image_data) >= 12 and image_data[8:12] == b'WEBP':
                    return mime
                else:
                    continue  # 不是WebP文件
            return mime
    
    return None


def convert_image_to_webp(image_data, quality=75, filename=None):
    """
    使用FFmpeg将图像数据转换为WebP格式以减小文件大小
    """
    temp_input = None
    temp_output = None
    try:
        # 创建唯一的临时文件名，避免多线程冲突
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        temp_input = Path(f"temp_cover_image_{unique_id}_{os.getpid()}")
        temp_output = Path(f"{temp_input}.webp")
        
        # 写入原始图像数据
        with open(temp_input, "wb") as f:
            f.write(image_data)
        
        # 使用FFmpeg转换为WebP
        cmd = [
            'ffmpeg',
            '-i', str(temp_input),
            '-y',  # 覆盖输出文件
            '-quality', str(quality),  # 设置WebP质量
            '-f', 'webp',  # 指定输出格式
            str(temp_output)
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            check=False
        )
        
        # 读取转换后的WebP数据
        if result.returncode == 0 and temp_output.exists():
            # 检查转换后的文件是否确实更小
            original_size = len(image_data)
            webp_size = temp_output.stat().st_size
            
            # 只有当WebP文件更小时才使用它
            if webp_size < original_size:
                with open(temp_output, "rb") as f:
                    webp_data = f.read()
                return webp_data
            else:
                filename_info = f"({filename})" if filename else ""
                print(f"\n  {filename_info}WebP转换后文件更大，保留原始格式: 原始 {original_size} Bytes vs WebP {webp_size} Bytes\n")
                return None
        else:
            # 转换失败，返回None以使用原始图像
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            if not error_msg:
                error_msg = result.stdout.decode('utf-8', errors='ignore')
            print(f" WebP转换失败: {error_msg[:100]}...")  # 只显示前100个字符
            return None
            
    except Exception as e:
        # 出现异常
        print(f" 图像转换为WebP时出现异常: {str(e)}")
        return None
    finally:
        # 确保清理临时文件
        try:
            if temp_input and temp_input.exists():
                temp_input.unlink()
        except Exception as e:
            print(f" 清理临时输入文件时出错: {str(e)}")
        
        try:
            if temp_output and temp_output.exists():
                temp_output.unlink()
        except Exception as e:
            print(f" 清理临时输出文件时出错: {str(e)}")


def analyze_file_format(file_path: Path):
    """
    使用ffprobe分析文件的实际格式
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(file_path)
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            check=False,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            probe_data = json.loads(result.stdout)
            
            # 提取格式信息
            format_name = probe_data.get('format', {}).get('format_name', '未知')
            format_long_name = probe_data.get('format', {}).get('format_long_name', '未知')
            
            print(f"  可能的实际格式: {format_name} ({format_long_name})")
            
            # 提取流信息
            streams = probe_data.get('streams', [])
            for i, stream in enumerate(streams):
                codec_type = stream.get('codec_type', '未知')
                codec_name = stream.get('codec_name', '未知')
                print(f"  流 {i}: {codec_type} - {codec_name}")
        else:
            print(f"  无法分析文件格式: {result.stderr}")
            
    except FileNotFoundError:
        print("  无法分析文件格式: 系统中未找到ffprobe")
    except Exception as e:
        print(f"  分析文件格式时出错: {str(e)}")


def convert_mp3_to_opus(input_path: Path, output_path: Path, bitrate: int = 128, enable_webp: bool = True, mutagen_available: bool = True) -> bool:
    """
    使用FFmpeg将音频文件转换为OPUS，保留封面和元信息
    
    Args:
        input_path: 输入音频文件路径
        output_path: 输出OPUS文件路径
        bitrate: 目标码率(kbps)
        enable_webp: 是否启用WebP封面转换
        mutagen_available: mutagen库是否可用

    Returns:
        转换是否成功
    """
    try:
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:a', 'libopus',  # 使用libopus编码器
            '-b:a', f'{bitrate}k',  # 用户自定义码率
            '-application', 'audio',  # 音频应用类型
            '-vbr', 'on',  # 动态码率 开启
            '-compression_level', '10',  # 压缩质量 最高10
            '-frame_duration', '20',  # 帧时长
            '-map_metadata', '-1',  # 不复制元数据，稍后用mutagen处理
            '-vn',  # 移除视频，防止播放器误判
            '-y',  # 覆盖输出文件
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            check=False,  # 不在非零返回码时抛出异常
            text=True,    # 以文本模式处理输出
            encoding='utf-8'
        )
        
        # 如果转换失败，打印详细错误信息
        if result.returncode != 0:
            print(f"\n转换失败 {input_path.name}")
            print(f"命令: {' '.join(cmd)}")
            print(f"返回码: {result.returncode}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
            
        # 使用mutagen复制元数据和封面
        if not copy_metadata_with_mutagen(input_path, output_path, enable_webp, mutagen_available):
            print(f"\n元数据复制失败 {input_path.name}\n")
            return False
            
        return result.returncode == 0
    
    except Exception as e:
        print(f"\n转换失败 {input_path.name}: {str(e)}")
        return False


def worker_thread(task_queue: Queue, progress_bar: ProgressBar, results: dict, results_lock: threading.Lock, stop_event: threading.Event, bitrate: int, enable_webp: bool, mutagen_available: bool):
    """工作线程函数"""
    while not stop_event.is_set():
        try:
            # 从队列获取任务，设置超时避免死锁
            input_path, output_path = task_queue.get(timeout=1)
        except queue.Empty:
            # 队列为空或超时，退出线程
            break

        # 显示当前正在转换的文件
        progress_bar.update_current_file(input_path.name)
        success = False
        try:
            success = convert_mp3_to_opus(input_path, output_path, bitrate, enable_webp, mutagen_available)
        finally:
            # 确保无论成功或失败，task_done() 都会被调用
            task_queue.task_done()

        with results_lock:
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['failed_files'].append(input_path.name)

        progress_bar.update(1)


def parse_path(path_str: str) -> str:
    """解析路径，处理Windows拖放时的引号"""
    path_str = path_str.strip()
    
    # 处理PowerShell拖放文件时的格式 & 'path'
    if path_str.startswith("& '") and path_str.endswith("'"):
        path_str = path_str[3:-1]
    
    # 处理普通引号
    if path_str.startswith('"') and path_str.endswith('"'):
        path_str = path_str[1:-1]
        
    return path_str


def get_cpu_info():
    """获取CPU信息"""
    cpu_name = "未知 CPU"
    physical_cores = None
    logical_cores = os.cpu_count() or 1  # 至少为1

    # 尝试使用psutil获取更准确的CPU信息
    try:
        import psutil
        logical_cores = psutil.cpu_count(logical=True) or logical_cores
        physical_cores = psutil.cpu_count(logical=False)

        # 尝试获取CPU型号
        if os.name == 'nt':
            try:
                import platform
                cpu_name = platform.processor()
            except:
                pass
        else:
            # 非Windows系统尝试读取/proc/cpuinfo或使用platform
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            cpu_name = line.split(':')[1].strip()
                            break
            except:
                try:
                    cpu_name = platform.processor()
                except:
                    pass
    except ImportError:
        # psutil未安装，仅使用os和platform
        try:
            import platform
            cpu_name = platform.processor()
            logical_cores = os.cpu_count()
        except:
            pass
        physical_cores = None  # 无法确定
    
    print(f"检测到 CPU: {cpu_name}")
    if physical_cores is None:
        print(f"物理核心数: 无法确定")
    else:
        print(f"物理核心数: {physical_cores}")
    print(f"逻辑核心数: {logical_cores}\n")
    return logical_cores, physical_cores


def check_ffmpeg():
    """检查FFmpeg是否可用"""
    try:
        # 尝试运行ffmpeg命令来检查是否安装
        result = subprocess.run(
            ['ffmpeg', '-version'], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            check=False,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            # 成功执行，提取版本信息
            version_line = result.stdout.split('\n')[0] if result.stdout else "版本信息未知"
            print(f"检测到 FFmpeg: {version_line}")
        else:
            print("FFmpeg不可用: 命令执行失败")
            print(f"错误信息: {result.stderr}")
            print("\n由于缺少必要的FFmpeg环境，程序无法继续运行。")
            input("按回车键退出...")
            sys.exit(1)
            
    except FileNotFoundError:
        print("FFmpeg未安装或未添加到系统PATH中")
        print("请从 https://ffmpeg.org/download.html 下载并安装FFmpeg，并将其添加到系统PATH中")
        print("\n由于缺少必要的FFmpeg环境，程序无法继续运行。")
        input("按回车键退出...")
        sys.exit(1)
    except Exception as e:
        print(f"检查FFmpeg时发生错误: {e}")
        print("\n由于缺少必要的FFmpeg环境，程序无法继续运行。")
        input("按回车键退出...")
        sys.exit(1)


def get_thread_count(logical_cores, physical_cores):
    """获取用户设定的线程数"""
    # 获取线程数，基于检测到的CPU核心数
    # 如果能确定物理核心数，则使用物理核心数作为默认值，否则使用逻辑核心数的一半
    if physical_cores is not None:
        max_suggested_threads = physical_cores  # 物理核心数作为默认值
    else:
        max_suggested_threads = logical_cores // 2  # 建议线程数
    
    while True:
        try:
            thread_input = input(f"请输入线程数(1 ~ {logical_cores})，直接回车使用建议线程数 ({max_suggested_threads}) : ").strip()
            if not thread_input:
                thread_count = max_suggested_threads  # 使用建议值
                print(f"使用建议线程数: {thread_count}\n")
                break
            
            thread_count = int(thread_input)
            if 1 <= thread_count <= logical_cores:
                print(f"使用线程数: {thread_count}\n")
                break
            elif thread_count > logical_cores:
                print(f"线程数不能超过逻辑核心数 {logical_cores}")
            else:
                print("线程数必须大于0")
        except ValueError:
            print("请输入有效的数字(或Ctrl+C退出)\n")
        except KeyboardInterrupt:
            print("\n成功退出")
            sys.exit(1)
            
    return thread_count


def get_bitrate():
    """获取用户设定的码率"""
    # 获取码率设置
    while True:
        try:
            bitrate = 128  # 默认码率
            bitrate_input = input(f"请输入目标码率(64 ~ 512 kbps)，直接回车使用默认码率 ({bitrate} kbps) : ").strip()
            if not bitrate_input:
                print(f"使用默认码率: {bitrate} kbps\n")
                break
            
            bitrate = int(bitrate_input)
            if 64 <= bitrate <= 512:  # OPUS建议码率范围
                print(f"使用码率: {bitrate} kbps\n")
                break
            else:
                print("码率必须在 64~512 kbps之间\n")
        except ValueError:
            print("请输入有效的数字(或Ctrl+C退出)\n")
        except KeyboardInterrupt:
            print("\n成功退出")
            sys.exit(1)
            
    return bitrate


def get_cover_conversion_preference():
    """获取用户对封面格式转换的偏好设置"""
    while True:
        try:
            response = input("若要转换WebP，输入目标WebP质量参数(0 ~ 100)数字越大质量越高，直接回车视为不转换图片格式: ").strip()
            if not response:
                print("禁用封面WebP格式转换，原图输出\n")
                return None
            else:
                quality = int(response)
                if 0 <= quality <= 100:
                    print(f"启用封面WebP格式转换，质量参数: {quality}\n")
                    return quality
                else:
                    print("质量参数必须在0-100之间\n")
        except ValueError:
            print("请输入有效的数字或直接回车\n")
        except KeyboardInterrupt:
            print("\n成功退出")
            sys.exit(1)


def check_mutagen():
    """检查mutagen库是否可用"""
    try:
        # 尝试导入mutagen库
        from mutagen.id3 import ID3
        from mutagen.id3._frames import APIC
        from mutagen.oggopus import OggOpus
        from mutagen.mp3 import MP3
        from mutagen.flac import Picture
        print("检测到 mutagen 库，将使用 mutagen 处理元数据和封面\n")
        return True
    except ImportError:
        print("错误：未检测到mutagen库，无法处理音频元数据和封面\n")
        response = input("是否要自动安装mutagen库?(Y/n): ").strip().lower()
        if response in ['y', 'Y', 'yes', 'Yes', 'YES', '是']:
            try:
                print("正在安装mutagen库...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "mutagen"],
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                # 重新尝试导入
                from mutagen.id3 import ID3
                from mutagen.id3._frames import APIC
                from mutagen.oggopus import OggOpus
                from mutagen.mp3 import MP3
                from mutagen.flac import Picture
                print("mutagen库安装成功！")
                print("检测到 mutagen 库，将使用 mutagen 处理元数据和封面\n")
                return True
            except (subprocess.CalledProcessError, Exception) as e:
                print(f"安装失败: {e}")
                print("请手动安装: pip install mutagen")
        
        # 如果安装失败或用户选择不安装，询问是否继续
        print("\n由于缺少mutagen库，程序将无法处理元数据和封面。")
        response = input("是否继续?(Y/n): ").strip().lower()
        if response not in ['y', 'Y', 'yes', 'Yes', 'YES', '是']:
            sys.exit(1)
        return False


def select_input_path():
    """选择输入文件或文件夹"""
    input_path = ""
    if len(sys.argv) > 1:
        input_path = parse_path(' '.join(sys.argv[1:]))
    else:
        print("转换后的文件将存于源文件夹下的 converted_opus 文件夹中 ")
        while True:
            try:
                input_path = input("请输入音频文件或文件夹路径(或拖放文件/文件夹到此处): ").strip()
                input_path = parse_path(input_path)
                
                # 验证路径
                if os.path.exists(input_path):
                    break
                else:
                    print(f"错误: 路径不存在 -> {input_path}")
                    print("请重新输入路径(或Ctrl+C退出)\n")
            except KeyboardInterrupt:
                print("\n成功退出")
                sys.exit(1)
                
    return input_path


def convert_files(input_path, bitrate, thread_count, enable_webp, mutagen_available):
    """执行文件转换"""
    # 判断是文件还是文件夹，并查找音频文件
    audio_files = []
    output_folder = None
    
    if os.path.isfile(input_path):
        # 如果是文件，检查是否为支持的音频格式
        audio_files = find_single_audio_file(input_path)
        # 输出文件夹设置为文件所在目录下的converted_opus
        output_folder = Path(input_path).parent / "converted_opus"
    else:
        # 如果是文件夹，查找其中的所有音频文件
        print(f"\n正在扫描文件夹: {input_path}")
        audio_files = find_audio_files(input_path)
        # 输出文件夹设置为输入文件夹下的converted_opus
        output_folder = Path(input_path) / "converted_opus"
    
    if not audio_files:
        print("未找到任何支持的音频文件(MP3/WAV/FLAC/OGG/M4A等)")
        return False
    
    print(f"找到 {len(audio_files)} 个音频文件")
    
    # 创建输出文件夹
    output_folder.mkdir(exist_ok=True)
    
    # 使用线程安全的队列
    task_queue = Queue()
    for audio_file in audio_files:
        output_path = output_folder / f"{audio_file.stem}.opus"
        task_queue.put((audio_file, output_path))
    
    # 初始化进度条和结果统计
    progress_bar = ProgressBar(len(audio_files))
    results = {
        'success': 0,
        'failed': 0,
        'failed_files': []
    }
    
    # 创建线程锁以保护结果统计
    results_lock = threading.Lock()
    
    # 创建停止事件，用于控制线程退出
    stop_event = threading.Event()
    
    print(f"\n开始转换，使用码率 {bitrate} kbps，线程数 {thread_count}...")
    
    # 创建并启动工作线程
    threads = []
    for _ in range(thread_count):
        thread = threading.Thread(
            target=worker_thread,
            args=(task_queue, progress_bar, results, results_lock, stop_event, bitrate, enable_webp, mutagen_available)
        )
        threads.append(thread)
        thread.daemon = True  # 设置为守护线程
        thread.start()
    
    # 等待队列中的所有任务完成
    try:
        # 使用更可靠的等待机制，基于队列的未完成任务计数
        # 这样可以确保所有任务都已处理完毕，而不仅仅是队列为空
        while True:
            # 检查是否所有任务都已完成(未完成任务数为0)
            if task_queue.unfinished_tasks == 0:
                break
            time.sleep(0.1)  # 短暂休眠以允许响应键盘中断
            
    except KeyboardInterrupt:
        print("\n\n用户中断转换过程...")
        # 设置停止事件，通知所有线程尽快退出
        stop_event.set()
        sys.exit(1)
    
    # 强制更新进度条到100%
    progress_bar.current = progress_bar.total
    progress_bar.update(0)  # 触发重新绘制但不增加计数
    
    # 完成后换行
    print()
    progress_bar.finish()
    print("=" * 50)
    print("转换完成!")
    print(f"成功: {results['success']} 个文件")
    print(f"失败: {results['failed']} 个文件")
    
    if results['failed_files']:
        print("\n失败的文件:")
        for failed_file in results['failed_files']:
            print(f"  - {failed_file}")
    
    print(f"转换后的文件保存在: {output_folder}")
    print("\n可继续转换，也可Ctrl+C退出")
    return True


def greeting():
    """欢迎信息"""
    print("音频文件到OPUS批量转换器  Ctrl+C可退出")
    print("本程序将使用FFmpeg将音频文件(MP3/WAV/FLAC/OGG/M4A等)转换为OPUS格式")
    print("=" * 50)
    
def main():
    """主函数"""
    # 欢迎信息
    greeting()

    # 检测CPU信息
    logical_cores, physical_cores = get_cpu_info()
    
    # 检测FFmpeg环境
    check_ffmpeg()
    
    # 检查mutagen库
    mutagen_available = check_mutagen()
    
    # 获取线程数
    thread_count = get_thread_count(logical_cores, physical_cores)
    
    # 获取码率
    bitrate = get_bitrate()
    
    # 获取封面转换偏好
    enable_webp = get_cover_conversion_preference()
    
    # 主循环
    while True:
        try:
            # 选择输入路径
            input_path = select_input_path()
            
            # 执行转换
            convert_files(input_path, bitrate, thread_count, enable_webp, mutagen_available)
            
        except KeyboardInterrupt:
            print("\n成功退出")
            sys.exit(0)


if __name__ == "__main__":
    main()
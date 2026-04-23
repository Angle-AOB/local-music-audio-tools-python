#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复MP3文件中嵌入图片的MIME类型信息
支持循环拖入文件或文件夹进行批量处理
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List

try:
    from mutagen.id3 import ID3
    from mutagen.id3._frames import APIC
    from mutagen.mp3 import MP3
except ImportError as e:
    print(f"缺少必要的库: {e}")
    print("请安装mutagen库: pip install mutagen")
    sys.exit(1)


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


def analyze_file_format(file_path: Path):
    """
    使用ffprobe分析文件的实际格式
    
    Args:
        file_path: 文件路径
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
            
            print(f"  实际格式: {format_name} ({format_long_name})")
            
            # 提取流信息
            streams = probe_data.get('streams', [])
            for i, stream in enumerate(streams):
                codec_type = stream.get('codec_type', '未知')
                codec_name = stream.get('codec_name', '未知')
                print(f"  流 {i}: {codec_type} - {codec_name}")
                
            # 判断是否真的是MP3文件
            is_mp3 = 'mp3' in format_name.lower() or any(
                'mp3' in stream.get('codec_name', '').lower() for stream in streams
            )
            
            return is_mp3
        else:
            print(f"  无法分析文件格式: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("  无法分析文件格式: 系统中未找到ffprobe")
        return False
    except Exception as e:
        print(f"  分析文件格式时出错: {str(e)}")
        return False


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


def get_mp3_files(input_path: str) -> List[Path]:
    """
    从输入路径获取所有MP3文件
    
    Args:
        input_path: 输入路径
        
    Returns:
        MP3文件路径列表
    """
    mp3_files = []
    
    path = Path(parse_path(input_path))
    
    if path.is_file() and path.suffix.lower() == '.mp3':
        mp3_files.append(path)
    elif path.is_dir():
        # 递归查找目录中的所有MP3文件
        for mp3_file in path.rglob('*.mp3'):
            mp3_files.append(mp3_file)
                
    return mp3_files


def process_files(input_path: str, auto_fix: bool = False) -> None:
    """
    处理用户输入的文件
    
    Args:
        input_path: 用户输入的路径
        auto_fix: 是否自动修复所有MIME类型错误而无需逐一确认
    """
    # 获取所有MP3文件
    mp3_files = get_mp3_files(input_path)
    
    if not mp3_files:
        print("未找到MP3文件，请检查输入路径")
        return
        
    print(f"\n找到 {len(mp3_files)} 个MP3文件:")
    for i, mp3_file in enumerate(mp3_files, 1):
        print(f"  {i}. {mp3_file.name}")
        
    # 处理每个MP3文件
    success_count = 0
    failed_count = 0
    
    for mp3_file in mp3_files:
        if fix_mp3_cover_mime(mp3_file, auto_fix):
            success_count += 1
        else:
            failed_count += 1
            
    # 输出处理结果统计
    print(f"\n处理完成:")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")


def fix_mp3_cover_mime(mp3_path: Path, auto_fix: bool = False) -> bool:
    """
    修复单个MP3文件的封面MIME类型
    
    Args:
        mp3_path: MP3文件路径
        auto_fix: 是否自动修复所有MIME类型错误而无需逐一确认
        
    Returns:
        是否成功修复
    """
    try:
        # 先用ffprobe检查文件是否真的是MP3文件
        print("-"*30)
        print(f"\n检查文件: {mp3_path.name}")
        if not analyze_file_format(mp3_path):
            print(f"  {mp3_path.name}: 文件格式分析失败或不是有效的MP3文件")
            return False
        
        # 读取MP3文件的ID3标签
        audio_file = MP3(mp3_path)
        if audio_file.tags is None:
            print(f"  {mp3_path.name}: 没有ID3标签")
            return False
            
        # 查找APIC帧（封面图片）
        apic_frames = []
        for key, value in audio_file.tags.items():
            if isinstance(value, APIC):
                apic_frames.append((key, value))
                
        if not apic_frames:
            print(f"  {mp3_path.name}: 没有嵌入封面图片")
            return True  # 不是错误，只是没有封面
            
        # 处理每个APIC帧
        modified = False
        for key, apic_frame in apic_frames:
            original_mime = apic_frame.mime
            detected_mime = detect_image_mime(apic_frame.data)
            
            if detected_mime and detected_mime != original_mime:
                print(f"\n{mp3_path.name}: 封面MIME类型不匹配")
                print(f"  标签中的MIME类型: {original_mime}")
                print(f"  检测到的MIME类型: {detected_mime}")
                
                # 自动修复或询问用户是否修复
                if auto_fix:
                    apic_frame.mime = detected_mime
                    modified = True
                    print(f"  已自动更新MIME类型为: {detected_mime}")
                else:
                    modified = ask_user_for_confirmation(apic_frame, detected_mime, modified)

            elif detected_mime:
                print(f"{mp3_path.name}: 封面MIME类型正确 ({detected_mime})")
            else:
                print(f"{mp3_path.name}: 无法检测封面图片格式")
                
        # 如果有修改，保存文件
        if modified:
            audio_file.save()
            print(f"{mp3_path.name}: 已保存更改")
            
        return True
        
    except Exception as e:
        print(f"{mp3_path.name}: 处理时出错 - {e}")
        return False


def ask_user_for_confirmation(apic_frame, detected_mime, modified):
    while True:
        response = input("  是否更新MIME类型? (N/n取消，默认更新MIME): ").strip().lower()
        
        if response in ['N', 'n', 'NO', 'No', 'no', '否']:
            print("  跳过更新")
            return modified
        else:
            # 更新MIME类型
            apic_frame.mime = detected_mime
            modified = True
            print(f"  已更新MIME类型为: {detected_mime}")
            return modified


def greeting():
    print("MP3封面MIME类型修复工具")
    print("=" * 30)
    print("功能说明:")
    print("  1. 拖放一个或多个MP3文件或包含MP3文件的文件夹到本窗口")
    print("  2. 程序会检测文件中嵌入的封面图片MIME类型")
    print("  3. 如果发现不匹配，会询问是否修复")
    print("=" * 30)


def select_input_path():
    """选择输入文件或文件夹"""
    input_path = ""
    if len(sys.argv) > 1:
        input_path = parse_path(' '.join(sys.argv[1:]))
    else:
        while True:
            try:
                input_path = input("\n请输入或拖放MP3文件或文件夹 (按Ctrl+C退出):").strip()
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


def ask_auto_fix():
    """询问用户是否自动修复所有文件"""
    while True:
        try:
            response = input("\n是否要全部自动修改，无需再次确认？(y/N): ").strip().lower()
            if response in ['y', 'yes', '是']:
                return True
            elif response in ['n', 'no', '否', '']:
                return False
            else:
                print("请输入 y 或 n (默认为 n)")
        except KeyboardInterrupt:
            print("\n成功退出")
            sys.exit(1)


def main():
    """主函数"""
    
    greeting()
    
    # 询问是否自动修复
    auto_fix = ask_auto_fix()
    
    while True:
        try:
            # 选择输入路径
            input_path = select_input_path()
                
            # 处理文件
            process_files(input_path, auto_fix)
            
        except KeyboardInterrupt:
            print("\n\n程序已退出")
            break

if __name__ == "__main__":
    main()
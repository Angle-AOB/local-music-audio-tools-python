#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MP3低码率检测工具
用于检测MP3文件的比特率，当低于300kbps时给出提示

使用方法:
1. 运行程序
2. 拖拽文件或文件夹到程序窗口
3. 程序会自动分析并报告低码率文件
"""

import subprocess
import json
import os
import sys
from pathlib import Path
from typing import List, Union


def analyze_mp3_bitrate(file_path: Union[str, Path]) -> dict:
    """
    使用ffprobe分析MP3文件的比特率
    
    Args:
        file_path: MP3文件路径
        
    Returns:
        dict: 包含分析结果的字典
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return {"error": f"文件 '{file_path}' 不存在"}
    
    # 构建ffprobe命令
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        '-show_format',
        '-select_streams', 'a:0',
        str(file_path)
    ]
    
    try:
        # 执行ffprobe命令
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=30, 
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            # 解析JSON输出
            probe_data = json.loads(result.stdout)
            return probe_data
        else:
            return {"error": f"ffprobe执行失败: {result.stderr}"}
            
    except subprocess.TimeoutExpired:
        return {"error": "ffprobe执行超时"}
    except json.JSONDecodeError:
        return {"error": "无法解析ffprobe输出为JSON"}
    except Exception as e:
        return {"error": f"执行ffprobe时发生错误: {e}"}


def extract_bitrate_info(probe_data: dict) -> dict:
    """
    从ffprobe数据中提取比特率信息
    
    Args:
        probe_data: ffprobe返回的数据
        
    Returns:
        dict: 包含比特率信息的字典
    """
    if "error" in probe_data:
        return probe_data
    
    bitrate_info = {}
    
    # 获取流信息
    if 'streams' in probe_data and len(probe_data['streams']) > 0:
        stream = probe_data['streams'][0]
        bitrate_info['codec_name'] = stream.get('codec_name', 'unknown')
        bitrate_info['bit_rate'] = stream.get('bit_rate')
        
        # 如果流中没有比特率信息，尝试从格式信息中获取
        if not bitrate_info['bit_rate'] and 'format' in probe_data:
            bitrate_info['bit_rate'] = probe_data['format'].get('bit_rate')
    
    # 获取格式信息
    if 'format' in probe_data:
        bitrate_info['format_name'] = probe_data['format'].get('format_name', 'unknown')
    
    return bitrate_info


def check_bitrate_threshold(bit_rate_str: str, threshold: int = 300000) -> tuple:
    """
    检查比特率是否低于阈值
    
    Args:
        bit_rate_str: 比特率字符串
        threshold: 阈值，默认为300000（300kbps）
        
    Returns:
        tuple: (是否低于阈值, 比特率值)
    """
    if not bit_rate_str or bit_rate_str == 'N/A':
        return False, 0
    
    try:
        bit_rate = int(bit_rate_str)
        return bit_rate < threshold, bit_rate
    except (ValueError, TypeError):
        return False, 0


def find_mp3_files(path: Union[str, Path]) -> List[Path]:
    """
    查找指定路径下的所有MP3文件
    
    Args:
        path: 文件或文件夹路径
        
    Returns:
        List[Path]: MP3文件列表
    """
    path_obj = Path(path)
    
    if path_obj.is_file():
        # 单个文件
        if path_obj.suffix.lower() == '.mp3':
            return [path_obj]
        else:
            return []
    elif path_obj.is_dir():
        # 文件夹，递归查找所有MP3文件
        return list(path_obj.rglob("*.mp3"))
    else:
        return []


def clean_path_input(path_str: str) -> str:
    """
    清理拖拽输入的路径字符串
    
    Args:
        path_str: 原始路径字符串
        
    Returns:
        str: 清理后的路径
    """
    # 去除首尾空白字符
    path_str = path_str.strip()
    
    # 处理PowerShell等shell的路径格式 & 'path'
    if path_str.startswith("& "):
        path_str = path_str[2:].strip()
    
    # 去除可能的引号
    if path_str.startswith(("'", '"')) and path_str.endswith(("'", '"')):
        path_str = path_str[1:-1]
    
    return path_str


def main():
    """主函数"""
    print("MP3低码率检测工具")
    print("=" * 50)
    print("请将MP3文件或包含MP3文件的文件夹拖拽到此处，然后按回车键开始检测")
    print("输入 'quit' 或 'exit' 退出程序")
    print()
    
    while True:
        try:
            # 获取用户输入
            user_input = input("请输入文件或文件夹路径: ").strip()
            
            # 检查退出命令
            if user_input.lower() in ['quit', 'exit']:
                print("程序已退出")
                break
            
            # 清理路径输入
            cleaned_path = clean_path_input(user_input)
            
            # 检查路径有效性
            if not cleaned_path:
                print("输入路径为空，请重新输入")
                continue
                
            if not os.path.exists(cleaned_path):
                print(f"路径不存在: {cleaned_path}")
                continue
            
            # 查找MP3文件
            mp3_files = find_mp3_files(cleaned_path)
            
            if not mp3_files:
                print(f"在路径 '{cleaned_path}' 中未找到MP3文件")
                continue
            
            print(f"\n找到 {len(mp3_files)} 个MP3文件，开始检测...")
            print("-" * 50)
            
            low_bitrate_files = []
            
            # 分析每个MP3文件
            for mp3_file in mp3_files:
                print(f"正在分析: {mp3_file.name}")
                
                # 使用ffprobe分析文件
                probe_result = analyze_mp3_bitrate(mp3_file)
                
                # 提取比特率信息
                bitrate_info = extract_bitrate_info(probe_result)
                
                # 检查是否有错误
                if "error" in bitrate_info:
                    print(f"  错误: {bitrate_info['error']}")
                    continue
                
                # 检查编解码器是否为MP3
                if bitrate_info.get('codec_name') != 'mp3':
                    print(f"  警告: 文件不是MP3格式 (实际格式: {bitrate_info.get('codec_name')})")
                    continue
                
                # 检查比特率
                bit_rate_str = bitrate_info.get('bit_rate')
                if bit_rate_str is None:
                    bit_rate_str = 'N/A'
                is_low, bit_rate_value = check_bitrate_threshold(bit_rate_str)
                
                if bit_rate_value > 0:
                    bit_rate_kbps = bit_rate_value // 1000
                    print(f"  比特率: {bit_rate_kbps} kbps")
                    
                    if is_low:
                        print(f"  *** 警告: 检测到低码率文件 (< 300 kbps) ***")
                        low_bitrate_files.append((mp3_file.name, bit_rate_kbps))
                else:
                    print(f"  无法确定比特率")
            
            # 输出总结
            print("\n" + "=" * 50)
            print("检测完成!")
            
            if low_bitrate_files:
                print(f"\n发现 {len(low_bitrate_files)} 个低码率文件:")
                for filename, bitrate in low_bitrate_files:
                    print(f"  {filename}: {bitrate} kbps")
            else:
                print("未发现低于300kbps的MP3文件")
            
            print("\n" + "=" * 50)
            
        except KeyboardInterrupt:
            print("\n\n程序已被用户中断")
            break
        except Exception as e:
            print(f"发生错误: {e}")
            continue


if __name__ == "__main__":
    main()
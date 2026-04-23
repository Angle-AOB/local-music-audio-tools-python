import subprocess
import json
import os
import sys
from pathlib import Path


def analyze_audio_file(file_path):
    """
    使用ffprobe分析音频文件并返回流信息
    
    Args:
        file_path (str): 音频文件路径
        
    Returns:
        dict: 包含流信息的字典，如果出错则返回None
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不存在")
        return None

    # 构建ffprobe命令
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        '-show_format',  # 添加-show_format以获取更多文件信息，包括码率
        '-select_streams', 'a:0',
        file_path
    ]

    try:
        # 执行ffprobe命令，指定编码为utf-8
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8')
        if result.returncode == 0:
            # 解析JSON输出
            probe_data = json.loads(result.stdout)
            return probe_data
        else:
            print(f"ffprobe执行失败: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"错误: ffprobe执行超时")
        return None
    except json.JSONDecodeError:
        print(f"错误: 无法解析ffprobe输出为JSON")
        return None
    except Exception as e:
        print(f"执行ffprobe时发生错误: {e}")
        return None


def detect_lossy_conversion(file_path, stream_info):
    """
    根据流信息判断文件是否可能是从有损格式转换而来
    
    Args:
        file_path (str): 文件路径
        stream_info (dict): ffprobe获取的流信息
        
    Returns:
        tuple: (bool, str, str) 是否可能为有损转换, 详细说明, 实际格式
    """
    if not stream_info or 'streams' not in stream_info or len(stream_info['streams']) == 0:
        return False, "无法获取流信息", ""

    stream = stream_info['streams'][0]
    codec_name = stream.get('codec_name', '').lower()
    sample_rate = stream.get('sample_rate', 0)
    
    # 尝试从streams或format中获取码率信息
    bit_rate = stream.get('bit_rate', 0)
    if not bit_rate and 'format' in stream_info:
        bit_rate = stream_info['format'].get('bit_rate', 0)

    filename = Path(file_path).name.lower()
    actual_format = ""

    # 计算码率（转换为kbps）
    bit_rate_kbps = 0
    if bit_rate and bit_rate != 'N/A':
        try:
            bit_rate_kbps = int(bit_rate) // 1000
        except (ValueError, TypeError):
            pass

    # 简化判断逻辑，主要基于编码名称和码率
    # 检测实际是MP3但后缀不是.mp3的文件
    if codec_name == 'mp3':
        actual_format = "mp3"
        file_extension = Path(file_path).suffix.lower()
        if file_extension != ".mp3":
            return True, f"文件实际是MP3格式，但后缀为{file_extension}", actual_format
        else:
            return False, "MP3文件格式与后缀匹配", ""
    
    # 对于FLAC文件，只检查文件名中是否包含有损格式标识
    elif codec_name == 'flac':
        # 检查文件名中是否包含有损格式标识
        if '320' in filename or '128' in filename or 'mp3' in filename or 'aac' in filename:
            return True, f"FLAC文件名包含有损格式标识，疑似从有损格式转换", ""
            
        return False, "文件看起来是FLAC无损格式", ""

    # 对于WAV文件，只检查文件名标识
    elif codec_name in ['pcm_s16le', 'pcm_s24le', 'pcm_u8', 'pcm_s32le']:
        # 检查文件名标识
        if '320' in filename or '128' in filename or 'mp3' in filename or 'aac' in filename:
            return True, f"WAV文件名包含有损格式标识，疑似从有损格式转换", ""
            
        return False, "文件看起来是WAV无损格式", ""
    
    return False, f"未识别的编码格式: {codec_name}", ""


def process_single_file(file_path, auto_process=False):
    """
    处理单个文件
    
    Args:
        file_path (str): 文件路径
        auto_process (bool): 是否自动处理，无需确认
    """
    print(f"\n正在分析文件: {file_path}")
    print("-" * 50)
    
    # 获取流信息
    stream_info = analyze_audio_file(file_path)
    if not stream_info:
        print("无法分析该文件")
        return

    # 显示基本流信息
    if 'streams' in stream_info and len(stream_info['streams']) > 0:
        stream = stream_info['streams'][0]
        codec_name = stream.get('codec_name', '').lower()
        
        # 尝试从streams或format中获取码率信息
        bit_rate = stream.get('bit_rate', '未知')
        if bit_rate == '未知' and 'format' in stream_info:
            bit_rate = stream_info['format'].get('bit_rate', '未知')
        
        # 转换码率显示格式
        if bit_rate != '未知' and bit_rate != 'N/A':
            try:
                bit_rate_kbps = int(bit_rate) // 1000
                bit_rate_display = f"{bit_rate_kbps} kbps"
            except (ValueError, TypeError):
                bit_rate_display = str(bit_rate)
        else:
            bit_rate_display = str(bit_rate)
            
        print(f"编码格式: {stream.get('codec_name', '未知')}")
        print(f"码率: {bit_rate_display}")
        print(f"采样率: {stream.get('sample_rate', '未知')} Hz")
        
        # 根据不同的音频格式显示正确的位深度信息
        if codec_name == 'flac':
            # FLAC文件使用bits_per_raw_sample显示位深度
            bits_info = stream.get('bits_per_raw_sample', '未知')
            print(f"位深度: {bits_info} 位")
        elif codec_name in ['pcm_s16le', 'pcm_s24le', 'pcm_u8', 'pcm_s32le']:
            # WAV文件使用bits_per_sample显示位深度
            bits_info = stream.get('bits_per_sample', '未知')
            print(f"位深度: {bits_info} 位")
        else:
            # 其他格式尝试显示bits_per_sample，如果没有则显示bits_per_raw_sample
            bits_info = stream.get('bits_per_sample', stream.get('bits_per_raw_sample', '未知'))
            print(f"位深度: {bits_info} 位")
            
        print(f"声道数: {stream.get('channels', '未知')}")
        
        # 检测是否可能为有损转换
        is_lossy_conv, reason, actual_format = detect_lossy_conversion(file_path, stream_info)
        if is_lossy_conv:
            print(f"⚠️  警告: {reason}")
            # 如果检测到实际是MP3格式，则询问用户是否重命名文件
            if actual_format == "mp3":
                rename_to_mp3(file_path, auto_process)
        else:
            print(f"✅ 正常: {reason}")
    else:
        print("文件中没有找到音频流")


def rename_to_mp3(file_path, auto_process=False):
    """
    将文件重命名为.mp3后缀
    
    Args:
        file_path (str): 原文件路径
        auto_process (bool): 是否自动处理，无需确认
    """
    path_obj = Path(file_path)
    new_path = path_obj.with_suffix('.mp3')
    
    # 检查是否已经存在同名的.mp3文件
    if new_path.exists():
        print(f"  文件 '{new_path}' 已存在，跳过重命名")
        return
    
    # 如果是自动处理模式，则直接重命名
    if auto_process:
        try:
            path_obj.rename(new_path)
            print(f"  ✅ 自动重命名: {path_obj.name} -> {new_path.name}")
        except Exception as e:
            print(f"  ❌ 重命名失败: {e}")
        return
    
    # 交互式模式：询问用户是否重命名，默认直接重命名，仅当用户输入'n'或'no'时跳过
    response = input(f"  是否将文件 '{path_obj.name}' 重命名为 '{new_path.name}'? (Y/n): ")
    if response.lower() in ['n', 'no', '否']:
        print(f"  已跳过重命名")
    else:
        try:
            path_obj.rename(new_path)
            print(f"  ✅ 已将文件重命名为: {new_path.name}")
        except Exception as e:
            print(f"  ❌ 重命名失败: {e}")


def process_directory(directory_path, auto_process=False):
    """
    处理目录中的所有FLAC和WAV文件
    
    Args:
        directory_path (str): 目录路径
        auto_process (bool): 是否自动处理，无需确认
    """
    flac_files = list(Path(directory_path).glob("*.flac"))
    wav_files = list(Path(directory_path).glob("*.wav"))
    
    all_files = flac_files + wav_files
    
    if not all_files:
        print(f"在目录 '{directory_path}' 中没有找到FLAC或WAV文件")
        return

    print(f"找到 {len(all_files)} 个音频文件")
    
    for file_path in all_files:
        process_single_file(str(file_path), auto_process)


def clean_path(input_path):
    """
    清理路径字符串，处理PowerShell拖放格式
    
    Args:
        input_path (str): 原始路径字符串
        
    Returns:
        str: 清理后的路径
    """
    # 处理PowerShell拖放时的特殊格式 & 'path'
    if input_path.startswith("& '") and input_path.endswith("'"):
        input_path = input_path[3:-1]  # 移除 & ' 和 '
    elif input_path.startswith("& \"") and input_path.endswith("\""):
        input_path = input_path[3:-1]  # 移除 & " 和 "
    
    # 处理路径中的转义单引号
    input_path = input_path.replace("''", "'")
    
    # 去除首尾空格和引号
    input_path = input_path.strip()
    input_path = input_path.strip('"')
    input_path = input_path.strip("'")
    
    return input_path


def greeting():
    """
    欢迎信息
    """
    print("真假FLAC/WAV格式检测工具")
    print("=" * 50)
    print("使用方法: 将音频文件或文件夹拖放到本程序上即可")
    print("按 Ctrl+C 退出程序")
    print()


def select_input_path():
    """选择输入文件或文件夹"""
    input_path = ""
    if len(sys.argv) > 1:
        # 如果通过命令行参数提供了路径，使用第一个参数
        input_path = clean_path(sys.argv[1])
    else:
        # 交互式获取路径
        while True:
            try:
                input_path = input("\n请输入或拖放FLAC/WAV文件或文件夹 (按Ctrl+C退出): ").strip()
                input_path = clean_path(input_path)
                
                # 验证路径
                if os.path.exists(input_path):
                    break
                else:
                    print(f"错误: 路径不存在 -> {input_path}")
                    print("请重新输入路径(或Ctrl+C退出)\n")
            except KeyboardInterrupt:
                print("\n成功退出")
                sys.exit(0)
                
    return input_path


def process_paths(paths, auto_process=False):
    """
    处理路径列表中的文件或文件夹
    
    Args:
        paths (list): 路径列表
        auto_process (bool): 是否自动处理，无需确认
    """
    for path in paths:
        if os.path.isfile(path):
            # 处理单个文件
            if path.lower().endswith(('.flac', '.wav', '.mp3')):
                process_single_file(path, auto_process)
            else:
                print(f"不支持的文件类型: {path}")
        elif os.path.isdir(path):
            # 处理整个目录
            process_directory(path, auto_process)
        else:
            print(f"路径 '{path}' 不存在")


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
    """
    主函数
    """
    greeting()
    
    # 询问是否自动处理
    auto_process = ask_auto_fix()
    
    try:
        while True:
            # 获取拖放的文件或文件夹路径
            paths = [select_input_path()]
            
            # 处理路径
            process_paths(paths, auto_process)
            
            # 如果是通过命令行参数运行的（拖放），处理完后退出循环
            if len(sys.argv) > 1:
                break
                
            # 添加分隔线以便更好地查看结果
            print("\n" + "=" * 50 + "\n")
            
    except KeyboardInterrupt:
        print("\n\n程序已退出")
        sys.exit(0)


if __name__ == "__main__":
    main()
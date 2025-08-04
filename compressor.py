#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emoji压缩转换工具
功能：将origins目录中的图片转换为高效的AVIF格式，并调整到指定尺寸
支持格式：PNG, JPG, WebP (自动检测实际格式)
输出格式：AVIF (优先) 或 WebP (降级)
"""

import os
import json
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime

class EmojiCompressor:
    def __init__(self, input_dir="origins", output_dir="output",
                 target_size=60, quality=50, verbose=True):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.target_size = target_size
        self.quality = quality
        self.verbose = verbose

        # 平台目录映射
        self.platform_mapping = {
            '贴吧': 'tieba',
            '知乎': 'zhihu',
            '小红书': 'xiaohongshu',
            '抖音': 'douyin',
            'B站': 'bilibili'
        }

        # 检查并初始化工具
        self.available_tools = self._check_tools()

    def _print(self, message, force=False):
        """条件打印"""
        if self.verbose or force:
            print(message)

    def _check_tools(self):
        """检查可用的转换工具"""
        tools = {
            'avifenc': shutil.which('avifenc'),
            'avifdec': shutil.which('avifdec'),
            'dwebp': shutil.which('dwebp'),
            'cwebp': shutil.which('cwebp'),
            'sips': shutil.which('sips'),
            'convert': shutil.which('convert'),
            'magick': shutil.which('magick')
        }

        available = []
        for tool, path in tools.items():
            if path:
                available.append(tool)
                self._print(f"✅ 找到 {tool}: {path}")
            else:
                self._print(f"❌ 未找到 {tool}")

        return available

    def _detect_image_format(self, file_path):
        """检测文件的实际格式"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)

                # WebP格式检测
                if header.startswith(b'RIFF') and b'WEBP' in header:
                    return 'webp'
                # PNG格式检测
                elif header.startswith(b'\x89PNG\r\n\x1a\n'):
                    return 'png'
                # JPEG格式检测
                elif header.startswith(b'\xff\xd8\xff'):
                    return 'jpeg'
                # AVIF格式检测
                elif b'ftyp' in header and b'avif' in header:
                    return 'avif'
                else:
                    return 'unknown'
        except:
            return 'unknown'

    def _resize_with_sips(self, input_file, output_file, size):
        """使用macOS sips调整图片尺寸"""
        try:
            cmd = ['sips', '-Z', str(size), input_file, '--out', output_file]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def _resize_with_imagemagick(self, input_file, output_file, size):
        """使用ImageMagick调整图片尺寸"""
        tools_to_try = ['convert', 'magick']

        for tool in tools_to_try:
            if tool in self.available_tools:
                try:
                    if tool == 'convert':
                        cmd = ['convert', input_file, '-resize', f'{size}x{size}', output_file]
                    else:  # magick
                        cmd = ['magick', input_file, '-resize', f'{size}x{size}', output_file]

                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        return True
                except:
                    continue
        return False

    def _convert_webp_to_png(self, webp_file, png_file):
        """使用dwebp将WebP转换为PNG"""
        if 'dwebp' not in self.available_tools:
            return False

        try:
            cmd = ['dwebp', webp_file, '-o', png_file]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def _convert_avif_to_png(self, avif_file, png_file):
        """使用avifdec将AVIF转换为PNG"""
        if 'avifdec' not in self.available_tools:
            return False

        try:
            cmd = ['avifdec', avif_file, png_file]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def _convert_png_to_avif(self, png_file, avif_file):
        """使用avifenc将PNG转换为AVIF"""
        if 'avifenc' not in self.available_tools:
            return False

        try:
            cmd = [
                'avifenc',
                '-q', str(self.quality),
                '-s', '6',
                png_file,
                avif_file
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def _convert_png_to_webp(self, png_file, webp_file):
        """使用cwebp将PNG转换为WebP"""
        if 'cwebp' not in self.available_tools:
            return False

        try:
            cmd = [
                'cwebp',
                '-q', str(min(self.quality + 30, 100)),  # WebP使用更高质量
                '-m', '6',
                png_file,
                '-o', webp_file
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def _process_single_file(self, input_file, output_file, target_format='avif'):
        """处理单个文件的完整流程"""
        input_path = Path(input_file)
        output_path = Path(output_file)

        # 检测原始格式
        original_format = self._detect_image_format(input_file)

        # 创建输出目录
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 临时文件路径
        temp_png_original = str(input_path) + '.temp_orig.png'
        temp_png_resized = str(input_path) + '.temp_resized.png'

        try:
            # 第一步：转换为PNG（如果需要）
            if original_format == 'png':
                temp_png_original = str(input_file)  # 直接使用原文件
            elif original_format == 'webp':
                if not self._convert_webp_to_png(input_file, temp_png_original):
                    self._print(f"    ❌ WebP -> PNG 转换失败")
                    return False, 0, 0
                self._print(f"    ✅ WebP -> PNG 转换成功")
            elif original_format == 'avif':
                if not self._convert_avif_to_png(input_file, temp_png_original):
                    self._print(f"    ❌ AVIF -> PNG 转换失败")
                    return False, 0, 0
                self._print(f"    ✅ AVIF -> PNG 转换成功")
            elif original_format in ['jpeg', 'jpg']:
                # JPEG直接复制为PNG处理
                shutil.copy2(input_file, temp_png_original)
            else:
                self._print(f"    ❌ 不支持的格式: {original_format}")
                return False, 0, 0

            # 第二步：调整尺寸
            resize_success = False

            # 尝试sips (macOS)
            if 'sips' in self.available_tools:
                resize_success = self._resize_with_sips(temp_png_original, temp_png_resized, self.target_size)
                if resize_success:
                    self._print(f"    ✅ 尺寸调整成功 (sips) -> {self.target_size}x{self.target_size}")

            # 尝试ImageMagick
            if not resize_success:
                resize_success = self._resize_with_imagemagick(temp_png_original, temp_png_resized, self.target_size)
                if resize_success:
                    self._print(f"    ✅ 尺寸调整成功 (ImageMagick) -> {self.target_size}x{self.target_size}")

            if not resize_success:
                # 如果调整尺寸失败，直接使用原PNG
                temp_png_resized = temp_png_original
                self._print(f"    ⚠️ 尺寸调整失败，使用原始尺寸")

            # 第三步：转换为目标格式
            conversion_success = False
            actual_output_format = ""

            if target_format == 'avif' and 'avifenc' in self.available_tools:
                # 优先转换为AVIF
                avif_output = str(output_path).replace('.webp', '.avif')
                if not avif_output.endswith('.avif'):
                    avif_output = str(output_path.with_suffix('.avif'))

                conversion_success = self._convert_png_to_avif(temp_png_resized, avif_output)
                if conversion_success:
                    actual_output_format = "AVIF"
                    actual_output_file = avif_output
                    self._print(f"    ✅ PNG -> AVIF 转换成功")

            if not conversion_success and 'cwebp' in self.available_tools:
                # 降级到WebP
                webp_output = str(output_path).replace('.avif', '.webp')
                if not webp_output.endswith('.webp'):
                    webp_output = str(output_path.with_suffix('.webp'))

                conversion_success = self._convert_png_to_webp(temp_png_resized, webp_output)
                if conversion_success:
                    actual_output_format = "WebP"
                    actual_output_file = webp_output
                    self._print(f"    ✅ PNG -> WebP 转换成功")

            if not conversion_success:
                self._print(f"    ❌ 格式转换失败")
                return False, 0, 0

            # 获取文件大小
            original_size = os.path.getsize(input_file)
            new_size = os.path.getsize(actual_output_file) if os.path.exists(actual_output_file) else 0

            return True, original_size, new_size, actual_output_format, actual_output_file

        finally:
            # 清理临时文件
            for temp_file in [temp_png_original, temp_png_resized]:
                if temp_file != str(input_file) and os.path.exists(temp_file):
                    os.remove(temp_file)

    def _process_platform_directory(self, platform_name, platform_dir):
        """处理单个平台目录"""
        input_platform_dir = Path(self.input_dir) / platform_name
        output_platform_dir = Path(self.output_dir) / platform_dir

        if not input_platform_dir.exists():
            self._print(f"⚠️ 平台目录不存在: {input_platform_dir}")
            return []

        # 找到所有图片文件
        image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.avif', '.gif']
        image_files = []

        for ext in image_extensions:
            image_files.extend(input_platform_dir.glob(f'*{ext}'))
            image_files.extend(input_platform_dir.glob(f'*{ext.upper()}'))

        if not image_files:
            self._print(f"⚠️ {platform_name} 目录中没有图片文件")
            return []

        self._print(f"📁 处理 {platform_name} ({len(image_files)} 个文件 -> {self.target_size}×{self.target_size})")

        results = []
        success_count = 0
        total_original_size = 0
        total_new_size = 0
        format_counts = {}

        for image_file in image_files:
            self._print(f"\n🔄 处理: {image_file.name}")

            # 生成输出文件路径
            output_file = output_platform_dir / (image_file.stem + '.avif')

            # 处理文件
            result = self._process_single_file(str(image_file), str(output_file))

            if result[0]:  # 成功
                success_count += 1
                original_size = result[1]
                new_size = result[2]
                output_format = result[3]
                actual_output_file = result[4]

                total_original_size += original_size
                total_new_size += new_size

                compression_ratio = (original_size - new_size) / original_size * 100 if original_size > 0 else 0
                format_counts[output_format] = format_counts.get(output_format, 0) + 1

                file_result = {
                    'original_file': str(image_file.name),
                    'new_file': os.path.basename(actual_output_file),
                    'output_format': output_format,
                    'original_size': original_size,
                    'new_size': new_size,
                    'compression_ratio': compression_ratio,
                    'target_size': f"{self.target_size}×{self.target_size}",
                    'success': True
                }

                self._print(f"    📊 {original_size} -> {new_size} bytes ({output_format}, 压缩率: {compression_ratio:.1f}%)")
            else:
                file_result = {
                    'original_file': str(image_file.name),
                    'success': False
                }
                self._print(f"    ❌ 处理失败")

            results.append(file_result)

        # 平台处理总结
        if success_count > 0:
            overall_compression = (total_original_size - total_new_size) / total_original_size * 100 if total_original_size > 0 else 0
            space_saved = (total_original_size - total_new_size) / 1024
            format_summary = ", ".join([f"{fmt}:{count}" for fmt, count in format_counts.items()])

            self._print(f"\n📊 {platform_name} 处理完成:")
            self._print(f"  成功处理: {success_count}/{len(image_files)} 个文件")
            self._print(f"  原始大小: {total_original_size/1024:.1f} KB")
            self._print(f"  处理后大小: {total_new_size/1024:.1f} KB")
            self._print(f"  整体压缩率: {overall_compression:.1f}%")
            self._print(f"  节省空间: {space_saved:.1f} KB")
            self._print(f"  输出格式: {format_summary}")

        return results

    def compress_all(self):
        """压缩所有平台的emoji"""
        self._print("🚀 Emoji压缩转换工具启动", force=True)
        self._print("=" * 70, force=True)

        # 检查必要工具
        if not self.available_tools:
            self._print("❌ 没有找到任何可用的转换工具", force=True)
            self._print("请安装以下工具之一:", force=True)
            self._print("  - libavif: brew install libavif", force=True)
            self._print("  - webp: brew install webp", force=True)
            self._print("  - ImageMagick: brew install imagemagick (可选)", force=True)
            return None

        self._print(f"🔧 配置信息:", force=True)
        self._print(f"  输入目录: {self.input_dir}", force=True)
        self._print(f"  输出目录: {self.output_dir}", force=True)
        self._print(f"  目标尺寸: {self.target_size}×{self.target_size}", force=True)
        self._print(f"  质量设置: {self.quality}", force=True)
        self._print(f"  可用工具: {', '.join(self.available_tools)}", force=True)

        # 处理所有平台
        all_results = {}

        for platform_name, platform_dir in self.platform_mapping.items():
            self._print(f"\n{'='*70}", force=True)
            results = self._process_platform_directory(platform_name, platform_dir)
            if results:
                all_results[platform_name] = results

        # 生成总体报告
        self._generate_final_report(all_results)

        return all_results

    def _generate_final_report(self, all_results):
        """生成最终报告"""
        if not all_results:
            self._print("\n❌ 没有处理任何文件", force=True)
            return

        total_files = 0
        successful_files = 0
        total_original_size = 0
        total_new_size = 0
        format_counts = {}

        platform_stats = {}

        for platform, results in all_results.items():
            success_count = sum(1 for r in results if r.get('success', False))
            total_count = len(results)

            platform_original_size = sum(r.get('original_size', 0) for r in results if r.get('success', False))
            platform_new_size = sum(r.get('new_size', 0) for r in results if r.get('success', False))

            # 统计格式
            platform_formats = {}
            for r in results:
                if r.get('success', False):
                    fmt = r.get('output_format', 'unknown')
                    platform_formats[fmt] = platform_formats.get(fmt, 0) + 1
                    format_counts[fmt] = format_counts.get(fmt, 0) + 1

            platform_stats[platform] = {
                'total_files': total_count,
                'successful_files': success_count,
                'original_size': platform_original_size,
                'new_size': platform_new_size,
                'compression_ratio': (platform_original_size - platform_new_size) / platform_original_size * 100 if platform_original_size > 0 else 0,
                'formats': platform_formats
            }

            total_files += total_count
            successful_files += success_count
            total_original_size += platform_original_size
            total_new_size += platform_new_size

        overall_compression = (total_original_size - total_new_size) / total_original_size * 100 if total_original_size > 0 else 0

        # 打印最终报告
        self._print(f"\n{'='*70}", force=True)
        self._print("📊 压缩转换完成报告", force=True)
        self._print(f"{'='*70}", force=True)

        self._print(f"🎯 总体统计:", force=True)
        self._print(f"  总文件数: {total_files}", force=True)
        self._print(f"  成功转换: {successful_files}", force=True)
        self._print(f"  成功率: {successful_files/total_files*100:.1f}%" if total_files > 0 else "  成功率: 0%", force=True)
        self._print(f"  目标尺寸: {self.target_size}×{self.target_size}", force=True)

        self._print(f"\n📊 输出格式统计:", force=True)
        for fmt, count in format_counts.items():
            self._print(f"  {fmt}: {count} 个文件", force=True)

        self._print(f"\n💾 存储效果:", force=True)
        self._print(f"  原始大小: {total_original_size/1024:.1f} KB", force=True)
        self._print(f"  压缩后大小: {total_new_size/1024:.1f} KB", force=True)
        self._print(f"  节省空间: {(total_original_size-total_new_size)/1024:.1f} KB", force=True)
        self._print(f"  整体压缩率: {overall_compression:.1f}%", force=True)

        self._print(f"\n📊 各平台详情:", force=True)
        self._print(f"{'平台':<8} {'成功/总数':<10} {'压缩率':<8} {'主要格式':<10} {'节省空间':<12}", force=True)
        self._print("-" * 65, force=True)

        for platform, stats in platform_stats.items():
            saved_space = (stats['original_size'] - stats['new_size']) / 1024
            main_format = max(stats['formats'].items(), key=lambda x: x[1])[0] if stats['formats'] else "N/A"
            self._print(f"{platform:<8} {stats['successful_files']}/{stats['total_files']:<9} "
                       f"{stats['compression_ratio']:.1f}%{'':<4} {main_format:<10} {saved_space:.1f} KB", force=True)

        # 保存详细报告
        self._save_report_to_file(all_results, platform_stats, {
            'total_files': total_files,
            'successful_files': successful_files,
            'total_original_size': total_original_size,
            'total_new_size': total_new_size,
            'overall_compression_ratio': overall_compression,
            'format_distribution': format_counts,
            'target_size': f"{self.target_size}×{self.target_size}",
            'quality': self.quality
        })

        self._print(f"\n📁 压缩文件保存在: {self.output_dir}/", force=True)

    def _save_report_to_file(self, all_results, platform_stats, summary):
        """保存详细报告到文件"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'input_directory': self.input_dir,
                'output_directory': self.output_dir,
                'target_size': f"{self.target_size}×{self.target_size}",
                'quality': self.quality,
                'available_tools': self.available_tools
            },
            'summary': summary,
            'platforms': platform_stats,
            'detailed_results': all_results
        }

        report_filename = f'emoji_compression_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        self._print(f"💾 详细报告已保存到: {report_filename}", force=True)


def main():
    parser = argparse.ArgumentParser(description='Emoji压缩转换工具')
    parser.add_argument('--input', '-i', default='origins',
                       help='输入目录 (默认: origins)')
    parser.add_argument('--output', '-o', default='output',
                       help='输出目录 (默认: output)')
    parser.add_argument('--size', '-s', type=int, default=60,
                       help='目标尺寸 (默认: 60)')
    parser.add_argument('--quality', '-q', type=int, default=50,
                       help='压缩质量 0-100 (默认: 50)')
    parser.add_argument('--quiet', action='store_true',
                       help='静默模式，只显示关键信息')

    args = parser.parse_args()

    # 创建压缩器实例
    compressor = EmojiCompressor(
        input_dir=args.input,
        output_dir=args.output,
        target_size=args.size,
        quality=args.quality,
        verbose=not args.quiet
    )

    # 执行压缩
    results = compressor.compress_all()

    if results:
        print(f"\n🎉 压缩完成! 所有emoji已转换为{args.size}×{args.size}的高效格式!")
    else:
        print("\n❌ 压缩失败，请检查工具安装和输入目录")


if __name__ == "__main__":
    main()
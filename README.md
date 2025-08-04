# Emoji Compressor 使用说明

## 功能概述

`compressor.py` 是一个综合性的表情包压缩工具，整合了整个项目中所有学到的图片处理技术。

## 主要特性

- 支持多种图片格式：PNG, JPG, WebP, AVIF
- 智能格式检测和转换
- 可配置的压缩尺寸和质量
- 多工具支持与回退机制（avifenc, sips, PIL 等）
- 透明度保持（特别针对 WebP 格式）
- 详细的统计报告

## 基本使用

### 默认压缩（60x60 像素）

```bash
python compressor.py
```

### 自定义参数

```bash
python compressor.py --input origins --output output --size 80 --quality 60
```

### 参数说明

- `--input`: 输入目录（默认：origins）
- `--output`: 输出目录（默认：output）
- `--size`: 目标尺寸（默认：60 像素）
- `--quality`: 压缩质量（默认：50）
- `--verbose`: 显示详细处理信息

## 处理流程

1. **格式检测**: 自动识别 PNG、JPG、WebP、AVIF 等格式
2. **透明度处理**: WebP 文件通过 dwebp->PNG->AVIF 管道保持透明度
3. **尺寸优化**: AVIF 文件通过 avifdec->sips->avifenc 管道调整尺寸
4. **质量压缩**: 所有文件统一压缩到指定质量和尺寸
5. **统计报告**: 提供详细的压缩前后对比数据

## 技术要求

- Python 3.6+
- macOS 系统（使用 sips 工具）
- 已安装的工具：
  - avifenc/avifdec（libavif 包）
  - dwebp（webp 包）
  - sips（macOS 内置）

## 安装依赖

```bash
# 安装libavif
brew install libavif

# 安装webp工具
brew install webp
```

## 示例结果

处理完成后会显示类似以下的统计信息：

```
=== 压缩统计报告 ===
总文件数: 245
成功压缩: 245
失败: 0
原始总大小: 15.2 MB
压缩后总大小: 3.8 MB
压缩比: 75.0%
平均文件大小: 15.5 KB
```

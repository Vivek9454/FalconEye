#!/usr/bin/env python3
"""
FalconEye Asset Export Script
Exports SVG assets to various PNG sizes for different use cases
"""

import os
import subprocess
import sys
from pathlib import Path

# Asset sizes for different use cases
SIZES = {
    'favicon': [16, 32, 48],
    'app_icon': [57, 60, 72, 76, 96, 114, 120, 144, 152, 180, 192],
    'logo': [100, 200, 400, 800],
    'icon': [64, 128, 256, 512]
}

def check_dependencies():
    """Check if required tools are installed"""
    try:
        subprocess.run(['which', 'rsvg-convert'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        print("❌ rsvg-convert not found. Please install librsvg2-bin:")
        print("   Ubuntu/Debian: sudo apt-get install librsvg2-bin")
        print("   macOS: brew install librsvg")
        print("   Or use: pip install cairosvg")
        return False

def export_svg_to_png(svg_path, output_dir, sizes, prefix=""):
    """Export SVG to PNG at various sizes"""
    svg_file = Path(svg_path)
    if not svg_file.exists():
        print(f"❌ SVG file not found: {svg_path}")
        return False
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = svg_file.stem
    if prefix:
        base_name = f"{prefix}_{base_name}"
    
    success_count = 0
    for size in sizes:
        output_file = output_dir / f"{base_name}_{size}x{size}.png"
        
        try:
            # Try rsvg-convert first
            cmd = [
                'rsvg-convert',
                '--width', str(size),
                '--height', str(size),
                '--format', 'png',
                '--output', str(output_file),
                str(svg_file)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✅ Created {output_file}")
            success_count += 1
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                # Fallback to cairosvg
                import cairosvg
                cairosvg.svg2png(
                    url=str(svg_file),
                    write_to=str(output_file),
                    output_width=size,
                    output_height=size
                )
                print(f"✅ Created {output_file} (via cairosvg)")
                success_count += 1
            except ImportError:
                print(f"❌ Failed to create {output_file} - install cairosvg: pip install cairosvg")
            except Exception as e:
                print(f"❌ Error creating {output_file}: {e}")
    
    return success_count > 0

def main():
    """Main export function"""
    print("🎨 FalconEye Asset Export Script")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        print("\n💡 Alternative: Install cairosvg for Python-based conversion")
        try:
            import cairosvg
            print("✅ cairosvg found - will use Python conversion")
        except ImportError:
            print("❌ Neither rsvg-convert nor cairosvg available")
            sys.exit(1)
    
    # Set up paths
    assets_dir = Path(__file__).parent
    output_dir = assets_dir / "png"
    
    print(f"\n📁 Assets directory: {assets_dir}")
    print(f"📁 Output directory: {output_dir}")
    
    # Export logo
    print("\n🖼️  Exporting logo...")
    logo_svg = assets_dir / "falconeye-logo.svg"
    if logo_svg.exists():
        export_svg_to_png(logo_svg, output_dir, SIZES['logo'], "logo")
    else:
        print("❌ Logo SVG not found")
    
    # Export icon
    print("\n🔲 Exporting icon...")
    icon_svg = assets_dir / "falconeye-icon.svg"
    if icon_svg.exists():
        export_svg_to_png(icon_svg, output_dir, SIZES['icon'], "icon")
        export_svg_to_png(icon_svg, output_dir, SIZES['favicon'], "favicon")
        export_svg_to_png(icon_svg, output_dir, SIZES['app_icon'], "app")
    else:
        print("❌ Icon SVG not found")
    
    print("\n✨ Export complete!")
    print(f"📁 Check output in: {output_dir}")
    
    # List created files
    if output_dir.exists():
        png_files = list(output_dir.glob("*.png"))
        if png_files:
            print(f"\n📋 Created {len(png_files)} PNG files:")
            for png_file in sorted(png_files):
                print(f"   {png_file.name}")

if __name__ == "__main__":
    main()

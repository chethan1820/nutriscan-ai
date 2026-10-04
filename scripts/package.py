#!/usr/bin/env python3
"""
Package the AI Food Health Monitoring System into a ZIP archive.

Usage:
    python scripts/package.py
    python scripts/package.py --output my_project.zip
"""

import os
import sys
import zipfile
import argparse
from pathlib import Path
from datetime import datetime

# Files and directories to EXCLUDE
EXCLUDE_PATTERNS = {
    '__pycache__', '.pyc', '.pyo', '.pyd',
    'venv', '.venv', 'env',
    '.env',          # Exclude actual .env (keep .env.example)
    '.git', '.gitignore',
    'node_modules',
    '*.log',
    'uploads',       # Don't package user uploads
    'checkpoints',   # Large training checkpoints
    '*.tar.gz',      # Raw dataset archives
    '.DS_Store',
    'Thumbs.db',
    '*.egg-info',
    'dist', 'build',
    'food_health.db',  # SQLite DB
    '*.pth',         # Model weights (too large; user downloads separately)
}


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded from the ZIP."""
    parts = set(path.parts)
    name = path.name

    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith('*'):
            # Extension match
            if name.endswith(pattern[1:]):
                return True
        elif pattern in parts or name == pattern:
            return True
    return False


def package_project(root_dir: Path, output_path: Path):
    """Create a ZIP archive of the project."""
    print(f"📦 Packaging NutriScan AI from: {root_dir}")
    print(f"📁 Output: {output_path}")

    included = []
    skipped = []

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file_path in sorted(root_dir.rglob('*')):
            if not file_path.is_file():
                continue

            relative = file_path.relative_to(root_dir.parent)

            if should_exclude(relative):
                skipped.append(str(relative))
                continue

            arcname = str(relative)
            zf.write(file_path, arcname)
            included.append(arcname)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ Package created successfully!")
    print(f"   Files included: {len(included)}")
    print(f"   Files skipped:  {len(skipped)}")
    print(f"   Archive size:   {size_mb:.2f} MB")
    print(f"   Location:       {output_path.absolute()}")

    print(f"\n📋 Included files:")
    for f in included:
        print(f"   {f}")


def main():
    parser = argparse.ArgumentParser(description="Package NutriScan AI project")
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=f"nutriscan_ai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        help='Output ZIP filename'
    )
    parser.add_argument(
        '--root',
        type=str,
        default=None,
        help='Root directory of the project (default: parent of this script)'
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    root_dir = Path(args.root) if args.root else script_dir.parent
    output_path = Path(args.output)

    if not root_dir.exists():
        print(f"❌ Project directory not found: {root_dir}")
        sys.exit(1)

    package_project(root_dir, output_path)


if __name__ == '__main__':
    main()

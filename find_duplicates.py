#!/usr/bin/env python3
import os
import sys
import hashlib
from pathlib import Path
from collections import defaultdict
import argparse
from typing import Dict, List, Set, Tuple


def calculate_md5(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate MD5 hash of file content."""
    md5_hash = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except (OSError, IOError) as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return ""


def scan_directory(directory: Path, min_size: int = 1024) -> Dict[str, List[Path]]:
    """Scan directory for files and group by hash."""
    hash_groups = defaultdict(list)
    file_count = 0
    skipped_count = 0

    print(f"Scanning {directory}...")

    for root, dirs, files in os.walk(directory):
        for filename in files:
            file_path = Path(root) / filename
            file_count += 1

            # Show progress
            if file_count % 100 == 0:
                print(f"  Processed {file_count} files...")

            try:
                # Skip files smaller than min_size
                if file_path.stat().st_size < min_size:
                    skipped_count += 1
                    continue

                # Calculate hash
                file_hash = calculate_md5(file_path)
                if file_hash:
                    hash_groups[file_hash].append(file_path)

            except (OSError, IOError) as e:
                print(f"Error accessing {file_path}: {e}", file=sys.stderr)
                continue

    print(f"Scan complete: {file_count} files processed, {skipped_count} skipped (too small)")
    return hash_groups


def find_duplicates(hash_groups: Dict[str, List[Path]]) -> Dict[str, List[Path]]:
    """Extract only groups with duplicates."""
    return {h: paths for h, paths in hash_groups.items() if len(paths) > 1}


def format_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def report_duplicates(duplicates: Dict[str, List[Path]]) -> None:
    """Report duplicate files in a clear format."""
    if not duplicates:
        print("No duplicate files found.")
        return

    total_duplicates = sum(len(paths) - 1 for paths in duplicates.values())
    total_wasted = 0

    print(f"\nFound {len(duplicates)} groups of duplicates ({total_duplicates} duplicate files):")
    print("=" * 70)

    for i, (file_hash, paths) in enumerate(sorted(duplicates.items(),
                                                key=lambda x: len(x[1]),
                                                reverse=True), 1):
        try:
            file_size = paths[0].stat().st_size
            wasted = file_size * (len(paths) - 1)
            total_wasted += wasted

            print(f"\n{i}. Duplicate group ({len(paths)} files, {format_size(file_size)} each):")
            print(f"   Hash: {file_hash[:12]}...")
            print(f"   Wasted space: {format_size(wasted)}")

            for j, path in enumerate(sorted(paths), 1):
                print(f"   {j}. {path}")

        except (OSError, IOError) as e:
            print(f"   Error getting file info: {e}", file=sys.stderr)

    print("\n" + "=" * 70)
    print(f"Total wasted space: {format_size(total_wasted)}")


def main():
    parser = argparse.ArgumentParser(
        description="Find duplicate files in a directory based on content hash",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/directory
  %(prog)s --min-size 2048 /path/to/directory
  %(prog)s --hash sha256 /path/to/directory
        """
    )

    parser.add_argument('directory',
                       help='Directory to scan for duplicates')
    parser.add_argument('--min-size', type=int, default=1024,
                       help='Minimum file size in bytes to check (default: 1024)')
    parser.add_argument('--hash', choices=['md5', 'sha1', 'sha256'],
                       default='md5',
                       help='Hash algorithm to use (default: md5)')

    args = parser.parse_args()

    # Validate directory
    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory", file=sys.stderr)
        sys.exit(1)

    try:
        # Scan directory
        hash_groups = scan_directory(directory, args.min_size)

        # Find duplicates
        duplicates = find_duplicates(hash_groups)

        # Report results
        report_duplicates(duplicates)

    except KeyboardInterrupt:
        print("\nScan interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""File Organizer"""

import os
import shutil
import json
import re
from pathlib import Path

def get_category(filename):
    """Determine file category based on filename patterns."""
    
    # Skip script files and binaries
    if filename.endswith(('.py', '.bat', '.txt', '.exe', '.sh')) or filename in ['python']:
        return None
    
    # Video files (priority 1: ALL videos to videos)
    if filename.endswith(('.mp4', '.MP4', '.webm', '.WEBM', '.mov', '.MOV', '.avi', '.AVI', '.mkv', '.MKV')):
        return 'videos'
    
    name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename

    # Pixel phone photos
    if filename.startswith('PXL_'):
        return 'pixel_photos'
    
    # iPhone photos (including newer formats)
    if filename.startswith('IMG_') and filename.endswith(('.JPG', '.PNG', '.HEIC', '.jpg', '.png', '.heic', '.jpeg', '.JPEG', '.webp', '.WEBP', '.avif', '.AVIF')):
        return 'iphone_photos'
    
    # Phone screenshots
    if filename.startswith('Screenshot_') or filename.startswith('screenshot_'):
        return 'screenshots'
    
    # Reddit downloads (RDT_ prefix) - CHECK EARLY
    if filename.startswith('RDT_'):
        return 'reddit'
    
    # Twitter: username_weirddateformat (like username_2048281074183389490-4)
    if re.search(r'_[0-9]{15,}(?:-[0-9]+)?$', name_without_ext):
        return 'twitter'
    
    # Twitter-style timestamps (YYYYMMDD_HHMMSS)
    if len(filename) >= 15 and filename[:8].isdigit() and filename[8] == '_' and filename[9:15].isdigit():
        if filename[15:16] not in '0123456789_':
            return 'twitter'
    
    # Twitter alphanumeric IDs (like HGNfsYHXMAAdlgb or HFDUR8PboAA-hUM)
    if len(name_without_ext) >= 10 and name_without_ext[0].isupper() and any(c.isalpha() for c in name_without_ext):
        # Check if it looks like Twitter media ID (uppercase letters, hyphens, no underscores)
        if all(c.isalnum() or c == '-' for c in name_without_ext):
            return 'twitter'
    
    # 4chan filenames - Unix timestamps (like 1702951395086 or 1652500509327)
    if name_without_ext.isdigit() and len(name_without_ext) >= 10:
        return '4chan'
    
    # 4chan filenames (UUID format like 1d591620-389b-11f1-88a3-a5e153261350)
    if filename.count('-') == 4:
        parts = filename.split('-')
        if len(parts[0]) == 8 and all(c in '0123456789abcdefABCDEF' for c in parts[0]):
            return '4chan'
    
    # MD5 hashes (common for Booru image downloads)
    if re.fullmatch(r'[0-9a-fA-F]{32}', name_without_ext):
        return 'images'

    # Reddit post IDs (alphanumeric like 6j2rsvpu0jyf1) - check BEFORE default image
    if name_without_ext.isalnum() and not name_without_ext.isdigit() and not name_without_ext.isalpha() and len(name_without_ext) >= 6:
        if name_without_ext.islower():
            return 'reddit'

    # Imageboard / Booru files (long tag strings separated by '+')
    if name_without_ext.count('+') >= 4:
        return 'images'
    
    # Manga archives and extracted pages (never GIFs)
    if not filename.lower().endswith('.gif'):
        manga_kws = ['vol.', 'vol ', 'chapter', 'ch.', 'anime', 'manga', 'reincarnated', 'issue']
        if any(ext in filename.lower() for ext in ['.cbz', '.rar', '.zip']) or any(kw in name_without_ext.lower() for kw in manga_kws):
            return 'manga'
            
        # Manga volumes formatted like " - v01" or " v05"
        if re.search(r'\s+(?:-\s+)?v\d+', name_without_ext.lower()):
            return 'manga'
    
    # Default image (including modern formats and GIFs)
    if filename.endswith(('.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG', '.webp', '.WEBP', '.avif', '.AVIF', '.gif', '.GIF')):
        return 'images'
    
    return None


def organize(directory, dry_run=False, recursive=False):
    """Organize files in directory and subdirectories."""
    
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: {directory} is not a valid directory")
        return
    
    log_file = dir_path / '.organize_log.json'
    moves = []
    stats = {'total': 0, 'organized': 0, 'uncategorized': 0, 'errors': 0, 'by_cat': {}}
    
    # Get files (recursively if flag is set, otherwise just top-level)
    files = []
    iterator = dir_path.rglob('*') if recursive else dir_path.iterdir()
    for item in iterator:
        if item.is_file() and not item.name.startswith('.'):
            files.append(item)
    files = sorted(files)
    stats['total'] = len(files)
    
    mode = 'DRY-RUN' if dry_run else 'LIVE'
    print(f"\n{'='*70}")
    print(f"FILE ORGANIZER [{mode}]")
    print(f"{'='*70}")
    print(f"Directory: {directory}")
    print(f"Total files: {len(files)}\n")
    
    for file in files:
        category = get_category(file.name)
        
        if category is None:
            stats['uncategorized'] += 1
            continue
        
        # Check if file is already in the correct category folder
        current_parent = file.parent.name
        if current_parent == category:
            # Already in correct folder
            continue
        
        if category not in stats['by_cat']:
            stats['by_cat'][category] = 0
        stats['by_cat'][category] += 1
        stats['organized'] += 1
        
        cat_path = dir_path / category
        dest = cat_path / file.name
        
        print(f"{file.name[:50]:<50} -> {category}")
        
        if not dry_run:
            try:
                cat_path.mkdir(exist_ok=True)
                # Handle duplicate filenames
                if dest.exists():
                    base, ext = dest.name.rsplit('.', 1) if '.' in dest.name else (dest.name, '')
                    counter = 1
                    while dest.exists():
                        if ext:
                            dest = cat_path / f"{base}_{counter}.{ext}"
                        else:
                            dest = cat_path / f"{base}_{counter}"
                        counter += 1
                shutil.move(str(file), str(dest))
                moves.append({
                    'filename': file.name,
                    'from': str(file.parent),
                    'to': str(cat_path)
                })
            except Exception as e:
                print(f"  ERROR: {e}")
                stats['errors'] += 1
                stats['organized'] -= 1
                if category in stats['by_cat']:
                    stats['by_cat'][category] -= 1
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Organized:     {stats['organized']:,} files")
    print(f"Uncategorized: {stats['uncategorized']:,} files")
    print(f"Errors:        {stats['errors']:,}")
    
    if stats['by_cat']:
        print(f"\nBy category:")
        for cat in sorted(stats['by_cat'].keys()):
            print(f"  {cat:.<40} {stats['by_cat'][cat]:>4} files")
    
    # Save log if not dry-run
    if not dry_run and moves:
        # Append to existing log to allow undoing multiple runs
        existing_moves = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    existing_moves = json.load(f)
            except json.JSONDecodeError:
                pass
        existing_moves.extend(moves)
        
        with open(log_file, 'w') as f:
            json.dump(existing_moves, f, indent=2)
        print(f"\nLog saved to: {log_file}")
        print("To undo this organization, run: python file_organizer.py --undo")
        
        # Clean up empty folders
        print(f"\nCleaning up empty folders...")
        removed = cleanup_empty_folders(dir_path)
        if removed > 0:
            print(f"Removed {removed} empty folder(s)")
    
    print(f"{'='*70}\n")


def cleanup_empty_folders(directory):
    """Remove empty subdirectories."""
    
    dir_path = Path(directory)
    removed = 0
    
    for folder in dir_path.iterdir():
        if folder.is_dir() and not folder.name.startswith('.'):
            # Check if folder is truly empty
            contents = list(folder.iterdir())
            if len(contents) == 0:
                try:
                    folder.rmdir()
                    print(f"Removed empty folder: {folder.name}")
                    removed += 1
                except Exception as e:
                    print(f"  ERROR removing {folder.name}: {e}")
    
    return removed

def undo(directory):
    """Undo the last organization."""
    
    dir_path = Path(directory)
    log_file = dir_path / '.organize_log.json'
    
    if not log_file.exists():
        print("Error: No organization log found. Nothing to undo.")
        return
    
    with open(log_file, 'r') as f:
        moves = json.load(f)
    
    if not moves:
        print("Error: Log is empty. Nothing to undo.")
        return
    
    print(f"\n{'='*70}")
    print("UNDOING ORGANIZATION")
    print(f"{'='*70}")
    print(f"Found {len(moves)} files to move back\n")
    
    errors = 0
    for move in reversed(moves):  # Reverse order
        filename = move['filename']
        src = Path(move['to']) / filename
        dst = Path(move['from']) / filename
        
        if src.exists():
            try:
                shutil.move(str(src), str(dst))
                print(f"{filename[:50]:<50} -> back to root")
            except Exception as e:
                print(f"  ERROR moving {filename}: {e}")
                errors += 1
        else:
            print(f"  WARNING: {filename} not found at {src}")
    
    # Delete log file
    log_file.unlink()
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Moved back:    {len(moves) - errors} files")
    print(f"Errors:        {errors}")
    print(f"Log deleted")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    import sys
    
    undo_flag = '--undo' in sys.argv
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    recursive_flag = '--recursive' in sys.argv or '-r' in sys.argv
    directory = os.getcwd()
    
    for arg in sys.argv[1:]:
        if not arg.startswith('-'):
            directory = arg
    
    if undo_flag:
        undo(directory)
    else:
        organize(directory, dry_run=dry_run, recursive=recursive_flag)

#!/usr/bin/env python3
"""Validate .dockerignore file and check for missing patterns."""

import os
import fnmatch
from pathlib import Path
from typing import List, Set

def load_dockerignore_patterns() -> List[str]:
    """Load patterns from .dockerignore file."""
    dockerignore_path = Path(__file__).parent.parent / '.dockerignore'
    
    if not dockerignore_path.exists():
        print("❌ .dockerignore file not found!")
        return []
    
    with open(dockerignore_path, 'r') as f:
        patterns = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#')
        ]
    
    print(f"📋 Loaded {len(patterns)} ignore patterns")
    return patterns

def find_matching_files(patterns: List[str], root_dir: Path) -> Set[Path]:
    """Find files that would be ignored by the patterns."""
    ignored_files = set()
    
    for root, dirs, files in os.walk(root_dir):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')
        
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(root_dir)
            
            for pattern in patterns:
                if fnmatch.fnmatch(str(rel_path), pattern):
                    ignored_files.add(rel_path)
                    break
    
    return ignored_files

def find_missing_patterns(ignored_files: Set[Path]) -> List[str]:
    """Find common patterns that might be missing."""
    common_patterns = [
        '.env',
        '.env.*',
        '*.pyc',
        '__pycache__',
        '.pytest_cache',
        '.coverage',
        'htmlcov',
        'logs/',
        '*.log',
        'venv/',
        '.vscode/',
        '.idea/',
        '*.swp',
        '*.swo',
        '.DS_Store',
        'Thumbs.db',
        'secrets/',
        '*.pem',
        '*.key',
        '*.crt',
    ]
    
    missing = []
    for pattern in common_patterns:
        # Check if pattern would match any files
        matched = False
        for file in ignored_files:
            if fnmatch.fnmatch(str(file), pattern):
                matched = True
                break
        
        if not matched:
            # Check if pattern might be useful (if files exist)
            if any(Path('.').glob(pattern.replace('*', ''))):
                missing.append(pattern)
    
    return missing

def main():
    """Main validation function."""
    print("🔍 Starting .dockerignore validation...")
    
    patterns = load_dockerignore_patterns()
    if not patterns:
        return
    
    root_dir = Path(__file__).parent.parent
    ignored_files = find_matching_files(patterns, root_dir)
    
    print(f"\n📦 Total files that would be ignored: {len(ignored_files)}")
    
    # Show sample of ignored files
    if ignored_files:
        print("\n📋 Sample of ignored files:")
        for file in sorted(ignored_files)[:10]:
            print(f"  - {file}")
        if len(ignored_files) > 10:
            print(f"  ... and {len(ignored_files) - 10} more")
    
    # Check for missing patterns
    missing = find_missing_patterns(ignored_files)
    if missing:
        print("\n⚠️  Consider adding these common patterns:")
        for pattern in missing:
            print(f"  - {pattern}")
    
    # Check for sensitive files
    sensitive_patterns = ['.env', '*.pem', '*.key', 'secrets/']
    sensitive_found = []
    
    for pattern in sensitive_patterns:
        for file in ignored_files:
            if fnmatch.fnmatch(str(file), pattern):
                sensitive_found.append(file)
    
    if sensitive_found:
        print(f"\n✅ Sensitive files are properly ignored: {len(sensitive_found)} found")
    else:
        print("\n⚠️  No sensitive files detected - verify they exist and are ignored")
    
    print("\n✅ Validation complete!")

if __name__ == '__main__':
    main()
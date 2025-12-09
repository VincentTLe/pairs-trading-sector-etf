import os
from pathlib import Path

def list_files_stats(root_dir):
    files = []
    for p in Path(root_dir).rglob('*.py'):
        try:
            line_count = len(p.read_text(encoding='utf-8').splitlines())
            files.append((line_count, str(p)))
        except Exception as e:
            print(f"Error reading {p}: {e}")
            
    files.sort(key=lambda x: x[0], reverse=True)
    
    print(f"{'Lines':<10} {'Path'}")
    print("-" * 80)
    for lines, path in files:
        print(f"{lines:<10} {path}")

if __name__ == "__main__":
    list_files_stats("src/pairs_trading_etf")

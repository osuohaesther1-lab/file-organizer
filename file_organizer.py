"""
============================================================
 FILE ORGANIZER
============================================================
 Automatically sorts the files in a folder into clean,
 categorized subfolders (Images, Documents, Videos, etc.)

 Features:
   - 14 smart categories based on file extension
   - Dry-run mode to preview changes before moving anything
   - Undo mode to revert the last run
   - Handles duplicate file names safely (no overwrites)
   - Full log of every action (saved as JSON)

 Usage:
   python file_organizer.py --folder "C:\\Users\\You\\Downloads"
   python file_organizer.py --folder "C:\\Users\\You\\Downloads" --dry-run
   python file_organizer.py --folder "C:\\Users\\You\\Downloads" --undo
============================================================
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------
# Category definitions: extension -> category name
# ----------------------------------------------------------------------
CATEGORIES = {
    # Images
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images",
    ".bmp": "Images", ".svg": "Images", ".webp": "Images", ".ico": "Images",
    ".tiff": "Images", ".heic": "Images", ".raw": "Images",
    # Documents
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
    ".txt": "Documents", ".md": "Documents", ".rtf": "Documents", ".odt": "Documents",
    # Spreadsheets
    ".xls": "Spreadsheets", ".xlsx": "Spreadsheets", ".csv": "Spreadsheets",
    ".ods": "Spreadsheets",
    # Presentations
    ".ppt": "Presentations", ".pptx": "Presentations", ".odp": "Presentations",
    # Videos
    ".mp4": "Videos", ".mov": "Videos", ".avi": "Videos", ".mkv": "Videos",
    ".wmv": "Videos", ".flv": "Videos", ".webm": "Videos", ".m4v": "Videos",
    # Audio
    ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio", ".aac": "Audio",
    ".ogg": "Audio", ".m4a": "Audio", ".wma": "Audio",
    # Archives
    ".zip": "Archives", ".rar": "Archives", ".7z": "Archives", ".tar": "Archives",
    ".gz": "Archives", ".bz2": "Archives", ".xz": "Archives",
    # Code
    ".py": "Code", ".js": "Code", ".ts": "Code", ".html": "Code", ".css": "Code",
    ".java": "Code", ".c": "Code", ".cpp": "Code", ".cs": "Code", ".php": "Code",
    ".rb": "Code", ".go": "Code", ".rs": "Code", ".json": "Code", ".xml": "Code",
    ".yml": "Code", ".yaml": "Code", ".sh": "Code", ".bat": "Code", ".sql": "Code",
    ".ipynb": "Code",
    # Installers
    ".exe": "Installers", ".msi": "Installers", ".dmg": "Installers",
    ".deb": "Installers", ".rpm": "Installers", ".apk": "Installers",
    # Fonts
    ".ttf": "Fonts", ".otf": "Fonts", ".woff": "Fonts", ".woff2": "Fonts",
}

LOG_FILE_NAME = ".file_organizer_log.json"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def get_category(filename: str) -> str:
    """Return the category for a file based on its extension."""
    ext = Path(filename).suffix.lower()
    return CATEGORIES.get(ext, "Other")


def unique_destination(target_dir: Path, filename: str) -> Path:
    """Return a non-colliding destination path (adds (1), (2), ... if needed)."""
    destination = target_dir / filename
    if not destination.exists():
        return destination

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = target_dir / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def organize(folder: Path, dry_run: bool = False) -> None:
    """
    Move every file directly inside `folder` into a category subfolder.
    Returns nothing; writes a log entry for every move.
    """
    if not folder.is_dir():
        print(f"ERROR: '{folder}' is not a valid folder.")
        sys.exit(1)

    files = [f for f in folder.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not files:
        print("Nothing to organize - the folder is already empty (or only has folders).")
        return

    moves = []          # (source, destination) for real moves
    log_entries = []    # saved to JSON for undo

    for file_path in files:
        category = get_category(file_path.name)
        target_dir = folder / category
        destination = unique_destination(target_dir, file_path.name)

        moves.append((file_path, destination))
        log_entries.append({
            "moved": str(file_path),
            "to": str(destination),
            "category": category,
            "time": datetime.now().isoformat(timespec="seconds"),
        })

    # -- Show the plan -------------------------------------------------
    print(f"\n{'DRY RUN - nothing will be moved' if dry_run else 'ORGANIZING'}: {folder}")
    print("-" * 60)
    for source, destination in moves:
        print(f"  {source.name:45} ->  {destination.parent.name}\\{destination.name}")
    print("-" * 60)
    print(f"Total files: {len(moves)}")

    if dry_run:
        print("Dry run complete. Remove --dry-run to organize for real.\n")
        return

    # -- Execute the moves ---------------------------------------------
    for source, destination in moves:
        destination.parent.mkdir(exist_ok=True)
        shutil.move(str(source), str(destination))

    # Save the log so the run can be undone
    log_path = folder / LOG_FILE_NAME
    log_path.write_text(json.dumps(log_entries, indent=2), encoding="utf-8")
    print(f"\nDone! {len(moves)} file(s) organized.")
    print(f"Log saved to: {log_path}")
    print("Tip: run with --undo to put everything back.\n")


def undo(folder: Path) -> None:
    """Revert the most recent organize run using the saved log."""
    log_path = folder / LOG_FILE_NAME
    if not log_path.exists():
        print(f"ERROR: no log found at '{log_path}' - nothing to undo.")
        sys.exit(1)

    entries = json.loads(log_path.read_text(encoding="utf-8"))
    restored = 0

    for entry in entries:
        moved_to = Path(entry["to"])
        moved_from = Path(entry["moved"])
        if moved_to.exists():
            moved_from.parent.mkdir(exist_ok=True)
            shutil.move(str(moved_to), str(unique_destination(moved_from.parent, moved_from.name)))
            restored += 1

    # Clean up now-empty category folders (but never touch the log or hidden files)
    for child in folder.iterdir():
        if child.is_dir() and not any(child.iterdir()):
            child.rmdir()

    log_path.unlink(missing_ok=True)
    print(f"\nUndo complete! {restored} file(s) moved back. Empty category folders removed.\n")


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Organize files in a folder into categorized subfolders.",
        epilog="Example: python file_organizer.py --folder Downloads --dry-run",
    )
    parser.add_argument(
        "--folder", "-f", type=str, default=str(Path.home() / "Downloads"),
        help="Folder to organize (default: your Downloads folder)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be moved without changing anything",
    )
    parser.add_argument(
        "--undo", action="store_true",
        help="Undo the last organize run in this folder",
    )
    args = parser.parse_args()

    folder = Path(args.folder).expanduser()
    if args.undo:
        undo(folder)
    else:
        organize(folder, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

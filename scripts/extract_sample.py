import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.extractor import extract_text_from_file


def extract_and_write(path: Path, out_dir: Path):
    try:
        text = extract_text_from_file(str(path))
    except Exception as e:
        print(f"[ERROR] Failed extracting {path}: {e}")
        return False
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (path.stem + ".txt")
    out_path.write_text(text, encoding="utf-8")
    print(f"Wrote: {out_path} (chars: {len(text)})")
    excerpt = text[:800].replace('\n', ' ') + ("..." if len(text) > 800 else "")
    print("Excerpt:", excerpt)
    return True


def main():
    p = argparse.ArgumentParser(description="Run extractor on sample PDFs")
    p.add_argument("--samples", "-s", default="samples/sample_rfps", help="Samples folder")
    p.add_argument("--out", "-o", default="outputs/extracted", help="Output folder for extracted text")
    p.add_argument("--pattern", default="*.pdf", help="Glob pattern to match files")
    args = p.parse_args()

    samples_dir = Path(args.samples)
    out_dir = Path(args.out)

    if not samples_dir.exists():
        print(f"Samples folder not found: {samples_dir}")
        return

    files = sorted(samples_dir.glob(args.pattern))
    if not files:
        print(f"No files found in {samples_dir} matching {args.pattern}")
        return

    success = 0
    for f in files:
        print(f"\n--- Processing {f.name} ---")
        if extract_and_write(f, out_dir):
            success += 1

    print(f"\nCompleted: {success}/{len(files)} files extracted. Outputs in: {out_dir}")


if __name__ == "__main__":
    main()

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parsing.layout.parse_layout import import_layout_xml


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Import all .fromLayout.xml files into PostgreSQL."
    )
    parser.add_argument(
        "root",
        help="Root folder that contains the PIAS layout XMLs (InvokeOutputs).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[ERROR] Root folder does not exist: {root}")
        return

    # find all layout XMLs
    xml_files = sorted(root.rglob("*.fromLayout.xml"))
    if not xml_files:
        print(f"No .fromLayout.xml files found under {root}")
        return

    print(f"Found {len(xml_files)} layout XML files under {root}")
    for xml in xml_files:
        print(f"Importing {xml}")
        try:
            import_layout_xml(xml)
            print("  -> OK")
        except Exception as e:
            print(f"  [ERROR] {e}")


if __name__ == "__main__":
    main()

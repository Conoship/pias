import os
import re
import subprocess
import argparse
import logging
import sys
from typing import Optional, Tuple, Dict, List
from src.parsing.stability.parse_probdam_local import import_probdam_rtf_local
from src.parsing.stability.parse_num_int import import_numint_rtf

logger = logging.getLogger(__name__)

# finding version-like folder names
VERSION_REGEX = re.compile(
    r"^(?:"
    r"(?P<v>v)(?P<vnum>\d+(?:\.\d+)?)"
    r"|(?P<run>run)(?P<runnum>\d+(?:\.\d+)?)"
    r"|(?P<numdot>\d+(?:\.\d+)?)\."
    r"|(?P<num>\d+(?:\.\d+)?)"
    r")(?P<rest>\D.*)?$",
    re.IGNORECASE,
)


def to_windows_path(path: str) -> str:
    if path.startswith("/mnt/") and len(path) > 6:
        drive_letter = path[5].upper()
        rest = path[7:]
        rest_windows = rest.replace("/", "\\")
        return f"{drive_letter}:\\" + rest_windows
    return path


def get_version_token(folder_name: str) -> Optional[str]:
    m = VERSION_REGEX.match(folder_name.strip())
    if not m:
        return None
    if m.group("v"):
        return f"v{m.group('vnum')}"
    if m.group("run"):
        return f"run{m.group('runnum')}"
    if m.group("numdot"):
        return m.group("numdot")
    if m.group("num"):
        return m.group("num")
    return None


# normalize names and add _ for spaces/special chars
def normalize_name(name: str) -> str:
    name = name.strip()
    return re.sub(r"[^\w\-]+", "_", name)


# regulates version number format
def numeric_version_from_token(token: Optional[str]) -> str:
    if not token:
        return "1"
    t = token.strip().lower()
    # strip v / run prefix
    if t.startswith("v"):
        t = t[1:]
    elif t.startswith("run"):
        t = t[3:]

    # normalize leading zeros in integer part
    if re.match(r"^\d+(?:\.\d+)?$", t):
        parts = t.split(".")
        parts[0] = str(int(parts[0]))  # '04' -> '4'
        t = ".".join(parts)

    # ensure only digits / dots
    if not t or not re.match(r"^[0-9.]+$", t):
        return "1"
    return t


# Find process / ship / base-version / subversion (run index)
def find_info(
    path: str,
    design_process: List[str],
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[int]]:

    parts = path.split(os.sep)
    process: Optional[str] = None
    folder_ship: Optional[str] = None
    version_token: Optional[str] = None
    sub_index: Optional[int] = None

    # normalise design names
    normalized_processes = [p.strip().lower() for p in design_process]

    # find process + ship
    process_idx: Optional[int] = None
    for i, part in enumerate(parts):
        part_clean = part.strip()
        if part_clean.lower() in normalized_processes:
            process = part_clean
            process_idx = i
            if i + 1 < len(parts):
                folder_ship = parts[i + 1]
            break

    if process_idx is None or folder_ship is None:
        return process, folder_ship, version_token, sub_index

    last_dir_idx = len(parts) - 2  # directory containing the rtf
    filename = parts[-1]

    # find version folder index + token
    version_folder_idx: Optional[int] = None

    # try explicit version folder between ship and last_dir
    for j in range(process_idx + 2, last_dir_idx + 1):
        candidate = parts[j]
        vt = get_version_token(candidate)
        if vt:
            version_folder_idx = j
            version_token = vt
            break

    # if no explicit version folder then first folder under ship
    if version_folder_idx is None:
        ship_idx = process_idx + 1
        if ship_idx + 1 <= last_dir_idx:
            version_folder_idx = ship_idx + 1
            # compute implicit version index among ship's children
            ship_dir = path
            # climb from full path to the ship directory
            levels_up = len(parts) - 1 - ship_idx
            for _ in range(levels_up):
                ship_dir = os.path.dirname(ship_dir)
            version_folder = parts[version_folder_idx]
            try:
                children = sorted(
                    d
                    for d in os.listdir(ship_dir)
                    if os.path.isdir(os.path.join(ship_dir, d))
                )
                if version_folder in children:
                    version_num = children.index(version_folder) + 1
                    version_token = str(version_num)  # '1','2',...
                else:
                    version_token = "1"
            except Exception:
                version_token = "1"
        else:
            # rtf directly under ship
            version_token = "1"

    # compute sub_index
    rtf_dir = os.path.dirname(path)

    if version_folder_idx is not None and last_dir_idx > version_folder_idx:
        # rtf is in a run-folder below the version folder
        run_folder_path = rtf_dir
        run_folder_name = os.path.basename(run_folder_path)
        # reconstruct version_dir (directory of version folder)
        version_dir = path
        levels_up_v = len(parts) - 1 - version_folder_idx
        for _ in range(levels_up_v):
            version_dir = os.path.dirname(version_dir)
        try:
            siblings = sorted(
                d
                for d in os.listdir(version_dir)
                if os.path.isdir(os.path.join(version_dir, d))
            )
            if run_folder_name in siblings:
                sub_index = siblings.index(run_folder_name) + 1
        except Exception:
            sub_index = None
    else:
        # rtf sits directly in the version folder (or directly under ship)
        parent_dir = rtf_dir
        try:
            rtf_siblings = sorted(
                f for f in os.listdir(parent_dir) if f.lower().endswith(".rtf")
            )
            if filename in rtf_siblings:
                sub_index = rtf_siblings.index(filename) + 1
        except Exception:
            sub_index = None

    return process, folder_ship, version_token, sub_index


# RTF parsing
def extract_ship_rtf(path: str) -> Optional[str]:
    """
    Find the ship name in an RTF file by looking for the pattern:
      {\\info{\\subject Results of PIAS module .... \\<ship>}
    We look for 'subject Results of PIAS module' and take the last token
    after '\\' before the closing '}'.
    """
    try:
        with open(path, "r", encoding="latin-1", errors="ignore") as f:
            content = f.read(4096)
    except OSError:
        return None

    lower = content.lower()
    key = "subject results of pias module"
    pos = lower.find(key)
    if pos == -1:
        return None

    end_brace = content.find("}", pos)
    if end_brace == -1:
        chunk = content[pos:]
    else:
        chunk = content[pos:end_brace]

    last_bs = chunk.rfind("\\")
    if last_bs == -1:
        return None

    start = last_bs + 1
    end = start
    while end < len(chunk) and chunk[end] not in (
        "\\",
        "{",
        "}",
        " ",
        "\t",
        "\r",
        "\n",
    ):
        end += 1

    ship = chunk[start:end].strip()
    return ship or None


# dumpcomps.xml template
DUMPCOMPS_TEMPLATE = """
<XML_requests>
  <XML_request>
    <Request_type>Set_subcompartment_to_frustrum</Request_type>
    <Request_parameters>
        <XML_output_filename>{output_filename}</XML_output_filename>
    </Request_parameters>
  </XML_request>
  <XML_request>
    <Request_type>export_ship_layout</Request_type>
  </XML_request>
</XML_requests>
"""

PROCESS_SHORT = {
    "basic design": "basic",
    "concept design": "concept",
    "final design": "final",
}


# Final pattern: ship_design_version(_if_duplicate)_subversion_piasShip.fromLayout
def make_output_filename(
    process: Optional[str],
    ship: Optional[str],
    version_numeric: str,
    sub_index: Optional[int],
    pias_ship: Optional[str],
) -> str:

    ship_token = normalize_name(ship or "UnknownShip")
    proc_key = (process or "").strip().lower()
    design_token = PROCESS_SHORT.get(
        proc_key, normalize_name(process or "UnknownProcess")
    )

    # ensure we always have a numeric version string
    version_str = version_numeric or "1"
    if not re.match(r"^[0-9.]+$", version_str):
        version_str = "1"

    # subversion defaults to 1 if missing
    sub = sub_index if sub_index is not None else 1

    base = f"{ship_token}_{design_token}_{version_str}_{sub}"

    if pias_ship:
        base += f"_{normalize_name(pias_ship)}"

    return base + ".fromLayout"


def write_dumpcomps(xml_dir: str, xml_output_filename: str) -> None:
    os.makedirs(xml_dir, exist_ok=True)
    xml_content = DUMPCOMPS_TEMPLATE.format(output_filename=xml_output_filename)
    dumpcomps_path = os.path.join(xml_dir, "dumpcomps.xml")
    with open(dumpcomps_path, "w", encoding="utf-8") as f:
        f.write(xml_content)


# invoke.bat handling
def create_invoke(
    invoke_template: str, run_dir: str, pias_ship: Optional[str], bat_name: str
) -> Optional[str]:
    if not pias_ship:
        logger.info(
            "[warning] No PIAS ship name found in RTF for %s, skipping", run_dir
        )
        return None

    replacement = f"set piasname={pias_ship}"
    if "set piasname=ship" in invoke_template:
        bat_text = invoke_template.replace("set piasname=ship", replacement)
    else:
        logger.info(
            "[warning] Could not find 'set piasname=ship' in template; using as-is."
        )
        bat_text = invoke_template

    os.makedirs(run_dir, exist_ok=True)
    bat_path = os.path.join(run_dir, bat_name)
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_text)
    return bat_path


def run(
    invoke_template: str,
    rtf_path: str,
    run_dir: str,
    out_dir: str,
    ship_folder: Optional[str],
    process: Optional[str],
    version_numeric: str,
    sub_index: Optional[int],
    pias_ship: Optional[str],
    numint_template: Optional[str],
    run_numint: bool,
    skip_numint_exists: bool,
) -> int:

    os.makedirs(out_dir, exist_ok=True)

    print("\n[run] starting")
    print(f"       RTF: {rtf_path}")
    print(f"       run_dir: {run_dir}")
    print(f"       out_dir: {out_dir}")
    print(f"       process: {process}")
    print(f"       ship_folder: {ship_folder}")
    print(f"       version_numeric: {version_numeric}")
    print(f"       sub_index: {sub_index}")
    print(f"       pias_ship: {pias_ship}")

    xml_out = make_output_filename(
        process, ship_folder, version_numeric, sub_index, pias_ship
    )
    xml_output_path = os.path.join(out_dir, xml_out)

    xml_output_pias = to_windows_path(xml_output_path)
    print(f"       xml_output_path (WSL): {xml_output_path}")
    print(f"       xml_output_path (Windows): {xml_output_pias}")

    write_dumpcomps(run_dir, xml_output_pias)
    print(f"       dumpcomps.xml written in {run_dir}")

    bat_path = create_invoke(invoke_template, run_dir, pias_ship, "invoke_run.bat")
    if not bat_path:
        print("[warning] no bat_path (no pias_ship), skipping rtf")
        return 1

    bat_windows = to_windows_path(bat_path)
    print(f"       bat_path (WSL): {bat_path}")
    print(f"       bat_path (Windows): {bat_windows}")

    try:
        result = subprocess.run(
            ["cmd.exe", "/c", bat_windows],
            cwd=run_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        logger.error("invoke_run.bat timed out for RTF: %s", rtf_path)
        return 1
    except Exception as e:
        logger.error("failes to start cmd.exe for RTF: %s, error: %s", rtf_path, e)
        return 1

    if result.returncode != 0:
        logger.error("invoke_run.bat failed for RTF: %s", rtf_path)
        if result.stderr.strip():
            logger.error("  stderr:")
            logger.error(result.stderr.strip())
        if result.stdout.strip():
            logger.error("  stdout:")
            logger.error(result.stdout.strip())
    else:
        logger.info("[invoke] %s", rtf_path)
        logger.info("         PIAS ship run: %s", pias_ship)
        logger.info("         Output file: %s", xml_out)
        if result.stdout.strip():
            logger.info("  stdout:")
            logger.info(result.stdout.strip())
        if result.stderr.strip():
            logger.info("  stderr:")
            logger.info(result.stderr.strip())

    # Always import the existing ProbDam RTF, even if invoke_run.bat failed.
    ship_token = normalize_name(ship_folder or "UnknownShip")
    proc_key = (process or "").strip().lower()
    design_token = PROCESS_SHORT.get(
        proc_key, normalize_name(process or "UnknownProcess")
    )
    sub = sub_index if sub_index is not None else 1
    ship_run = normalize_name(pias_ship) if pias_ship else ""

    try:
        logger.info("Importing Probdam data into SQL from RTF: %s", rtf_path)
        import_probdam_rtf_local(
            rtf_path,
            ship_name=ship_token,
            design_name=design_token,
            version=version_numeric,
            subversion=str(sub),
            ship_run=ship_run,
        )
        print("         -> Probdam data imported into SQL")
    except Exception:
        logger.exception("         Probdam import failed for RTF: %s", rtf_path)

    if run_numint:
        if not numint_template:
            logger.error("numint_invoke.bat template not provided, cannot run numint.")
            return result.returncode

        numint_rtf = os.path.join(run_dir, "outputNumInt.rtf")

        if skip_numint_exists and os.path.isfile(numint_rtf):
            logger.info(
                "Skipping numint_invoke.bat as outputNumInt.rtf already exists: %s",
                numint_rtf,
            )
        else:
            numint_bat_path = create_invoke(
                numint_template, run_dir, pias_ship, "numint_invoke.bat"
            )
            if not numint_bat_path:
                logger.error(
                    "Could not create numint_invoke.bat (no pias_ship), skipping numint."
                )
                return result.returncode

            numint_bat_windows = to_windows_path(numint_bat_path)
            logger.info("[numint] Running numint_invoke.bat for RTF: %s", rtf_path)

            try:
                numint_result = subprocess.run(
                    ["cmd.exe", "/c", numint_bat_windows],
                    cwd=run_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=False,
                )
            except Exception as e:
                logger.error(
                    "failed to start cmd.exe for numint RTF: %s, error: %s", rtf_path, e
                )
                return result.returncode

            if numint_result.stdout.strip():
                logger.info("[numint] stdout:", numint_result.stdout.strip())
            if numint_result.stderr.strip():
                logger.info("[numint] stderr:", numint_result.stderr.strip())

            if numint_result.returncode != 0:
                logger.error(
                    "[numint] numint_invoke.bat failed for RTF: %s | %s",
                    rtf_path,
                    numint_result.returncode,
                )
            else:
                if os.path.exists(numint_rtf):
                    try:
                        logger.info("Importing NumInt data into SQL...")
                        import_numint_rtf(
                            numint_rtf,
                            ship_name=ship_token,
                            design_name=design_token,
                            version=version_numeric,
                            subversion=str(sub),
                            ship_run=ship_run,
                        )
                        print("         -> NumInt data imported into SQL")
                    except Exception as e:
                        logger.error("         NumInt import failed: %s", e)
                else:
                    logger.error(
                        "NumInt run succeeded but outputNumInt.rtf not found: %s",
                        run_dir,
                    )
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run or preview invoke.bat on a folder tree."
    )
    parser.add_argument("--root", required=True, help="Root folder of project tree.")
    parser.add_argument(
        "--out", required=True, help="Output folder for invoke results."
    )
    parser.add_argument(
        "--invoke",
        required=True,
        help="Path to invoke.bat template ('ship' as placeholder)",
    )
    parser.add_argument(
        "--numint-invoke",
        default=None,
        help="Path to numint_invoke.bat template (different).",
    )
    parser.add_argument(
        "--run-numint",
        action="store_true",
        help="Also run numint_invoke.bat after invoke.bat for each RTF (outputNumInt.rtf).",
    )
    parser.add_argument(
        "--skip-numInt-exists",
        action="store_true",
        help="Skip running numint_invoke.bat if outputNumInt.rtf already exists.",
    )
    parser.add_argument(
        "--design-process",
        nargs="+",
        default=["Basic Design", "Concept Design", "Final Design"],
        help="Process folder names to detect match.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run invoke.bat, otherwise just preview.",
    )
    args = parser.parse_args()

    ROOT = os.path.abspath(args.root)
    OUTPUT_DIR = os.path.abspath(args.out)
    INVOKE_TEMPLATE_PATH = os.path.abspath(args.invoke)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_path = os.path.join(OUTPUT_DIR, "runInvoke.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger.info("-- runInvoke start --")
    logger.info("ROOT=%s", ROOT)
    logger.info("OUTPUT_DIR=%s", OUTPUT_DIR)
    logger.info("INVOKE_TEMPLATE_PATH=%s", INVOKE_TEMPLATE_PATH)

    try:
        with open(INVOKE_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            invoke_template = f.read()
    except OSError as e:
        logger.error("Could not read invoke template: %s", INVOKE_TEMPLATE_PATH)
        raise SystemExit(1)

    normalized_processes = [p.strip().lower() for p in args.design_process]

    numint_template = None
    if args.numint_invoke:
        numint_path = os.path.abspath(args.numint_invoke)
        try:
            with open(numint_path, "r", encoding="utf-8") as f:
                numint_template = f.read()
            logger.info("NUMINT_INVOKE_TEMPLATE_PATH=%s", numint_path)
        except OSError as e:
            logger.error("Could not read numint invoke template: %s", numint_path)
            raise SystemExit(1)

    # track all subdirectories under ship folders, and which actually contain RTFs
    all_ship_subdirs = set()
    dirs_with_rtf = set()

    # global counter to ensure duplicates (same ship/design/version/sub/pias) get .2 for example
    usage_counts: Dict[Tuple[str, str, str, int, str], int] = {}

    for dirpath, dirnames, filenames in os.walk(ROOT):
        parts = dirpath.split(os.sep)

        # find process + ship indices in this path
        process_idx = None
        ship_idx = None
        for i, part in enumerate(parts):
            if part.strip().lower() in normalized_processes:
                process_idx = i
                if i + 1 < len(parts):
                    ship_idx = i + 1  # folder right after process is ship
                break

        ship_dir = None
        if ship_idx is not None:
            ship_dir = os.path.join(*parts[: ship_idx + 1])

        is_under_ship = ship_idx is not None and len(parts) > ship_idx + 1

        if is_under_ship:
            all_ship_subdirs.add(dirpath)

        # all real RTFs in THIS folder
        rtf_files = [
            f
            for f in filenames
            if f.lower().endswith(".rtf") and not f.startswith("~$")
        ]

        if rtf_files:
            # mark this folder as containing RTFs
            dirs_with_rtf.add(dirpath)
            # we do not traverse deeper once an RTF is found (so we never see M-TANKS etc under a run that already has an RTF)
            dirnames[:] = []

        # processing logic for each RTF
        for filename in rtf_files:
            rtf_path = os.path.join(dirpath, filename)
            pias_ship = extract_ship_rtf(rtf_path)

            process, ship_folder, version_token, sub_index = find_info(
                rtf_path, args.design_process
            )

            if not process or not ship_folder or ship_dir is None:
                logger.info(
                    "[skip] Could not detect process/ship/ship_dir for RTF: %s, skipping",
                    rtf_path,
                )
                continue

            # base numeric version (no 'run', no 'v', no `0`, only digits/decimals)
            base_version = numeric_version_from_token(version_token)

            # subversion defaults to 1
            sub = sub_index if sub_index is not None else 1

            # prepare key for duplicate detection
            ship_token = normalize_name(ship_folder)
            proc_key = PROCESS_SHORT.get(
                process.strip().lower(), normalize_name(process)
            )
            pias_key = normalize_name(pias_ship) if pias_ship else "none"
            key = (ship_token, proc_key, base_version, sub, pias_key)

            count = usage_counts.get(key, 0) + 1
            usage_counts[key] = count

            # if this is a duplicate, append .2, .3... to version
            if count > 1:
                version_numeric = f"{base_version}.{count}"
            else:
                version_numeric = base_version

            out_dir = os.path.join(
                OUTPUT_DIR,
                normalize_name(process),
                normalize_name(ship_folder),
            )

            xml_out = make_output_filename(
                process, ship_folder, version_numeric, sub_index, pias_ship
            )

            if not args.execute:
                logger.info(
                    "process=%r, ship_folder=%r, version_token=%r, "
                    "base_version=%r, version_numeric=%r, subversion=%r, "
                    "pias_ship=%r, count=%d",
                    process,
                    ship_folder,
                    version_token,
                    base_version,
                    version_numeric,
                    sub,
                    pias_ship,
                    count,
                )
                logger.info("output_dir=%s", out_dir)
                logger.info("xml_output_filename=%s", xml_out)
            else:
                run(
                    invoke_template,
                    rtf_path,
                    dirpath,
                    out_dir,
                    ship_folder,
                    process,
                    version_numeric,
                    sub_index,
                    pias_ship,
                    numint_template,
                    args.run_numint,
                    args.skip_numInt_exists,
                )

    # find deepest subdirs under ships with NO RTF anywhere in their subtree
    candidate_missing = set()
    for d in all_ship_subdirs:
        # does this directory or any directory below it have RTFs?
        has_rtf_in_subtree = any(
            r == d or r.startswith(d + os.sep) for r in dirs_with_rtf
        )
        if not has_rtf_in_subtree:
            candidate_missing.add(d)

    deepest_missing = []
    for d in candidate_missing:
        is_parent_of_other = any(
            other != d and other.startswith(d + os.sep) for other in candidate_missing
        )
        if not is_parent_of_other:
            deepest_missing.append(d)

    deepest_missing.sort()
    for d in deepest_missing:
        logger.warning("[SKIP] No RTF files found in subtree under: %s", d)


if __name__ == "__main__":
    main()

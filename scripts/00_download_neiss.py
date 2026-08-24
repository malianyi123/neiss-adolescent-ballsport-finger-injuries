#!/usr/bin/env python
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup

from utils import RAW_DIR, REPORT_DIR, annual_raw_path, curl_download, ensure_dirs, load_config, now_utc


def discover_archive_link(year: int) -> str | None:
    """Submit the public CPSC archive form with curl and parse the resulting data link."""

    home = "https://www.cpsc.gov/cgibin/NEISSQuery/home.aspx"
    cookie = RAW_DIR / ".neiss_cookies.txt"
    get = subprocess.run(
        ["curl", "-L", "-s", "-c", str(cookie), "-b", str(cookie), home],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if get.returncode != 0 or "Archived Annual NEISS Data" not in get.stdout:
        return None
    soup = BeautifulSoup(get.stdout, "html.parser")
    fields: dict[str, str] = {}
    for inp in soup.find_all("input"):
        name = inp.get("name")
        typ = (inp.get("type") or "").lower()
        if not name or typ in {"checkbox", "radio", "submit", "button", "image", "reset"}:
            continue
        fields[name] = inp.get("value", "")
    fields["ctl00$ContentPlaceHolder1$cbResearcher"] = "on"
    fields["ctl00$ContentPlaceHolder1$ddlArchivedYear"] = str(year)
    fields["ctl00$ContentPlaceHolder1$ddlArchivedFileFormat"] = "TSV"
    fields["ctl00$ContentPlaceHolder1$btnFindarchiveRpt"] = "Find Data"

    args = [
        "curl",
        "-L",
        "-s",
        "-c",
        str(cookie),
        "-b",
        str(cookie),
        "-H",
        "Content-Type: application/x-www-form-urlencoded",
        "--url",
        home,
    ]
    for k, v in fields.items():
        args.extend(["--data-urlencode", f"{k}={v}"])
    post = subprocess.run(args, check=False, capture_output=True, text=True, timeout=120)
    if post.returncode != 0:
        return None
    soup = BeautifulSoup(post.stdout, "html.parser")
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        txt = a.get_text(" ", strip=True)
        if re.search(fr"neiss{year}.*tab", txt, re.I) or re.search(fr"neiss{year}\.tsv", href, re.I):
            if href.startswith("http"):
                return href
            return "https://www.cpsc.gov/cgibin/NEISSQuery/" + href.lstrip("/")
    return None


def write_manual_readme(config: dict) -> None:
    years = config["study"]["years"]
    lines = [
        "# Manual NEISS Download Instructions",
        "",
        "Automated download was attempted first. If one or more files are missing, use these steps.",
        "",
        "1. Open the official CPSC NEISS query/download page:",
        f"   {config['sources']['neiss_query_page']}",
        "2. Select `Researcher` or the most appropriate user affiliation.",
        "3. Under `Archived Annual NEISS Data`, select each year listed below.",
        "4. Select `Tab Delimited Text` and click `Find Data`.",
        "5. Save raw files unchanged in `data/raw/neiss/` with the exact filenames shown.",
        "",
    ]
    for year in years:
        lines.append(f"- {year}: `neiss{year}.tsv`")
    lines.extend(
        [
            "",
            "Also download the official NEISS Data Dictionary Excel file from:",
            config["sources"]["data_dictionary_url"],
            "",
            "Save it as `data/raw/neiss/DataDictionary042022.xlsx`.",
            "",
            "Save the NEISS format file, if needed, from:",
            config["sources"]["format_file_url"],
            "",
            "as `data/raw/neiss/neiss_fmt.txt`.",
        ]
    )
    (RAW_DIR.parent / "README_download.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    config = load_config()
    write_manual_readme(config)
    rows = []

    dictionary_dest = RAW_DIR / "DataDictionary042022.xlsx"
    if dictionary_dest.exists() and dictionary_dest.stat().st_size > 1000:
        dict_ok = True
        dict_msg = "already present"
    else:
        dict_ok, dict_msg = curl_download(config["sources"]["data_dictionary_url"], dictionary_dest, timeout=120)
    rows.append(
        {
            "resource": "NEISS Data Dictionary",
            "year": "",
            "file": str(dictionary_dest),
            "source_url": config["sources"]["data_dictionary_url"],
            "download_utc": now_utc(),
            "status": "ok" if dict_ok else "failed",
            "message": dict_msg[:500],
        }
    )

    fmt_dest = RAW_DIR / "neiss_fmt.txt"
    if fmt_dest.exists() and fmt_dest.stat().st_size > 1000:
        fmt_ok = True
        fmt_msg = "already present"
    else:
        fmt_ok, fmt_msg = curl_download(config["sources"]["format_file_url"], fmt_dest, timeout=120)
    rows.append(
        {
            "resource": "NEISS format file",
            "year": "",
            "file": str(fmt_dest),
            "source_url": config["sources"]["format_file_url"],
            "download_utc": now_utc(),
            "status": "ok" if fmt_ok else "failed",
            "message": fmt_msg[:500],
        }
    )

    failed = []
    for year in config["study"]["years"]:
        dest = annual_raw_path(int(year))
        source_url = config["sources"]["annual_tsv_url_template"].format(year=year)
        if dest.exists() and dest.stat().st_size > 1000:
            ok, msg = True, "already present"
        else:
            ok, msg = curl_download(source_url, dest, timeout=600)
            if not ok:
                discovered = discover_archive_link(int(year))
                if discovered:
                    source_url = discovered
                    ok, msg = curl_download(source_url, dest, timeout=600)
        if not ok:
            failed.append(year)
        rows.append(
            {
                "resource": "annual archived NEISS TSV",
                "year": year,
                "file": str(dest),
                "source_url": source_url,
                "download_utc": now_utc(),
                "status": "ok" if ok else "failed",
                "message": msg[:500],
            }
        )
        print(f"{year}: {'ok' if ok else 'failed'}")

    report = REPORT_DIR / "download_log.csv"
    import pandas as pd

    pd.DataFrame(rows).to_csv(report, index=False)
    if failed or not dict_ok or not fmt_ok:
        raise SystemExit(
            "Automated download incomplete. Follow data/raw/README_download.md. "
            f"Failed years/resources: {failed}"
        )


if __name__ == "__main__":
    main()

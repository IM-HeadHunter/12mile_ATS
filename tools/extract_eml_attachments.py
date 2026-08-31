import argparse
import csv
import hashlib
import os
import re
from email import policy
from email.parser import BytesParser
from pathlib import Path


def safe_part(value: str, fallback: str = "unnamed") -> str:
    value = (value or "").strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:180] or fallback


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for index in range(1, 10000):
        candidate = parent / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not allocate unique path for {path}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eml-root", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    eml_root = Path(args.eml_root)
    out_root = Path(args.out_root)
    report = Path(args.report)
    out_root.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    eml_files = sorted(eml_root.rglob("*.eml"))
    for index, eml_path in enumerate(eml_files, start=1):
        rel_eml = eml_path.relative_to(eml_root)
        try:
            with eml_path.open("rb") as handle:
                msg = BytesParser(policy=policy.default).parse(handle)
        except Exception as exc:
            rows.append({
                "status": "eml_parse_error",
                "eml_path": str(eml_path),
                "eml_relative_path": str(rel_eml),
                "subject": "",
                "from": "",
                "date": "",
                "attachment_name": "",
                "content_type": "",
                "bytes": 0,
                "sha256": "",
                "output_path": "",
                "error": str(exc),
            })
            continue

        subject = str(msg.get("subject", ""))
        sender = str(msg.get("from", ""))
        date = str(msg.get("date", ""))
        message_folder = out_root / safe_part(str(rel_eml.parent), "root") / f"{index:06d}-{safe_part(subject, 'no subject')}"
        attachment_count = 0

        for part in msg.walk():
            if part.is_multipart():
                continue
            filename = part.get_filename()
            disposition = (part.get_content_disposition() or "").lower()
            if not filename and disposition != "attachment":
                continue
            filename = safe_part(filename or f"attachment-{attachment_count + 1}")
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    content = part.get_content()
                    payload = content.encode("utf-8", errors="replace") if isinstance(content, str) else bytes(content)
            except Exception as exc:
                rows.append({
                    "status": "attachment_decode_error",
                    "eml_path": str(eml_path),
                    "eml_relative_path": str(rel_eml),
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "attachment_name": filename,
                    "content_type": part.get_content_type(),
                    "bytes": 0,
                    "sha256": "",
                    "output_path": "",
                    "error": str(exc),
                })
                continue

            attachment_count += 1
            message_folder.mkdir(parents=True, exist_ok=True)
            output_path = unique_path(message_folder / filename)
            output_path.write_bytes(payload)
            rows.append({
                "status": "extracted",
                "eml_path": str(eml_path),
                "eml_relative_path": str(rel_eml),
                "subject": subject,
                "from": sender,
                "date": date,
                "attachment_name": filename,
                "content_type": part.get_content_type(),
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "output_path": str(output_path),
                "error": "",
            })

    with report.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "status",
            "eml_path",
            "eml_relative_path",
            "subject",
            "from",
            "date",
            "attachment_name",
            "content_type",
            "bytes",
            "sha256",
            "output_path",
            "error",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"EML files: {len(eml_files)}")
    print(f"Rows: {len(rows)}")
    print(f"Extracted: {sum(1 for row in rows if row['status'] == 'extracted')}")
    print(f"Report: {report}")
    print(f"Output: {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

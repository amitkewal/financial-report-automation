"""PDF conversion via LibreOffice headless. Each call gets its own throwaway
user-profile directory so concurrent conversions (multiple users/funds) don't
collide on soffice's lock file.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings


def convert_to_pdf(docx_path: str, output_dir: str, timeout: int = 120) -> str:
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    profile_dir = tempfile.mkdtemp(prefix="soffice_profile_")
    try:
        cmd = [
            settings.soffice_binary,
            "--headless",
            "--norestore",
            f"-env:UserInstallation=file://{profile_dir}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir_path),
            docx_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"soffice PDF conversion failed: {result.stderr or result.stdout}")

        pdf_path = output_dir_path / (Path(docx_path).stem + ".pdf")
        if not pdf_path.exists():
            raise RuntimeError("soffice reported success but no PDF was produced")
        return str(pdf_path)
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)

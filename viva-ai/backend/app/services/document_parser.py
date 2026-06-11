"""
Document Parser Service
Extracts text content from PDF reports, PPTX slides, and source code ZIP files.
"""
import zipfile
import os
import re
from pathlib import Path
from typing import Optional
import fitz  # PyMuPDF
from pptx import Presentation
from pptx.util import Inches


# Source code file extensions we care about
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c",
    ".cs", ".go", ".rb", ".php", ".html", ".css", ".sql", ".sh",
    ".yaml", ".yml", ".json", ".md", ".txt", ".env.example"
}

# Files/dirs to skip in ZIP
SKIP_PATTERNS = {
    "__pycache__", "node_modules", ".git", ".DS_Store",
    "dist", "build", ".next", "venv", ".env"
}


def parse_pdf(file_path: str) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    text_parts = []
    try:
        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                text_parts.append(f"[Page {page_num}]\n{text.strip()}")
        doc.close()
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}")

    return "\n\n".join(text_parts)


def parse_pptx(file_path: str) -> list[dict]:
    """Extract text from each PPTX slide. Returns list of {slide_num, title, content}."""
    slides = []
    try:
        prs = Presentation(file_path)
        for slide_num, slide in enumerate(prs.slides, start=1):
            title = ""
            content_parts = []

            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                text = shape.text_frame.text.strip()
                if not text:
                    continue
                # Heuristic: shape type 13 is a title placeholder; also use first short text as title
                if not title and (shape.shape_type == 13 or len(text) < 100):
                    title = text
                else:
                    content_parts.append(text)

            slides.append({
                "slide_num": slide_num,
                "title": title,
                "content": "\n".join(content_parts)
            })
    except Exception as e:
        raise ValueError(f"Failed to parse PPTX: {e}")

    return slides


def parse_code_zip(file_path: str, extract_dir: str) -> list[dict]:
    """
    Extract and read source code files from a ZIP archive.
    Returns list of {filename, relative_path, language, content}.
    """
    code_files = []
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            # Filter out unwanted entries
            members = [
                m for m in zf.namelist()
                if not any(skip in m for skip in SKIP_PATTERNS)
                and not m.endswith("/")  # skip directories
            ]

            for member in members:
                ext = Path(member).suffix.lower()
                if ext not in CODE_EXTENSIONS:
                    continue

                try:
                    with zf.open(member) as f:
                        raw = f.read()
                        # Try UTF-8, fallback to latin-1
                        try:
                            content = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            content = raw.decode("latin-1")

                    # Limit very large files to first 300 lines
                    lines = content.splitlines()
                    if len(lines) > 300:
                        content = "\n".join(lines[:300]) + f"\n... [{len(lines) - 300} more lines truncated]"

                    code_files.append({
                        "filename": Path(member).name,
                        "relative_path": member,
                        "language": _detect_language(ext),
                        "content": content,
                        "line_count": len(lines)
                    })
                except Exception:
                    continue  # skip unreadable files

    except zipfile.BadZipFile:
        raise ValueError("Uploaded file is not a valid ZIP archive.")

    return code_files


def _detect_language(ext: str) -> str:
    """Map file extension to language name."""
    mapping = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "React JSX", ".tsx": "React TSX", ".java": "Java",
        ".cpp": "C++", ".c": "C", ".cs": "C#", ".go": "Go",
        ".rb": "Ruby", ".php": "PHP", ".html": "HTML", ".css": "CSS",
        ".sql": "SQL", ".sh": "Shell", ".yaml": "YAML", ".yml": "YAML",
        ".json": "JSON", ".md": "Markdown"
    }
    return mapping.get(ext, "Unknown")


def build_extracted_content(
    report_path: Optional[str] = None,
    ppt_path: Optional[str] = None,
    code_zip_path: Optional[str] = None,
    extract_dir: str = "uploads/extracted"
) -> dict:
    """
    Orchestrates parsing of all uploaded files.
    Returns a unified content dict ready to feed into the AI service.
    """
    content = {
        "report": "",
        "slides": [],
        "code_files": [],
        "summary_text": ""  # Concatenated text for LLM context window
    }

    if report_path and os.path.exists(report_path):
        content["report"] = parse_pdf(report_path)

    if ppt_path and os.path.exists(ppt_path):
        content["slides"] = parse_pptx(ppt_path)

    if code_zip_path and os.path.exists(code_zip_path):
        content["code_files"] = parse_code_zip(code_zip_path, extract_dir)

    # Build a single summarized text blob (LLM has limited context)
    parts = []
    if content["report"]:
        # Trim to first 3000 chars for summary
        parts.append("=== PROJECT REPORT ===\n" + content["report"][:3000])

    if content["slides"]:
        slide_text = "\n".join(
            f"Slide {s['slide_num']}: {s['title']} — {s['content'][:200]}"
            for s in content["slides"]
        )
        parts.append("=== PRESENTATION SLIDES ===\n" + slide_text)

    if content["code_files"]:
        # Show file list + first file content as sample
        file_list = "\n".join(
            f"- {cf['relative_path']} ({cf['language']}, {cf['line_count']} lines)"
            for cf in content["code_files"]
        )
        parts.append("=== SOURCE CODE FILES ===\n" + file_list)
        if content["code_files"]:
            first = content["code_files"][0]
            parts.append(
                f"=== SAMPLE CODE ({first['filename']}) ===\n"
                + first["content"][:1500]
            )

    content["summary_text"] = "\n\n".join(parts)
    return content

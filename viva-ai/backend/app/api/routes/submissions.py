import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_student
from app.models.user import User
from app.models.submission import Submission
from app.services.document_parser import build_extracted_content
from app.services.ai_service import generate_knowledge_map

router = APIRouter(prefix="/submissions", tags=["Submissions"])

ALLOWED_EXTENSIONS = {
    "report": [".pdf"],
    "ppt": [".pptx", ".ppt"],
    "code": [".zip"]
}


def _validate_extension(filename: str, file_type: str) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED_EXTENSIONS.get(file_type, [])


async def _save_upload(file: UploadFile, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(dest_dir, filename)

    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB.")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    return file_path


@router.post("/", status_code=201)
async def create_submission(
    title: str = Form(...),
    description: str = Form(None),
    report: UploadFile = File(None),
    ppt: UploadFile = File(None),
    code_zip: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    if not report and not ppt and not code_zip:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    report_path = ppt_path = code_zip_path = None

    if report and report.filename:
        if not _validate_extension(report.filename, "report"):
            raise HTTPException(status_code=400, detail="Report must be a PDF file.")
        report_path = await _save_upload(report, upload_dir)

    if ppt and ppt.filename:
        if not _validate_extension(ppt.filename, "ppt"):
            raise HTTPException(status_code=400, detail="Presentation must be PPTX.")
        ppt_path = await _save_upload(ppt, upload_dir)

    if code_zip and code_zip.filename:
        if not _validate_extension(code_zip.filename, "code"):
            raise HTTPException(status_code=400, detail="Source code must be a ZIP file.")
        code_zip_path = await _save_upload(code_zip, upload_dir)

    # Parse documents
    try:
        extracted_content = build_extracted_content(
            report_path=report_path,
            ppt_path=ppt_path,
            code_zip_path=code_zip_path,
            extract_dir=os.path.join(upload_dir, "extracted")
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Document parsing failed: {str(e)}")

    # Generate knowledge map via AI
    knowledge_map = {}
    if extracted_content.get("summary_text"):
        try:
            knowledge_map = await generate_knowledge_map(extracted_content["summary_text"])
        except Exception as e:
            # Don't fail the upload if AI call fails — store empty map
            knowledge_map = {"error": str(e), "key_topics": [], "tech_stack": []}

    submission = Submission(
        student_id=str(current_user.id),
        title=title,
        description=description,
        report_path=report_path,
        ppt_path=ppt_path,
        code_zip_path=code_zip_path,
        extracted_content=extracted_content,
        knowledge_map=knowledge_map,
    )
    db.add(submission)
    await db.flush()

    return {
        "submission_id": str(submission.id),
        "title": submission.title,
        "knowledge_map": knowledge_map,
        "files_uploaded": {
            "report": report_path is not None,
            "ppt": ppt_path is not None,
            "code_zip": code_zip_path is not None,
        }
    }


@router.get("/")
async def list_submissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    result = await db.execute(
        select(Submission)
        .where(Submission.student_id == str(current_user.id))
        .order_by(Submission.created_at.desc())
    )
    submissions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "description": s.description,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "has_report": s.report_path is not None,
            "has_ppt": s.ppt_path is not None,
            "has_code": s.code_zip_path is not None,
            "knowledge_map": s.knowledge_map,
        }
        for s in submissions
    ]


@router.get("/{submission_id}")
async def get_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission or str(submission.student_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Submission not found.")
    return {
        "id": str(submission.id),
        "title": submission.title,
        "description": submission.description,
        "knowledge_map": submission.knowledge_map,
        "created_at": submission.created_at.isoformat() if submission.created_at else None,
    }

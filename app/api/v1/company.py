import os
import shutil
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models import CompanyProfile
from app.schemas import CompanyProfileOut, CompanyProfileUpdate
import time
from app.core.config import settings

router = APIRouter()


@router.get("/", response_model=CompanyProfileOut)
async def get_company(db: AsyncSession = Depends(get_db)):
    cp = (await db.execute(select(CompanyProfile))).scalars().first()
    if not cp:
        # cp = CompanyProfile(name="YKG LAB & DIAGNOSTIC CENTER")
        # db.add(cp)
        # await db.commit()
        # await db.refresh(cp)
        raise HTTPException(detail="No company profile found", status_code=404)
    return cp


@router.put("/", response_model=CompanyProfileOut)
async def update_company(
    name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    slogan: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    cp = (await db.execute(select(CompanyProfile))).scalars().first()

    logo_url_path = None
    if logo:
        # 1. Path relative to the static folder
        relative_folder = "uploads/company"
        # 2. Absolute path on your disk (app/web/static/uploads/company)
        absolute_upload_dir = os.path.join(settings.STATIC_DIR, relative_folder)

        # Ensure the directory exists
        os.makedirs(absolute_upload_dir, exist_ok=True)

        # 3. Create a unique filename using a timestamp to avoid browser caching issues
        file_ext = os.path.splitext(logo.filename)[1]
        timestamp = int(time.time())
        filename = f"logo_{timestamp}{file_ext}"

        # Full path to save the file
        file_save_path = os.path.join(absolute_upload_dir, filename)

        # 4. Save file to disk
        with open(file_save_path, "wb") as buffer:
            shutil.copyfileobj(logo.file, buffer)

        # 5. The URL path the browser will use (e.g., /static/uploads/company/logo_123.png)
        logo_url_path = f"/static/{relative_folder}/{filename}"

    # Database logic
    if not cp:
        cp = CompanyProfile(name=name or "YKG LAB & DIAGNOSTIC CENTER")
        db.add(cp)

    # Update fields
    if name:
        cp.name = name
    if phone:
        cp.phone = phone
    if address:
        cp.address = address
    if email:
        cp.email = email
    if slogan:
        cp.slogan = slogan
    if logo_url_path:
        cp.logo = logo_url_path

    await db.commit()
    await db.refresh(cp)
    return cp


@router.post("/", response_model=CompanyProfileOut, status_code=status.HTTP_201_CREATED)
async def create_company_profile(
    name: str = Form(...),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    slogan: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    # 1. Check for existing profile
    existing_cp = (await db.execute(select(CompanyProfile))).scalars().first()
    if existing_cp:
        raise HTTPException(
            status_code=400,
            detail="Company profile already exists. Use the update (PUT) route instead.",
        )

    # 2. Handle Logo Upload
    logo_url_path = None
    if logo:
        relative_folder = "uploads/company"
        # Points to: app/web/static/uploads/company
        absolute_upload_dir = os.path.join(settings.STATIC_DIR, relative_folder)

        os.makedirs(absolute_upload_dir, exist_ok=True)

        file_ext = os.path.splitext(logo.filename)[1]
        # Unique filename to prevent cache issues
        filename = f"logo_init_{int(time.time())}{file_ext}"
        file_save_path = os.path.join(absolute_upload_dir, filename)

        with open(file_save_path, "wb") as buffer:
            shutil.copyfileobj(logo.file, buffer)

        # The path the browser will call: /static/uploads/company/logo_init_...
        logo_url_path = f"/static/{relative_folder}/{filename}"

    # 3. Create Database Object
    new_cp = CompanyProfile(
        name=name,
        phone=phone,
        address=address,
        email=email,
        slogan=slogan,
        logo=logo_url_path,
    )

    db.add(new_cp)
    await db.commit()
    await db.refresh(new_cp)
    return new_cp

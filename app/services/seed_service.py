# import json
# from pathlib import Path
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.models import Analyzer, Test, TestParameter, CompanyProfile

# async def seed_from_json(db: AsyncSession, seed_path: str = "integration/seed/seed.json") -> None:
#     # path = Path(seed_path)
#     path = Path(__file__).parent.parent / seed_path
#     if not path.exists():
#         return

#     payload = json.loads(path.read_text(encoding="utf-8"))

#     # Company profile (single row)
#     cp = (await db.execute(select(CompanyProfile))).scalars().first()
#     if not cp:
#         cp = CompanyProfile(name=payload.get("company", {}).get("name", "YKG LAB & DIAGNOSTIC CENTER"))
#         db.add(cp)

#     # analyzers
#     existing_analyzers = {a.name: a for a in (await db.execute(select(Analyzer))).scalars().all()}
#     for a in payload.get("analyzers", []):
#         if a["name"] not in existing_analyzers:
#             db.add(Analyzer(**a))

#     await db.commit()

#     # refresh analyzer mapping
#     analyzers = {a.name: a for a in (await db.execute(select(Analyzer))).scalars().all()}

#     # tests + parameters
#     existing_tests = {t.name: t for t in (await db.execute(select(Test))).scalars().all()}
#     for t in payload.get("tests", []):
#         if t["name"] not in existing_tests:
#             default_analyzer_id = analyzers.get(t.get("default_analyzer")) .id if t.get("default_analyzer") and t.get("default_analyzer") in analyzers else None
#             test_obj = Test(
#                 name=t["name"],
#                 department=t.get("department"),
#                 price_ghs=t.get("price_ghs"),
#                 default_analyzer_id=default_analyzer_id,
#             )
#             db.add(test_obj)
#             await db.flush()
#             for p in t.get("parameters", []):
#                 db.add(TestParameter(test_id=test_obj.id, name=p["name"], unit=p.get("unit"), ref_range=p.get("ref_range")))
#     await db.commit()

import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import Analyzer, Test, TestParameter, CompanyProfile, User

async def seed_from_json(db: AsyncSession, seed_path: str = "integration/seed/seed.json") -> None:
    path = Path(__file__).parent.parent / seed_path
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    async with db.begin():
        # Company profile
        cp = (await db.execute(select(CompanyProfile))).scalars().first()
        if not cp:
            cp = CompanyProfile(name=payload.get("company", {}).get("name", "YKG LAB & DIAGNOSTIC CENTER"))
            db.add(cp)

        # Analyzers
        existing_analyzers = {a.name: a for a in (await db.execute(select(Analyzer))).scalars().all()}
        for a in payload.get("analyzers", []):
            if a["name"] not in existing_analyzers:
                db.add(Analyzer(**a))

    # Refresh analyzers after commit
    analyzers = {a.name: a for a in (await db.execute(select(Analyzer))).scalars().all()}

    async with db.begin():
        # Tests + parameters
        existing_tests = {t.name: t for t in (await db.execute(select(Test))).scalars().all()}
        for t in payload.get("tests", []):
            if t["name"] not in existing_tests:
                analyzer_obj = analyzers.get(t.get("default_analyzer"))
                test_obj = Test(
                    name=t["name"],
                    department=t.get("department"),
                    price_ghs=t.get("price_ghs"),
                    default_analyzer_id=analyzer_obj.id if analyzer_obj else None,
                )
                db.add(test_obj)
                await db.flush()
                for p in t.get("parameters", []):
                    db.add(TestParameter(test_id=test_obj.id, name=p["name"], unit=p.get("unit"), ref_range=p.get("ref_range")))

    # Default admin user (idempotent)
    admin_email = "s.e@dataglow.tech"
    admin_name = "Emmanuel Sampah"
    existing_admin = (await db.execute(select(User).where(User.email == admin_email))).scalar_one_or_none()
    if not existing_admin:
        db.add(
            User(
                email=admin_email,
                full_name=admin_name,
                password_hash=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                role="admin",
                is_active=True,
            )
        )
        await db.commit()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from app.db.session import get_db
from app.models.catalog import Phlebotomy, Sample
from app.models.lab import Appointment


from app.schemas.phlebotomy import PhlebotomyResponse

router = APIRouter()


@router.get("/pending", response_model=list[PhlebotomyResponse])
async def get_pending_phlebotomies(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Phlebotomy)
        .options(selectinload(Phlebotomy.appointment).selectinload(Appointment.patient))
        .where(Phlebotomy.samples.any())
    )

    result = await db.execute(stmt)

    return result.scalars().all()


@router.get("/", response_model=list[PhlebotomyResponse])
async def get_all_phlebotomies(db: AsyncSession = Depends(get_db)):
    stmt = select(Phlebotomy).options(
        selectinload(Phlebotomy.appointment).selectinload(Appointment.patient)
    )

    result = await db.execute(stmt)

    return result.scalars().all()


# @router.get(
#     "/{phlebotomy_id}/samples",
#     response_model=list[SampleResponse],
# )
# async def get_phlebotomy_samples(
#     phlebotomy_id: int,
#     db: AsyncSession = Depends(get_db),
# ):
#     phlebotomy = await db.get(Phlebotomy, phlebotomy_id)

#     if not phlebotomy:
#         raise HTTPException(status_code=404, detail="Phlebotomy not found")

#     stmt = (
#         select(Sample)
#         .where(Sample.phlebotomy_id == phlebotomy_id)
#         .options(
#             joinedload(Sample.sample_category),
#             selectinload(Sample.tests).selectinload(SampleTest.test),
#         )
#         .order_by(Sample.collection_date.desc())
#     )

#     samples = await db.execute(stmt)
#     results = samples.scalars().all()

#     response = []

#     for sample in results:
#         test_list = [
#             SampleTestMiniResponse(
#                 sample_test_id=sample_test.id,  # association id
#                 test_id=sample_test.test.id,
#                 name=sample_test.test.name,
#             )
#             for sample_test in sample.tests
#         ]

#         response.append(
#             SampleResponse(
#                 id=sample.id,
#                 sample_type=sample.sample_category.category_name,
#                 priority=sample.priority,
#                 storage_location=sample.storage_location,
#                 collection_site=sample.collection_site,
#                 status=sample.status,
#                 appointment_id=sample.appointment_id,
#                 patient_id=sample.patient_id,
#                 phlebotomy_id=sample.phlebotomy_id,
#                 tests=test_list,
#             )
#         )

#     return response


# @router.delete("/sample-tests/{sample_test_id}", status_code=204)
# async def delete_sample_test(
#     sample_test_id: int,
#     db: AsyncSession = Depends(get_db),
# ):
#     sample_test = await db.get(SampleTest, sample_test_id)

#     if not sample_test:
#         raise HTTPException(status_code=404, detail="SampleTest not found")

#     await db.delete(sample_test)
#     await db.commit()

#     return None

from fastapi import APIRouter
<<<<<<< HEAD
from app.api.v1 import health, company, catalog, patients, orders, integration, seed, auth
=======
from app.api.v1 import health, company, catalog, patients, orders, integration, seed, reports
>>>>>>> origin/codex/implement-astm-parsing-and-auto-merge-reports

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(company.router, prefix="/company", tags=["company"])
router.include_router(catalog.router, prefix="/catalog", tags=["catalog"])
router.include_router(patients.router, prefix="/patients", tags=["patients"])
router.include_router(orders.router, prefix="/orders", tags=["orders"])
router.include_router(integration.router, prefix="/integration", tags=["integration"])
<<<<<<< HEAD
router.include_router(auth.router, prefix="/auth", tags=["auth"])
=======
router.include_router(reports.router, prefix="/reports", tags=["reports"])
>>>>>>> origin/codex/implement-astm-parsing-and-auto-merge-reports
router.include_router(seed.router, tags=["seed"])

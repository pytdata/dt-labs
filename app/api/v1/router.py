from fastapi import APIRouter

# <<<<<<< HEAD
# from app.api.v1 import health, company, catalog, patients, orders, integration, seed, auth
# =======
from app.api.v1 import (
    appointments,
    health,
    company,
    catalog,
    patients,
    orders,
    integration,
    seed,
    auth,
    reports,
    visits,
    test_categories,
    staffs,
    samples,
    transactions,
    tests,
    test_templates,
    phlebotomy,
)
# >>>>>>> origin/codex/implement-astm-parsing-and-auto-merge-reports

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(company.router, prefix="/company", tags=["company"])
router.include_router(catalog.router, prefix="/catalog", tags=["catalog"])
router.include_router(patients.router, prefix="/patients", tags=["patients"])
router.include_router(orders.router, prefix="/orders", tags=["orders"])
router.include_router(integration.router, prefix="/integration", tags=["integration"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(seed.router, tags=["seed"])
router.include_router(visits.router, prefix="/visits", tags=["visits"])
router.include_router(
    appointments.router, prefix="/appointments", tags=["appointments"]
)
router.include_router(staffs.router, prefix="/staffs", tags=["staffs"])
router.include_router(
    test_categories.router, prefix="/test-categories", tags=["test-categories"]
)
router.include_router(samples.router, prefix="/samples", tags=["samples"])
router.include_router(transactions.router, prefix="/payments", tags=["payments"])
router.include_router(tests.router, prefix="/tests", tags=["tests"])
router.include_router(
    test_templates.router, prefix="/tests-templates", tags=["tests-templates"]
)
router.include_router(phlebotomy.router, prefix="/phlebotomy", tags=["phlebotomy"])

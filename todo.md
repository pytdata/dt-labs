# LIS Analyzer Integration - Implementation Plan

## Phase 1: Model & Schema Fixes
- [x] Study existing codebase thoroughly
- [x] Add `is_automated` and `transport_type` fields to `Analyzer` model in catalog.py
- [x] Add `protocol_type` field to `Analyzer` model
- [x] Fix/remove conflicting `app/services/analyzer_ingestion.py`
- [x] Fix duplicate relationship declarations in LabResult model
- [x] Create Alembic migration for new Analyzer fields

## Phase 2: Core Ingestion Service Rewrite
- [x] Fix `AnalyzerIngestionService` - proper raw storage pipeline
- [x] Fix `AnalyzerTCPServerListener.run()` to use `tcp_ip`/`tcp_port`
- [x] Fix ASTM protocol handling in TCPServerListener (ENQ/ACK/EOT)
- [x] Fix `AnalyzerIngestionRepository.get_automated_analyzers()`

## Phase 3: FastAPI Integration
- [x] Wire `AnalyzerWorkerManager` into FastAPI lifespan (startup/shutdown)
- [x] Update `app/main.py` to use `asynccontextmanager` lifespan

## Phase 4: Standalone Services
- [x] Create `run_analyzer_worker.py` - standalone listener entry point
- [x] Create `run_simulator.py` - standalone simulator entry point

## Phase 5: API Endpoints
- [x] Add/verify analyzer CRUD endpoints (GET/POST/PUT/DELETE /analyzers)
- [x] Add simulator API endpoints (POST /api/v1/integration/simulate/*)
- [x] Update `app/schemas/catalog.py` with AnalyzerCreate/AnalyzerUpdate/AnalyzerOut

## Phase 6: Web UI Updates
- [ ] Update `analyzer-form.html` template — add is_automated, transport_type, protocol_type fields
- [ ] Update `analyzer_add_post` in `app/web/router.py` — accept new form fields
- [ ] Update `analyzer_edit_post` in `app/web/router.py` — accept and save new fields

## Phase 7: Migration & Verification
- [ ] Verify migration 0010 chain is clean (check down_revision is correct)
- [ ] Verify all imports work (no circular imports, no missing modules)
- [ ] Run full syntax check on all modified files

## Phase 8: GitHub Push
- [ ] Stage all changes (git add)
- [ ] Commit with descriptive message
- [ ] Push to feature branch and create PR summary
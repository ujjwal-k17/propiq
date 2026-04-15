"""
Data Pipeline
=============
Orchestrates all scrapers into a single, resumable ingestion pipeline.

Can be invoked:
  - Via FastAPI background task (POST /api/v1/admin/pipeline/refresh)
  - Directly from CLI:  python -m app.scrapers.pipeline
  - Via Celery beat for nightly scheduled runs

Pipeline stages (per city refresh):
  1. RERA    — projects + complaint counts (via RERAScraperMaharashtra)
  2. MCA     — developer corporate data + financial stress (via MCAScraper)
  3. News    — developer news sentiment (via NewsScraper)
  4. Scoring — (re)generate RiskScore for every affected project

PipelineResult dataclass captures per-stage counts and any errors so callers
can surface a progress summary without parsing logs.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.developer import Developer
from app.models.project import Project
from app.scrapers.mca_scraper import MCAScraper
from app.scrapers.news_scraper import NewsScraper
from app.scrapers.rera_scraper import RERAScraperMaharashtra
from app.services.risk_engine import RiskEngine

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    name: str
    success: bool
    records: int = 0
    error: str | None = None


@dataclass
class PipelineResult:
    cities: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    stages: list[StageResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return all(s.success for s in self.stages)

    @property
    def duration_seconds(self) -> float:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0

    def summary(self) -> dict:
        return {
            "success": self.success,
            "cities": self.cities,
            "duration_seconds": round(self.duration_seconds, 1),
            "stages": [
                {
                    "name": s.name,
                    "success": s.success,
                    "records": s.records,
                    "error": s.error,
                }
                for s in self.stages
            ],
        }


class DataPipeline:
    """
    Stateless pipeline orchestrator.  Instantiate once; call run methods
    as many times as needed.
    """

    def __init__(self) -> None:
        self._risk_engine = RiskEngine()

    # ── Full city refresh ─────────────────────────────────────────────────────

    async def run_full_refresh(
        self,
        db: AsyncSession,
        cities: list[str] | None = None,
    ) -> PipelineResult:
        """
        Run the complete ingestion pipeline for one or more cities.

        Steps per city:
          1. RERA scrape → upsert projects + developers
          2. MCA update → enrich every discovered developer
          3. News scan → sentiment analysis and storage
          4. Risk score → (re)generate for all projects in city

        Returns PipelineResult with per-stage counts and error messages.
        """
        if cities is None:
            cities = ["Mumbai", "Bengaluru"]

        result = PipelineResult(cities=cities)
        logger.info(f"[Pipeline] Starting full refresh for cities: {cities}")

        # ── Stage 1: RERA ─────────────────────────────────────────────────────
        rera_stage = await self._run_rera_stage(db, cities)
        result.stages.append(rera_stage)

        # ── Stage 2: MCA ──────────────────────────────────────────────────────
        mca_stage = await self._run_mca_stage(db)
        result.stages.append(mca_stage)

        # ── Stage 3: News ─────────────────────────────────────────────────────
        news_stage = await self._run_news_stage(db)
        result.stages.append(news_stage)

        # ── Stage 4: Risk scoring ─────────────────────────────────────────────
        scoring_stage = await self._run_scoring_stage(db, cities)
        result.stages.append(scoring_stage)

        result.finished_at = datetime.now(timezone.utc)
        summary = result.summary()
        logger.info(
            f"[Pipeline] Full refresh complete in {result.duration_seconds:.1f}s "
            f"— {summary}"
        )
        return result

    # ── Single project refresh ────────────────────────────────────────────────

    async def refresh_single_project(
        self,
        project_id: uuid.UUID,
        db: AsyncSession,
    ) -> PipelineResult:
        """
        Re-scrape RERA data for a specific project, refresh its developer's
        news, and regenerate the risk score.
        Returns PipelineResult with the new RiskScore accessible via
        ``stages[-1].records``.
        """
        result = PipelineResult()

        # Fetch project + developer from DB
        proj_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project: Project | None = proj_result.scalar_one_or_none()

        if project is None:
            result.stages.append(
                StageResult("rera", success=False, error=f"Project {project_id} not found")
            )
            result.finished_at = datetime.now(timezone.utc)
            return result

        # ── Stage 1: RERA re-scrape ───────────────────────────────────────────
        try:
            async with RERAScraperMaharashtra() as rera:
                if project.rera_registration_no:
                    raw = await rera.get_project_details(project.rera_registration_no)
                    await rera.save([raw], db)
            result.stages.append(StageResult("rera", success=True, records=1))
        except Exception as exc:
            logger.error(f"[Pipeline:single] RERA stage failed: {exc}")
            result.stages.append(StageResult("rera", success=False, error=str(exc)))

        # ── Stage 2: Developer news refresh ──────────────────────────────────
        dev_result = await db.execute(
            select(Developer).where(Developer.id == project.developer_id)
        )
        developer: Developer | None = dev_result.scalar_one_or_none()

        if developer:
            try:
                async with NewsScraper() as news:
                    count = await news.scrape_and_store_news(developer, db)
                result.stages.append(StageResult("news", success=True, records=count))
            except Exception as exc:
                logger.error(f"[Pipeline:single] News stage failed: {exc}")
                result.stages.append(StageResult("news", success=False, error=str(exc)))

        # ── Stage 3: Risk score ───────────────────────────────────────────────
        try:
            risk_score = await self._risk_engine.score_project(project_id, db)
            await db.commit()
            result.stages.append(
                StageResult("scoring", success=True, records=1)
            )
            logger.info(
                f"[Pipeline:single] Project {project_id} scored: "
                f"{risk_score.composite_score:.1f} ({risk_score.risk_band.value})"
            )
        except Exception as exc:
            logger.error(f"[Pipeline:single] Scoring stage failed: {exc}")
            result.stages.append(StageResult("scoring", success=False, error=str(exc)))

        result.finished_at = datetime.now(timezone.utc)
        return result

    # ── Internal stage runners ────────────────────────────────────────────────

    async def _run_rera_stage(
        self, db: AsyncSession, cities: list[str]
    ) -> StageResult:
        total = 0
        try:
            async with RERAScraperMaharashtra() as rera:
                for city in cities:
                    summary = await rera.scrape_and_store(db, city=city, max_pages=5)
                    total += summary.get("created", 0) + summary.get("updated", 0)
                    logger.info(
                        f"[Pipeline] RERA {city}: "
                        f"created={summary.get('created', 0)} "
                        f"updated={summary.get('updated', 0)} "
                        f"errors={summary.get('errors', 0)}"
                    )
            return StageResult("rera", success=True, records=total)
        except Exception as exc:
            logger.error(f"[Pipeline] RERA stage error: {exc}")
            return StageResult("rera", success=False, error=str(exc), records=total)

    async def _run_mca_stage(self, db: AsyncSession) -> StageResult:
        """Update all developers that have a CIN with MCA data."""
        total = 0
        try:
            result = await db.execute(
                select(Developer).where(Developer.mca_cin.isnot(None))
            )
            developers = list(result.scalars().all())
            logger.info(f"[Pipeline] MCA: enriching {len(developers)} developers")

            async with MCAScraper() as mca:
                for dev in developers:
                    try:
                        company_data = await mca.get_company_details(dev.mca_cin)
                        stress = await mca.check_financial_stress(company_data)
                        dev.financial_stress_score = stress
                        total += 1
                    except Exception as exc:
                        logger.warning(
                            f"[Pipeline] MCA failed for {dev.mca_cin}: {exc}"
                        )

            await db.commit()
            return StageResult("mca", success=True, records=total)
        except Exception as exc:
            logger.error(f"[Pipeline] MCA stage error: {exc}")
            return StageResult("mca", success=False, error=str(exc), records=total)

    async def _run_news_stage(self, db: AsyncSession) -> StageResult:
        """Fetch and store news for all developers."""
        total = 0
        try:
            result = await db.execute(select(Developer))
            developers = list(result.scalars().all())
            logger.info(
                f"[Pipeline] News: scanning {len(developers)} developers"
            )

            async with NewsScraper() as news:
                for dev in developers:
                    try:
                        count = await news.scrape_and_store_news(dev, db)
                        total += count
                    except Exception as exc:
                        logger.warning(
                            f"[Pipeline] News failed for {dev.name}: {exc}"
                        )

            return StageResult("news", success=True, records=total)
        except Exception as exc:
            logger.error(f"[Pipeline] News stage error: {exc}")
            return StageResult("news", success=False, error=str(exc), records=total)

    async def _run_scoring_stage(
        self, db: AsyncSession, cities: list[str]
    ) -> StageResult:
        """Regenerate risk scores for all projects in the given cities."""
        total = 0
        errors = 0
        try:
            city_filter = [c.lower() for c in cities]
            result = await db.execute(select(Project))
            all_projects = list(result.scalars().all())

            target = [
                p for p in all_projects
                if p.city.lower() in city_filter
            ]
            logger.info(
                f"[Pipeline] Scoring {len(target)} projects across {cities}"
            )

            for project in target:
                try:
                    await self._risk_engine.score_project(project.id, db)
                    total += 1
                    if total % 10 == 0:
                        await db.commit()
                        logger.info(f"[Pipeline] Scored {total}/{len(target)} projects")
                except Exception as exc:
                    logger.warning(
                        f"[Pipeline] Scoring failed for project "
                        f"{project.id} ({project.name}): {exc}"
                    )
                    errors += 1

            await db.commit()
            logger.info(
                f"[Pipeline] Scoring complete: {total} scored, {errors} errors"
            )
            return StageResult("scoring", success=errors == 0, records=total)
        except Exception as exc:
            logger.error(f"[Pipeline] Scoring stage error: {exc}")
            return StageResult(
                "scoring", success=False, error=str(exc), records=total
            )


# ── CLI entry point ───────────────────────────────────────────────────────────

async def _cli_main() -> None:
    import sys

    from app.database import AsyncSessionLocal

    cities = sys.argv[1:] if len(sys.argv) > 1 else ["Mumbai", "Bengaluru"]
    logger.info(f"CLI: running full refresh for cities: {cities}")

    async with AsyncSessionLocal() as db:
        pipeline = DataPipeline()
        result = await pipeline.run_full_refresh(db, cities=cities)

    import json
    print(json.dumps(result.summary(), indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    asyncio.run(_cli_main())

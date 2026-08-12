"""Scheduled retraining for the course-isolated student-knowledge DyGKT predictor."""

from __future__ import annotations

import asyncio
import logging

from app.engines.gnn.trainer import train_from_repository
from app.tasks.registry import scheduled_task

logger = logging.getLogger(__name__)


@scheduled_task("retrain_tgnn", trigger="cron", hour=3, minute=20)
async def retrain_tgnn() -> None:
    """Refresh the checkpoint before daily profiles and daily questions run."""

    try:
        result = await asyncio.to_thread(train_from_repository)
        logger.info("[DyGKT] scheduled retraining finished: %s", result)
    except ValueError as exc:
        # Sparse deployments stay in the clearly-labelled cold-start path.
        logger.info("[DyGKT] scheduled retraining skipped: %s", exc)
    except Exception:
        logger.exception("[DyGKT] scheduled retraining failed")

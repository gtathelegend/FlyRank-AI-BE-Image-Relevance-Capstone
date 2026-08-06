from typing import List, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, date
from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.image import Image, ImageStatus
from app.models.job import BatchJob, JobStatus, JobType
from app.models.cost import CostLog, OperationType
from app.models.suggestion import Suggestion
from app.schemas.analytics import (
    SystemMetricsResponse,
    CostMetricsResponse,
    JobMetricsResponse,
    DailyUsageSchema,
    MonthlyUsageSchema
)


class AnalyticsService:
    """Core analytics engine executing aggregation queries across logs, jobs, images, and suggestions."""

    async def get_system_metrics(self, db: AsyncSession) -> SystemMetricsResponse:
        """Calculates system-wide analytics summary metrics."""
        logger.info("Computing system-wide analytics metrics...")

        # 1. Images processed count
        img_stmt = select(func.count()).select_from(Image).where(Image.status == ImageStatus.PROCESSED)
        processed_images = (await db.execute(img_stmt)).scalar() or 0

        # 2. Cost logs aggregation
        cost_stmt = select(CostLog)
        cost_logs = list((await db.execute(cost_stmt)).scalars().all())

        vision_calls = 0
        embedding_calls = 0
        mismatch_calls = 0
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = Decimal("0.0")

        daily_map = defaultdict(lambda: {"in": 0, "out": 0, "cost": Decimal("0.0"), "ops": 0})
        monthly_map = defaultdict(lambda: {"in": 0, "out": 0, "cost": Decimal("0.0"), "ops": 0})

        for log in cost_logs:
            if log.operation_type == OperationType.VISION_ANALYSIS:
                vision_calls += 1
            elif log.operation_type == OperationType.EMBEDDING_GEN:
                embedding_calls += 1
            elif log.operation_type == OperationType.MISMATCH_GUARD_VERIFICATION:
                mismatch_calls += 1

            total_input_tokens += log.input_tokens
            total_output_tokens += log.output_tokens
            cost_val = Decimal(str(log.estimated_cost_usd or 0))
            total_cost += cost_val

            dt = log.created_at
            day_str = dt.strftime("%Y-%m-%d") if dt else datetime.utcnow().strftime("%Y-%m-%d")
            month_str = dt.strftime("%Y-%m") if dt else datetime.utcnow().strftime("%Y-%m")

            daily_map[day_str]["in"] += log.input_tokens
            daily_map[day_str]["out"] += log.output_tokens
            daily_map[day_str]["cost"] += cost_val
            daily_map[day_str]["ops"] += 1

            monthly_map[month_str]["in"] += log.input_tokens
            monthly_map[month_str]["out"] += log.output_tokens
            monthly_map[month_str]["cost"] += cost_val
            monthly_map[month_str]["ops"] += 1

        # 3. Batch jobs aggregation
        job_stmt = select(BatchJob)
        jobs = list((await db.execute(job_stmt)).scalars().all())

        successful_jobs = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
        failed_jobs = sum(1 for j in jobs if j.status == JobStatus.FAILED)

        # Average latency (duration) calculation across finished jobs
        latencies = []
        for j in jobs:
            if j.status in (JobStatus.COMPLETED, JobStatus.FAILED) and j.created_at and j.updated_at:
                dur = (j.updated_at - j.created_at).total_seconds()
                if dur >= 0:
                    latencies.append(dur)

        avg_latency = float(sum(latencies) / len(latencies)) if latencies else 0.0

        # 4. Suggestions average similarity score
        sug_stmt = select(func.avg(Suggestion.raw_similarity_score))
        avg_similarity = float((await db.execute(sug_stmt)).scalar() or 0.0)

        # Build Daily and Monthly usage schemas
        daily_usage_list = [
            DailyUsageSchema(
                date=k,
                input_tokens=v["in"],
                output_tokens=v["out"],
                total_tokens=v["in"] + v["out"],
                cost_usd=round(float(v["cost"]), 6),
                operations_count=v["ops"]
            )
            for k, v in sorted(daily_map.items())
        ]

        monthly_usage_list = [
            MonthlyUsageSchema(
                month=k,
                input_tokens=v["in"],
                output_tokens=v["out"],
                total_tokens=v["in"] + v["out"],
                cost_usd=round(float(v["cost"]), 6),
                operations_count=v["ops"]
            )
            for k, v in sorted(monthly_map.items())
        ]

        return SystemMetricsResponse(
            images_processed=processed_images,
            vision_api_calls=vision_calls,
            embedding_api_calls=embedding_calls,
            mismatch_guard_api_calls=mismatch_calls,
            average_latency_seconds=round(avg_latency, 4),
            estimated_token_usage=total_input_tokens + total_output_tokens,
            estimated_cost_usd=round(float(total_cost), 6),
            successful_jobs=successful_jobs,
            failed_jobs=failed_jobs,
            average_processing_time_seconds=round(avg_latency, 4),
            average_similarity_score=round(avg_similarity, 4),
            daily_usage=daily_usage_list,
            monthly_usage=monthly_usage_list
        )

    async def get_cost_metrics(self, db: AsyncSession) -> CostMetricsResponse:
        """Calculates detailed financial costs and token usage breakdowns."""
        logger.info("Computing cost & token usage metrics...")

        cost_stmt = select(CostLog)
        cost_logs = list((await db.execute(cost_stmt)).scalars().all())

        total_input = 0
        total_output = 0
        total_cost = Decimal("0.0")

        cost_by_op = defaultdict(Decimal)
        cost_by_model = defaultdict(Decimal)
        daily_map = defaultdict(lambda: {"in": 0, "out": 0, "cost": Decimal("0.0"), "ops": 0})
        monthly_map = defaultdict(lambda: {"in": 0, "out": 0, "cost": Decimal("0.0"), "ops": 0})

        for log in cost_logs:
            total_input += log.input_tokens
            total_output += log.output_tokens
            cost_val = Decimal(str(log.estimated_cost_usd or 0))
            total_cost += cost_val

            op_key = log.operation_type.value if hasattr(log.operation_type, "value") else str(log.operation_type)
            cost_by_op[op_key] += cost_val
            cost_by_model[log.model_name] += cost_val

            dt = log.created_at
            day_str = dt.strftime("%Y-%m-%d") if dt else datetime.utcnow().strftime("%Y-%m-%d")
            month_str = dt.strftime("%Y-%m") if dt else datetime.utcnow().strftime("%Y-%m")

            daily_map[day_str]["in"] += log.input_tokens
            daily_map[day_str]["out"] += log.output_tokens
            daily_map[day_str]["cost"] += cost_val
            daily_map[day_str]["ops"] += 1

            monthly_map[month_str]["in"] += log.input_tokens
            monthly_map[month_str]["out"] += log.output_tokens
            monthly_map[month_str]["cost"] += cost_val
            monthly_map[month_str]["ops"] += 1

        daily_list = [
            DailyUsageSchema(
                date=k,
                input_tokens=v["in"],
                output_tokens=v["out"],
                total_tokens=v["in"] + v["out"],
                cost_usd=round(float(v["cost"]), 6),
                operations_count=v["ops"]
            )
            for k, v in sorted(daily_map.items())
        ]

        monthly_list = [
            MonthlyUsageSchema(
                month=k,
                input_tokens=v["in"],
                output_tokens=v["out"],
                total_tokens=v["in"] + v["out"],
                cost_usd=round(float(v["cost"]), 6),
                operations_count=v["ops"]
            )
            for k, v in sorted(monthly_map.items())
        ]

        return CostMetricsResponse(
            estimated_cost_usd=round(float(total_cost), 6),
            input_tokens=total_input,
            output_tokens=total_output,
            total_tokens=total_input + total_output,
            cost_by_operation={k: round(float(v), 6) for k, v in cost_by_op.items()},
            cost_by_model={k: round(float(v), 6) for k, v in cost_by_model.items()},
            daily_usage=daily_list,
            monthly_usage=monthly_list
        )

    async def get_job_metrics(self, db: AsyncSession) -> JobMetricsResponse:
        """Calculates batch job execution analytics and duration statistics."""
        logger.info("Computing batch job execution metrics...")

        job_stmt = select(BatchJob)
        jobs = list((await db.execute(job_stmt)).scalars().all())

        total = len(jobs)
        successful = 0
        failed = 0
        pending = 0
        running = 0
        jobs_by_type = defaultdict(int)

        durations = []

        for j in jobs:
            t_key = j.job_type.value if hasattr(j.job_type, "value") else str(j.job_type)
            jobs_by_type[t_key] += 1

            if j.status == JobStatus.COMPLETED:
                successful += 1
            elif j.status == JobStatus.FAILED:
                failed += 1
            elif j.status == JobStatus.PENDING:
                pending += 1
            elif j.status == JobStatus.RUNNING:
                running += 1

            if j.created_at and j.updated_at:
                dur = (j.updated_at - j.created_at).total_seconds()
                if dur >= 0:
                    durations.append(dur)

        success_rate = float(successful / total) if total > 0 else 1.0
        avg_dur = float(sum(durations) / len(durations)) if durations else 0.0

        return JobMetricsResponse(
            total_jobs=total,
            successful_jobs=successful,
            failed_jobs=failed,
            pending_jobs=pending,
            running_jobs=running,
            success_rate=round(success_rate, 4),
            average_latency_seconds=round(avg_dur, 4),
            average_processing_time_seconds=round(avg_dur, 4),
            jobs_by_type=dict(jobs_by_type)
        )


analytics_service = AnalyticsService()

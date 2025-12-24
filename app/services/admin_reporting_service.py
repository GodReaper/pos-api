from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from app.db import mongo
from app.models.order import Order
from app.repositories.table_repo import get_table_by_id
from app.repositories.area_repo import get_area_by_id
from app.repositories.user_repo import get_user_by_id


def _get_date_range(date_str: str | None) -> tuple[datetime, datetime, str]:
    """
    Resolve a logical date string into a [start, end) UTC range and a normalized key string.
    Supported:
      - "today" (default)
      - explicit ISO date: YYYY-MM-DD
    """
    if not date_str or date_str == "today":
        today = datetime.now(timezone.utc).date()
    else:
        try:
            today = datetime.fromisoformat(date_str).date()
        except ValueError:
            # Fallback to today on invalid format
            today = datetime.now(timezone.utc).date()

    start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    key = today.isoformat()
    return start, end, key


async def get_admin_summary(date: str | None = None) -> Dict[str, Any]:
    """Compute admin summary for a given date (based on payments)."""
    if mongo.db is None:
        return {
            "total_sales": 0.0,
            "running_tables_count": 0,
            "payment_mode_breakdown": {},
        }

    start, end, _ = _get_date_range(date)

    # Aggregate payments for the date
    pipeline = [
        {"$unwind": "$payments"},
        {
            "$match": {
                "payments.paid_at": {"$gte": start, "$lt": end},
            }
        },
        {
            "$group": {
                "_id": "$payments.method",
                "total": {"$sum": "$payments.amount"},
            }
        },
    ]

    total_sales = 0.0
    payment_mode_breakdown: Dict[str, float] = {}

    try:
        async for row in mongo.db.orders.aggregate(pipeline):
            method = str(row["_id"])
            total = float(row.get("total", 0.0))
            payment_mode_breakdown[method] = round(total, 2)
            total_sales += total
    except Exception:
        # On any aggregation error, fall back to zeros
        total_sales = 0.0
        payment_mode_breakdown = {}

    # Count running tables (orders that are not yet closed)
    try:
        running_statuses = ["open", "kot_printed", "billed"]
        running_tables_count = await mongo.db.orders.count_documents(
            {"status": {"$in": running_statuses}}
        )
    except Exception:
        running_tables_count = 0

    return {
        "total_sales": round(total_sales, 2),
        "running_tables_count": int(running_tables_count),
        "payment_mode_breakdown": payment_mode_breakdown,
    }


async def get_running_tables() -> List[Dict[str, Any]]:
    """Return list of currently running tables with area, biller, and current total."""
    if mongo.db is None:
        return []

    running_statuses = ["open", "kot_printed", "billed"]

    results: List[Dict[str, Any]] = []
    try:
        cursor = mongo.db.orders.find({"status": {"$in": running_statuses}})
        async for order_doc in cursor:
            order = Order.from_db(order_doc)

            table = await get_table_by_id(order.table_id)
            area = await get_area_by_id(order.area_id)
            biller = await get_user_by_id(order.created_by)

            results.append(
                {
                    "order_id": order.id,
                    "table_id": order.table_id,
                    "table_name": table.name if table else None,
                    "area_id": order.area_id,
                    "area_name": area.name if area else None,
                    "biller_id": biller.id if biller else None,
                    "biller_username": biller.username if biller else None,
                    "current_total": order.totals.grand_total,
                    "status": order.status,
                }
            )
    except Exception:
        return []

    return results


async def get_biller_performance(date: str | None = None) -> List[Dict[str, Any]]:
    """Compute totals per biller for a given date (based on payments)."""
    if mongo.db is None:
        return []

    start, end, _ = _get_date_range(date)

    # First group payments per (biller, order), then per biller
    pipeline = [
        {"$unwind": "$payments"},
        {
            "$match": {
                "payments.paid_at": {"$gte": start, "$lt": end},
            }
        },
        {
            "$group": {
                "_id": {"biller": "$created_by", "order_id": "$_id"},
                "order_total": {"$sum": "$payments.amount"},
            }
        },
        {
            "$group": {
                "_id": "$_id.biller",
                "total_sales": {"$sum": "$order_total"},
                "orders_count": {"$sum": 1},
            }
        },
    ]

    performance: List[Dict[str, Any]] = []

    try:
        async for row in mongo.db.orders.aggregate(pipeline):
            biller_oid = row["_id"]
            total_sales = float(row.get("total_sales", 0.0))
            orders_count = int(row.get("orders_count", 0))

            # Load biller user
            biller = await get_user_by_id(str(biller_oid))

            performance.append(
                {
                    "biller_id": biller.id if biller else str(biller_oid),
                    "biller_username": biller.username if biller else None,
                    "total_sales": round(total_sales, 2),
                    "orders_count": orders_count,
                }
            )
    except Exception:
        return []

    return performance



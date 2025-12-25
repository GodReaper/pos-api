from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from app.db import mongo
from app.models.order import Order
from app.repositories.table_repo import get_table_by_id
from app.repositories.area_repo import get_area_by_id
from app.repositories.user_repo import get_user_by_username, get_user_by_id
from bson import ObjectId


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


async def get_biller_ids_by_report_username(report_username: str) -> List[str]:
    """Get all biller user IDs who have this report_username assigned"""
    if mongo.db is None:
        return []
    
    try:
        cursor = mongo.db.users.find({
            "report_username": report_username,
            "role": "biller"
        })
        biller_ids = []
        async for user_doc in cursor:
            biller_ids.append(str(user_doc["_id"]))
        return biller_ids
    except Exception:
        return []


async def get_reports_by_username(report_username: str, date: str | None = None) -> Dict[str, Any]:
    """
    Get all admin-style reports filtered by report_username.
    Returns reports for all orders created by billers who have this report_username assigned.
    
    The report_username is a tag/category assigned to billers, not necessarily a user in the system.
    """
    # Get all biller IDs who have this report_username assigned
    biller_ids = await get_biller_ids_by_report_username(report_username)
    
    if not biller_ids:
        # No billers have this report_username assigned - return empty data
        return {
            "username": report_username,
            "summary": {
                "total_sales": 0.0,
                "running_tables_count": 0,
                "payment_mode_breakdown": {},
            },
            "running_tables": [],
            "biller_performance": [],
        }

    if mongo.db is None:
        return {
            "summary": {
                "total_sales": 0.0,
                "running_tables_count": 0,
                "payment_mode_breakdown": {},
            },
            "running_tables": [],
            "biller_performance": [],
        }

    start, end, _ = _get_date_range(date)

    # Convert biller_ids to ObjectIds for MongoDB query
    biller_oids = [ObjectId(bid) for bid in biller_ids]

    # Get summary (total sales and payment mode breakdown) for these billers
    summary_pipeline = [
        {"$match": {"created_by": {"$in": biller_oids}}},
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
        async for row in mongo.db.orders.aggregate(summary_pipeline):
            method = str(row["_id"])
            total = float(row.get("total", 0.0))
            payment_mode_breakdown[method] = round(total, 2)
            total_sales += total
    except Exception:
        total_sales = 0.0
        payment_mode_breakdown = {}

    # Count running tables for these billers
    try:
        running_statuses = ["open", "kot_printed", "billed"]
        running_tables_count = await mongo.db.orders.count_documents(
            {"created_by": {"$in": biller_oids}, "status": {"$in": running_statuses}}
        )
    except Exception:
        running_tables_count = 0

    summary = {
        "total_sales": round(total_sales, 2),
        "running_tables_count": int(running_tables_count),
        "payment_mode_breakdown": payment_mode_breakdown,
    }

    # Get running tables for these billers
    running_statuses = ["open", "kot_printed", "billed"]
    running_tables: List[Dict[str, Any]] = []

    try:
        cursor = mongo.db.orders.find({
            "created_by": {"$in": biller_oids},
            "status": {"$in": running_statuses}
        })
        async for order_doc in cursor:
            order = Order.from_db(order_doc)

            table = await get_table_by_id(order.table_id)
            area = await get_area_by_id(order.area_id)
            biller = await get_user_by_id(order.created_by)

            running_tables.append(
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
        running_tables = []

    # Get biller performance for these billers
    performance_pipeline = [
        {"$match": {"created_by": {"$in": biller_oids}}},
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

    biller_performance: List[Dict[str, Any]] = []

    try:
        async for row in mongo.db.orders.aggregate(performance_pipeline):
            biller_oid = row["_id"]
            total_sales_perf = float(row.get("total_sales", 0.0))
            orders_count = int(row.get("orders_count", 0))

            # Load biller user
            biller = await get_user_by_id(str(biller_oid))

            biller_performance.append(
                {
                    "biller_id": biller.id if biller else str(biller_oid),
                    "biller_username": biller.username if biller else None,
                    "total_sales": round(total_sales_perf, 2),
                    "orders_count": orders_count,
                }
            )
    except Exception:
        biller_performance = []

    return {
        "username": report_username,
        "summary": summary,
        "running_tables": running_tables,
        "biller_performance": biller_performance,
    }


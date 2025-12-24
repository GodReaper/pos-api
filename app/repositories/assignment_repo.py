from typing import Optional, List
from datetime import datetime
from app.db import mongo
from app.models.assignment import AssignmentInDB, Assignment
from bson import ObjectId


async def get_assignment_by_biller_id(biller_id: str) -> Optional[Assignment]:
    """Get assignment by biller ID"""
    if mongo.db is None:
        return None
    
    try:
        assignment_doc = await mongo.db.assignments.find_one({"biller_id": ObjectId(biller_id)})
        if assignment_doc:
            return Assignment.from_db(assignment_doc)
    except Exception:
        pass
    return None


async def get_assignment_by_id(assignment_id: str) -> Optional[Assignment]:
    """Get assignment by ID"""
    if mongo.db is None:
        return None
    
    try:
        assignment_doc = await mongo.db.assignments.find_one({"_id": ObjectId(assignment_id)})
        if assignment_doc:
            return Assignment.from_db(assignment_doc)
    except Exception:
        pass
    return None


async def get_all_assignments() -> List[Assignment]:
    """Get all assignments"""
    if mongo.db is None:
        return []
    
    cursor = mongo.db.assignments.find()
    assignments = []
    async for assignment_doc in cursor:
        assignments.append(Assignment.from_db(assignment_doc))
    return assignments


async def create_or_update_assignment(assignment_data: AssignmentInDB) -> Assignment:
    """Create or update an assignment (upsert based on biller_id)"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    assignment_dict = assignment_data.model_dump(by_alias=True, exclude={"id"})
    # Convert IDs to ObjectId
    assignment_dict["admin_id"] = ObjectId(assignment_dict["admin_id"])
    assignment_dict["biller_id"] = ObjectId(assignment_dict["biller_id"])
    assignment_dict["area_ids"] = [ObjectId(aid) for aid in assignment_dict["area_ids"]]
    
    # Check if assignment exists for this biller
    existing = await mongo.db.assignments.find_one({"biller_id": assignment_dict["biller_id"]})
    
    if existing:
        # Update existing assignment
        result = await mongo.db.assignments.update_one(
            {"biller_id": assignment_dict["biller_id"]},
            {"$set": {
                "admin_id": assignment_dict["admin_id"],
                "area_ids": assignment_dict["area_ids"]
            }}
        )
        updated_assignment = await mongo.db.assignments.find_one({"biller_id": assignment_dict["biller_id"]})
        return Assignment.from_db(updated_assignment)
    else:
        # Create new assignment
        result = await mongo.db.assignments.insert_one(assignment_dict)
        created_assignment = await mongo.db.assignments.find_one({"_id": result.inserted_id})
        return Assignment.from_db(created_assignment)


async def delete_assignment_by_biller_id(biller_id: str) -> bool:
    """Delete assignment by biller ID"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        result = await mongo.db.assignments.delete_one({"biller_id": ObjectId(biller_id)})
        return result.deleted_count > 0
    except Exception:
        return False


async def assignment_exists_for_biller(biller_id: str) -> bool:
    """Check if an assignment exists for a biller"""
    if mongo.db is None:
        return False
    
    try:
        count = await mongo.db.assignments.count_documents({"biller_id": ObjectId(biller_id)})
        return count > 0
    except Exception:
        return False


async def get_assigned_area_ids_for_biller(biller_id: str) -> List[str]:
    """Get list of area IDs assigned to a biller"""
    if mongo.db is None:
        return []
    
    try:
        assignment = await mongo.db.assignments.find_one({"biller_id": ObjectId(biller_id)})
        if assignment:
            return [str(aid) for aid in assignment.get("area_ids", [])]
        return []
    except Exception:
        return []


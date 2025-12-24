from typing import List, Optional
from fastapi import HTTPException, status
from app.models.table import TableCreate, TableUpdate, Table, TableInDB
from app.repositories.table_repo import (
    get_table_by_id,
    get_tables_by_area,
    get_tables_by_area_ids,
    create_table,
    update_table,
    delete_table,
    table_exists
)
from app.repositories.area_repo import area_exists


async def get_tables(area_id: str) -> List[Table]:
    """Get all tables for an area"""
    if not await area_exists(area_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )
    return await get_tables_by_area(area_id)




async def get_table(table_id: str) -> Table:
    """Get a table by ID"""
    table = await get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    return table


async def create_table_service(area_id: str, table_data: TableCreate) -> Table:
    """Create a new table in an area"""
    if not await area_exists(area_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )
    
    # Override area_id from path parameter
    table_dict = table_data.model_dump()
    table_dict["area_id"] = area_id
    
    table_in_db = TableInDB(**table_dict)
    return await create_table(table_in_db)


async def update_table_service(table_id: str, table_data: TableUpdate) -> Table:
    """Update a table"""
    if not await table_exists(table_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    # If area_id is being updated, verify it exists
    update_dict = table_data.model_dump(exclude_unset=True)
    if "area_id" in update_dict:
        if not await area_exists(update_dict["area_id"]):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Area not found"
            )
    
    updated_table = await update_table(table_id, update_dict)
    
    if not updated_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    return updated_table


async def delete_table_service(table_id: str) -> bool:
    """Delete a table"""
    if not await table_exists(table_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    return await delete_table(table_id)


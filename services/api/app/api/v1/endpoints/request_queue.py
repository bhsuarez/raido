from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime, timezone, timedelta
import json

from app.core.database import get_db
from app.models import RequestQueue, RequestType, RequestStatus

router = APIRouter()
logger = structlog.get_logger()

class QueueRequest(BaseModel):
    request_type: RequestType
    file_path: str
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration_sec: Optional[float] = None
    priority: int = 0
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class QueueResponse(BaseModel):
    id: int
    request_type: RequestType
    file_path: str
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration_sec: Optional[float] = None
    queue_order: int
    priority: int
    status: RequestStatus
    created_at: datetime
    requested_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    liquidsoap_request_id: Optional[int] = None
    notes: Optional[str] = None

@router.post("/add", response_model=QueueResponse)
async def add_to_queue(
    request: QueueRequest,
    db: AsyncSession = Depends(get_db)
):
    """Add a new request to the queue"""
    try:
        # Get the next queue order
        max_order_result = await db.execute(
            select(func.max(RequestQueue.queue_order)).where(
                RequestQueue.status == RequestStatus.PENDING
            )
        )
        max_order = max_order_result.scalar() or 0
        next_order = max_order + 1
        
        # Create the request
        queue_item = RequestQueue(
            request_type=request.request_type,
            file_path=request.file_path,
            title=request.title,
            artist=request.artist,
            album=request.album,
            duration_sec=request.duration_sec,
            queue_order=next_order,
            priority=request.priority,
            extra_data=json.dumps(request.metadata) if request.metadata else None,
            notes=request.notes
        )
        
        db.add(queue_item)
        await db.commit()
        await db.refresh(queue_item)
        
        logger.info("Added item to queue", 
                   id=queue_item.id, 
                   type=queue_item.request_type,
                   file_path=queue_item.file_path,
                   queue_order=queue_item.queue_order)
        
        return QueueResponse(**queue_item.__dict__)
        
    except Exception as e:
        logger.error("Failed to add item to queue", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add to queue: {str(e)}")

@router.get("/next", response_model=Optional[QueueResponse])
async def get_next_request(
    db: AsyncSession = Depends(get_db),
    request_type: Optional[RequestType] = None
):
    """Get the next pending request from the queue (for Liquidsoap)"""
    try:
        # Build query for next pending request
        query = select(RequestQueue).where(RequestQueue.status == RequestStatus.PENDING)
        
        if request_type:
            query = query.where(RequestQueue.request_type == request_type)
        
        # Order by priority (desc) then queue_order (asc)
        query = query.order_by(RequestQueue.priority.desc(), RequestQueue.queue_order.asc())
        
        result = await db.execute(query)
        next_request = result.scalar_one_or_none()
        
        if not next_request:
            return None
        
        # Mark as requested
        next_request.requested_at = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info("Next request retrieved", 
                   id=next_request.id,
                   type=next_request.request_type,
                   file_path=next_request.file_path)
        
        return QueueResponse(**next_request.__dict__)
        
    except Exception as e:
        logger.error("Failed to get next request", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get next request: {str(e)}")

@router.post("/{request_id}/start")
async def mark_request_started(
    request_id: int,
    liquidsoap_request_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Mark a request as started playing"""
    try:
        result = await db.execute(
            select(RequestQueue).where(RequestQueue.id == request_id)
        )
        request_item = result.scalar_one_or_none()
        
        if not request_item:
            raise HTTPException(status_code=404, detail="Request not found")
        
        request_item.status = RequestStatus.PLAYING
        request_item.started_at = datetime.now(timezone.utc)
        if liquidsoap_request_id:
            request_item.liquidsoap_request_id = liquidsoap_request_id
        
        await db.commit()
        
        logger.info("Request marked as started", 
                   id=request_id, 
                   liquidsoap_id=liquidsoap_request_id)
        
        return {"status": "success", "message": "Request marked as started"}
        
    except Exception as e:
        logger.error("Failed to mark request as started", error=str(e), request_id=request_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to mark request as started: {str(e)}")

@router.post("/{request_id}/complete")
async def mark_request_completed(
    request_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Mark a request as completed"""
    try:
        result = await db.execute(
            select(RequestQueue).where(RequestQueue.id == request_id)
        )
        request_item = result.scalar_one_or_none()
        
        if not request_item:
            raise HTTPException(status_code=404, detail="Request not found")
        
        request_item.status = RequestStatus.COMPLETED
        request_item.completed_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info("Request marked as completed", id=request_id)
        
        return {"status": "success", "message": "Request marked as completed"}
        
    except Exception as e:
        logger.error("Failed to mark request as completed", error=str(e), request_id=request_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to mark request as completed: {str(e)}")

@router.get("/list", response_model=List[QueueResponse])
async def list_queue(
    db: AsyncSession = Depends(get_db),
    status: Optional[RequestStatus] = None,
    limit: int = Query(default=50, le=200)
):
    """List queue items"""
    try:
        query = select(RequestQueue)
        
        if status:
            query = query.where(RequestQueue.status == status)
        
        query = query.order_by(RequestQueue.priority.desc(), RequestQueue.queue_order.asc()).limit(limit)
        
        result = await db.execute(query)
        items = result.scalars().all()
        
        return [QueueResponse(**item.__dict__) for item in items]
        
    except Exception as e:
        logger.error("Failed to list queue", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list queue: {str(e)}")

@router.post("/{request_id}/cancel")
async def cancel_request(
    request_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a pending request"""
    try:
        result = await db.execute(
            select(RequestQueue).where(
                and_(RequestQueue.id == request_id, RequestQueue.status == RequestStatus.PENDING)
            )
        )
        request_item = result.scalar_one_or_none()
        
        if not request_item:
            raise HTTPException(status_code=404, detail="Pending request not found")
        
        request_item.status = RequestStatus.CANCELLED
        await db.commit()
        
        logger.info("Request cancelled", id=request_id)
        
        return {"status": "success", "message": "Request cancelled"}
        
    except Exception as e:
        logger.error("Failed to cancel request", error=str(e), request_id=request_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel request: {str(e)}")

@router.post("/clear")
async def clear_queue(
    status: RequestStatus = RequestStatus.PENDING,
    db: AsyncSession = Depends(get_db)
):
    """Clear queue of items with specified status"""
    try:
        result = await db.execute(
            update(RequestQueue)
            .where(RequestQueue.status == status)
            .values(status=RequestStatus.CANCELLED)
        )
        
        count = result.rowcount
        await db.commit()
        
        logger.info("Queue cleared", status=status, count=count)
        
        return {"status": "success", "message": f"Cleared {count} items", "count": count}
        
    except Exception as e:
        logger.error("Failed to clear queue", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear queue: {str(e)}")
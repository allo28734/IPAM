"""
Discovery Profiles API Router.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_admin
from app.schemas.discovery_profile import DiscoveryProfileCreate, DiscoveryProfileUpdate, DiscoveryProfileResponse
from app.services.discovery_profile_service import DiscoveryProfileService, DiscoveryProfileNotFoundError, DiscoveryProfileServiceError

router = APIRouter(
    prefix="/discovery-profiles",
    tags=["Discovery Profiles"],
    dependencies=[Depends(get_current_active_admin)],  # Protect entire router
)

@router.post("", response_model=DiscoveryProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_in: DiscoveryProfileCreate,
    db: AsyncSession = Depends(get_db)
):
    service = DiscoveryProfileService(db)
    try:
        return await service.create_profile(profile_in)
    except DiscoveryProfileServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[DiscoveryProfileResponse])
async def list_profiles(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    service = DiscoveryProfileService(db)
    return await service.list_profiles(skip=skip, limit=limit)

@router.get("/{profile_id}", response_model=DiscoveryProfileResponse)
async def get_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db)
):
    service = DiscoveryProfileService(db)
    try:
        return await service.get_profile(profile_id)
    except DiscoveryProfileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{profile_id}", response_model=DiscoveryProfileResponse)
async def update_profile(
    profile_id: int,
    profile_in: DiscoveryProfileUpdate,
    db: AsyncSession = Depends(get_db)
):
    service = DiscoveryProfileService(db)
    try:
        return await service.update_profile(profile_id, profile_in)
    except DiscoveryProfileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DiscoveryProfileServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db)
):
    service = DiscoveryProfileService(db)
    try:
        await service.delete_profile(profile_id)
    except DiscoveryProfileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


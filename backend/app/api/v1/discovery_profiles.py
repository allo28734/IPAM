"""
Discovery Profiles API Router.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_admin
from app.schemas.discovery_profile import DiscoveryProfileCreate, DiscoveryProfileUpdate, DiscoveryProfileResponse
from app.services.discovery_profile_service import DiscoveryProfileService, DiscoveryProfileNotFoundError, DiscoveryProfileServiceError

router = APIRouter(
    prefix="/discovery-profiles",
    tags=["Discovery Profiles"],
    dependencies=[Depends(get_current_active_admin)],  # Protect entire router
)

@router.post("", response_model=DiscoveryProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_in: DiscoveryProfileCreate,
    db: Session = Depends(get_db)
):
    service = DiscoveryProfileService(db)
    try:
        return service.create_profile(profile_in)
    except DiscoveryProfileServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[DiscoveryProfileResponse])
def list_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    service = DiscoveryProfileService(db)
    return service.list_profiles(skip=skip, limit=limit)

@router.get("/{profile_id}", response_model=DiscoveryProfileResponse)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db)
):
    service = DiscoveryProfileService(db)
    try:
        return service.get_profile(profile_id)
    except DiscoveryProfileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{profile_id}", response_model=DiscoveryProfileResponse)
def update_profile(
    profile_id: int,
    profile_in: DiscoveryProfileUpdate,
    db: Session = Depends(get_db)
):
    service = DiscoveryProfileService(db)
    try:
        return service.update_profile(profile_id, profile_in)
    except DiscoveryProfileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DiscoveryProfileServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db)
):
    service = DiscoveryProfileService(db)
    try:
        service.delete_profile(profile_id)
    except DiscoveryProfileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

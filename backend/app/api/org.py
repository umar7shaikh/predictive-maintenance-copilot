"""Organization / site / membership endpoints (Phase 7).

Additive multi-tenant groundwork: every user belongs to an organization, sites group
machines, and roles gate who may mutate data. Row-level isolation across all existing
queries is the remaining hardening step (a single deployment is one org today).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Machine, Organization, Role, Site, User
from app.schemas import (
    MachineSiteUpdate,
    MemberOut,
    OrganizationOut,
    RoleUpdate,
    SiteCreate,
    SiteOut,
)
from app.security import get_current_user, require_role

router = APIRouter(prefix="/api/org", tags=["organization"])

_VALID_ROLES = {Role.OWNER, Role.MANAGER, Role.OPERATOR, Role.AUDITOR}


def _user_org(db: Session, user: User) -> Organization:
    org = db.get(Organization, user.org_id) if user.org_id else None
    if not org:
        raise HTTPException(status_code=404, detail="No organization for user")
    return org


@router.get("", response_model=OrganizationOut)
def get_org(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return _user_org(db, current)


@router.get("/sites", response_model=list[SiteOut])
def list_sites(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return (
        db.query(Site).filter(Site.org_id == current.org_id).order_by(Site.name).all()
    )


@router.post("/sites", response_model=SiteOut)
def create_site(
    payload: SiteCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_role(Role.MANAGER)),
):
    site = Site(org_id=current.org_id, **payload.model_dump())
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.get("/members", response_model=list[MemberOut])
def list_members(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return (
        db.query(User).filter(User.org_id == current.org_id).order_by(User.email).all()
    )


@router.patch("/members/{user_id}/role", response_model=MemberOut)
def set_role(
    user_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_role(Role.OWNER)),
):
    if payload.role not in _VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role: {payload.role}")
    member = db.get(User, user_id)
    if not member or member.org_id != current.org_id:
        raise HTTPException(status_code=404, detail="Member not found in your organization")
    member.role = payload.role
    db.commit()
    db.refresh(member)
    return member


@router.patch("/machines/{machine_id}/site")
def assign_machine_site(
    machine_id: int,
    payload: MachineSiteUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_role(Role.MANAGER)),
):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    if payload.site_id is not None:
        site = db.get(Site, payload.site_id)
        if not site or site.org_id != current.org_id:
            raise HTTPException(status_code=404, detail="Site not found in your organization")
    machine.site_id = payload.site_id
    db.commit()
    return {"id": machine.id, "site_id": machine.site_id}

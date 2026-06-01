"""Role-based access control tests (pure, no DB)."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models import Role
from app.security import require_role


def _user(role):
    return SimpleNamespace(role=role)


def test_role_ranks():
    assert Role.RANK[Role.OWNER] > Role.RANK[Role.MANAGER] > Role.RANK[Role.OPERATOR]
    assert Role.AUDITOR in Role.READ_ONLY


def test_auditor_is_read_only():
    dep = require_role(Role.OPERATOR)
    with pytest.raises(HTTPException) as e:
        dep(current=_user(Role.AUDITOR))
    assert e.value.status_code == 403


def test_operator_can_write_but_not_manage():
    assert require_role(Role.OPERATOR)(current=_user(Role.OPERATOR)).role == Role.OPERATOR
    with pytest.raises(HTTPException):
        require_role(Role.MANAGER)(current=_user(Role.OPERATOR))


def test_manager_cannot_do_owner_actions():
    assert require_role(Role.MANAGER)(current=_user(Role.MANAGER)).role == Role.MANAGER
    with pytest.raises(HTTPException):
        require_role(Role.OWNER)(current=_user(Role.MANAGER))


def test_owner_can_do_everything():
    for needed in (Role.OPERATOR, Role.MANAGER, Role.OWNER):
        assert require_role(needed)(current=_user(Role.OWNER)).role == Role.OWNER

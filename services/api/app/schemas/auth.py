from typing import Optional, List, Dict, Any, Set
from pydantic import BaseModel, Field


class AuthenticatedUser(BaseModel):
    """Represents an authenticated user resolved from an OIDC token."""

    sub: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None
    preferred_username: Optional[str] = None
    groups: List[str] = Field(default_factory=list)
    scopes: Set[str] = Field(default_factory=set)
    permissions: Set[str] = Field(default_factory=set)
    is_authenticated: bool = False
    raw_claims: Dict[str, Any] = Field(default_factory=dict)

    def has_group(self, *expected_groups: str) -> bool:
        """Return True if the user belongs to any of the expected groups."""

        cleaned_groups = {group.strip() for group in expected_groups if group}
        if not cleaned_groups:
            return False
        return bool(cleaned_groups.intersection(set(self.groups)))

    def has_scope(self, scope: str) -> bool:
        """Return True if the user has the provided OAuth scope."""

        return scope in self.scopes

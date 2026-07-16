from fastapi import APIRouter

from app.api.v1.routes.dpdp import (
    analytics,
    audit,
    auth_dpdp,
    consents as dpdp_consents,
    forms,
    notifications,
    org_api_keys,
    orgs,
    public_consent,
    reconsent,
    users,
    versions,
)


def create_v1_router() -> APIRouter:
    router = APIRouter(prefix="/v1")

    router.include_router(orgs.router)
    router.include_router(org_api_keys.router)
    #router.include_router(users.router)
    router.include_router(auth_dpdp.router)
    router.include_router(forms.router)
    router.include_router(versions.router)
    router.include_router(dpdp_consents.router)
    router.include_router(public_consent.router)
    #router.include_router(reconsent.router)
    #router.include_router(audit.router)
    #router.include_router(analytics.router)
    #router.include_router(notifications.router)

    return router

"""FastAPI entrypoint. Run with: uvicorn app.main:app --reload"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .ai.llm import LlmBriefProvider
from .ai.schema import AccountBrief
from .ai.service import BriefService
from .config import Settings, load_settings
from .crm_service import CrmService, Sort, View
from .repository import CrmRepository, NotFoundError
from .schemas import (
    AccountDetail,
    AccountListItem,
    CompleteFollowUpRequest,
    Dashboard,
    InteractionResult,
    LogInteractionRequest,
    SystemInfo,
)

logging.basicConfig(level=logging.INFO)


def create_app(settings: Settings | None = None, llm: object | None = None) -> FastAPI:
    settings = settings or load_settings()
    if llm is None and settings.llm_enabled:
        llm = LlmBriefProvider(settings.llm_api_key or "", settings.llm_base_url,
                               settings.llm_model, settings.llm_timeout_seconds)
    repo = CrmRepository(settings.database_path)
    briefs = BriefService(llm)  # type: ignore[arg-type]
    crm = CrmService(repo, briefs, settings.today)

    app = FastAPI(title="Micro-CRM API", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(PermissionError)
    async def forbidden(_: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def bad_value(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/api/system", response_model=SystemInfo)
    def system() -> SystemInfo:
        return SystemInfo(status="ok", ai_mode=briefs.mode,  # type: ignore[arg-type]
                          model=getattr(llm, "model", None), today=settings.today())

    @app.get("/api/dashboard", response_model=Dashboard)
    def dashboard() -> Dashboard:
        return crm.dashboard()

    @app.get("/api/accounts", response_model=list[AccountListItem])
    def list_accounts(
        view: View = "all",
        q: str = Query(default="", max_length=100),
        sort: Sort = "priority",
    ) -> list[AccountListItem]:
        return crm.list_accounts(view=view, query=q, sort=sort)

    @app.get("/api/accounts/{customer_id}", response_model=AccountDetail)
    def get_account(customer_id: str) -> AccountDetail:
        return crm.get_account(customer_id)

    @app.post("/api/accounts/{customer_id}/brief", response_model=AccountBrief)
    def generate_brief(customer_id: str, refresh: bool = False) -> AccountBrief:
        return crm.get_brief(customer_id, refresh=refresh)

    @app.post("/api/accounts/{customer_id}/follow-ups/complete", response_model=InteractionResult)
    def complete_follow_up(customer_id: str, body: CompleteFollowUpRequest) -> InteractionResult:
        interaction, account = crm.complete_follow_up(customer_id, body.note, body.channel)
        return InteractionResult(interaction=interaction, account=account)

    @app.post("/api/accounts/{customer_id}/interactions", response_model=InteractionResult, status_code=201)
    def log_interaction(customer_id: str, body: LogInteractionRequest) -> InteractionResult:
        interaction, account = crm.log_interaction(customer_id, body.type, body.notes,
                                                   body.contact_id, body.occurred_at)
        return InteractionResult(interaction=interaction, account=account)

    @app.delete("/api/interactions/{interaction_id}", response_model=AccountListItem)
    def undo_interaction(interaction_id: str) -> AccountListItem:
        return crm.undo_interaction(interaction_id)

    @app.post("/api/demo/reset", status_code=204)
    def reset_demo() -> None:
        repo.reset_to_seed()

    @app.get("/api/{rest:path}", include_in_schema=False)
    def unknown(rest: str) -> None:
        raise HTTPException(status_code=404, detail=f"Unknown endpoint /api/{rest}")

    return app


app = create_app()

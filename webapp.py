import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from agent.openclaw_adapter import simulate_openclaw_agent
from app import process_input


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

APP_TITLE = "Intent Guard"
APP_DESCRIPTION = (
    "Intent Guard sits between user intent and trading execution, intercepting "
    "instructions before they reach OpenClaw or downstream financial systems."
)
DEMO_USERNAME = os.getenv("APP_DEMO_USERNAME", "demo@intentguard.ai")
DEMO_PASSWORD = os.getenv("APP_DEMO_PASSWORD", "intentguard123")
SESSION_SECRET = os.getenv("APP_SECRET_KEY", "intent-guard-dev-secret")


def create_app():
    app = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION)
    app.add_middleware(
        SessionMiddleware,
        secret_key=SESSION_SECRET,
        same_site="lax",
        session_cookie="intent_guard_session",
    )
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="home.html",
            context={
                "title": "Intent Guard",
                "user": request.session.get("user"),
                "app_description": APP_DESCRIPTION,
            },
        )

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if _is_authenticated(request):
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "title": "Login",
                "user": None,
                "demo_username": DEMO_USERNAME,
                "demo_password": DEMO_PASSWORD,
            },
        )

    @app.post("/api/login")
    async def login(request: Request):
        payload = await request.json()
        username = str(payload.get("username", "")).strip().lower()
        password = str(payload.get("password", ""))

        if username != DEMO_USERNAME.lower() or password != DEMO_PASSWORD:
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        display_name = username.split("@")[0].replace(".", " ").title() or "Operator"
        request.session["user"] = {
            "name": display_name,
            "email": DEMO_USERNAME,
            "role": "Safety Operator",
        }
        request.session["chat_history"] = _default_chat_history()
        request.session["openclaw_config"] = {
            "agent_name": "OpenClaw Trader",
            "agent_id": "openclaw-sim-001",
            "broker": "Paper Broker",
            "mode": "simulation",
            "connected": False,
        }
        return JSONResponse({"ok": True, "redirect_url": "/dashboard"})

    @app.post("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        user = request.session.get("user")
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        history = request.session.get("chat_history") or _default_chat_history()
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "title": "Dashboard",
                "user": user,
                "messages": history,
            },
        )

    @app.post("/api/chat")
    async def chat(request: Request):
        _require_user(request)
        payload = await request.json()
        user_message = str(payload.get("message", "")).strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required.")

        history = request.session.get("chat_history") or _default_chat_history()
        history.append({"role": "user", "content": user_message})

        assistant_payload = _build_assistant_payload(user_message)
        history.append(assistant_payload)

        request.session["chat_history"] = history[-14:]
        return JSONResponse(
            {
                "ok": True,
                "message": assistant_payload,
                "summary": assistant_payload.get("summary"),
            }
        )

    @app.get("/openclaw", response_class=HTMLResponse)
    async def openclaw_page(request: Request):
        user = request.session.get("user")
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        config = request.session.get("openclaw_config") or {
            "agent_name": "OpenClaw Trader",
            "agent_id": "openclaw-sim-001",
            "broker": "Paper Broker",
            "mode": "simulation",
            "connected": False,
        }
        return templates.TemplateResponse(
            request=request,
            name="openclaw.html",
            context={
                "title": "OpenClaw Integration",
                "user": user,
                "config": config,
            },
        )

    @app.post("/api/openclaw/connect")
    async def openclaw_connect(request: Request):
        _require_user(request)
        payload = await request.json()
        config = {
            "agent_name": str(payload.get("agent_name", "OpenClaw Trader")).strip() or "OpenClaw Trader",
            "agent_id": str(payload.get("agent_id", "openclaw-sim-001")).strip() or "openclaw-sim-001",
            "broker": str(payload.get("broker", "Paper Broker")).strip() or "Paper Broker",
            "mode": str(payload.get("mode", "simulation")).strip() or "simulation",
            "connected": True,
        }
        request.session["openclaw_config"] = config
        return JSONResponse({"ok": True, "config": config})

    @app.post("/api/openclaw/simulate")
    async def openclaw_simulate(request: Request):
        _require_user(request)
        payload = await request.json()
        instruction = str(payload.get("instruction", "")).strip()
        if not instruction:
            raise HTTPException(status_code=400, detail="Instruction is required.")

        config = request.session.get("openclaw_config") or {}
        result = simulate_openclaw_agent(
            instruction,
            agent_id=config.get("agent_id", "openclaw-sim-001"),
            name=config.get("agent_name", "OpenClaw Trader"),
        )
        return JSONResponse({"ok": True, "result": result})

    return app


def _is_authenticated(request: Request):
    return bool(request.session.get("user"))


def _require_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def _default_chat_history():
    return [
        {
            "role": "assistant",
            "content": (
                "Welcome to Intent Guard. I can review financial instructions, flag risky or "
                "ambiguous trades, and show what OpenClaw would be allowed to execute."
            ),
            "summary": {
                "decision": "READY",
                "risk_level": "baseline",
                "allowed": 0,
                "blocked": 0,
                "clarification": 0,
            },
        }
    ]


def _build_assistant_payload(user_message):
    try:
        result = process_input(user_message)
        final = result.get("final", {})
        clarification = result.get("clarification", {})
        explainability = result.get("explainability", {})
        summary = {
            "decision": final.get("decision", "ASK"),
            "risk_level": explainability.get("summary", {}).get("risk_level", "unknown"),
            "allowed": len(final.get("allowed_actions", [])),
            "blocked": len(final.get("blocked_actions", [])),
            "clarification": len(final.get("clarification_actions", [])),
        }
        content = _format_assistant_message(final, clarification, explainability)
        return {
            "role": "assistant",
            "content": content,
            "summary": summary,
            "details": result,
        }
    except Exception as exc:
        return {
            "role": "assistant",
            "content": (
                "The safety engine could not complete a live evaluation right now. "
                f"Reason: {exc}"
            ),
            "summary": {
                "decision": "ERROR",
                "risk_level": "unknown",
                "allowed": 0,
                "blocked": 0,
                "clarification": 0,
            },
        }


def _format_assistant_message(final, clarification, explainability):
    decision = final.get("decision", "ASK")
    reasons = final.get("reasons", [])
    reason_text = "\n".join(f"- {reason}" for reason in reasons[:4]) or "- No blocking reasons were recorded."

    questions = clarification.get("questions", [])
    if questions:
        question_text = "\n".join(f"- {item['question']}" for item in questions[:3])
    else:
        question_text = "- No follow-up questions are needed."

    risk_level = explainability.get("summary", {}).get("risk_level", "unknown")

    return (
        f"Decision: {decision}\n"
        f"Risk level: {risk_level}\n\n"
        f"Safety reasons:\n{reason_text}\n\n"
        f"Clarification guidance:\n{question_text}"
    )


app = create_app()

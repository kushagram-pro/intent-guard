import os
from pathlib import Path
import time
from typing import List

import httpx
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
USER_STORE = {
    DEMO_USERNAME.lower(): {
        "name": "Demo Operator",
        "email": DEMO_USERNAME,
        "password": DEMO_PASSWORD,
        "role": "Safety Operator",
    }
}
MARKET_CACHE = {}
MARKET_CACHE_TTL_SECONDS = 60


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

    @app.get("/signup", response_class=HTMLResponse)
    async def signup_page(request: Request):
        if _is_authenticated(request):
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={
                "title": "Sign Up",
                "user": None,
            },
        )

    @app.post("/api/signup")
    async def signup(request: Request):
        payload = await request.json()
        name = str(payload.get("name", "")).strip()
        username = str(payload.get("username", "")).strip().lower()
        password = str(payload.get("password", ""))

        if not name:
            raise HTTPException(status_code=400, detail="Name is required.")
        if "@" not in username or "." not in username:
            raise HTTPException(status_code=400, detail="Please enter a valid email address.")
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
        if username in USER_STORE:
            raise HTTPException(status_code=409, detail="An account with this email already exists.")

        USER_STORE[username] = {
            "name": name,
            "email": username,
            "password": password,
            "role": "Safety Operator",
        }
        return JSONResponse({"ok": True, "redirect_url": "/login"})

    @app.post("/api/login")
    async def login(request: Request):
        payload = await request.json()
        username = str(payload.get("username", "")).strip().lower()
        password = str(payload.get("password", ""))
        account = USER_STORE.get(username)
        if not account or password != account.get("password"):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        request.session["user"] = {
            "name": account.get("name") or "Operator",
            "email": account.get("email") or username,
            "role": account.get("role") or "Safety Operator",
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
        pending = request.session.get("pending_clarification")
        effective_input = _merge_with_pending_clarification(pending, user_message)
        user_log_content = user_message
        if effective_input != user_message:
            user_log_content = f"{user_message}\n\n(Used as clarification for previous instruction.)"

        history.append({"role": "user", "content": user_log_content})

        assistant_payload = _build_assistant_payload(effective_input)
        history.append(assistant_payload)

        if _is_clarification_required(assistant_payload):
            request.session["pending_clarification"] = {
                "original_instruction": pending.get("original_instruction") if pending else effective_input,
                "assistant_question": _extract_primary_question(assistant_payload),
            }
        else:
            request.session.pop("pending_clarification", None)

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

    @app.get("/api/market/{symbol}")
    async def market_chart(symbol: str):
        cleaned_symbol = "".join(ch for ch in symbol.upper() if ch.isalnum() or ch in {".", "-"})
        if not cleaned_symbol:
            raise HTTPException(status_code=400, detail="Valid stock symbol is required.")

        cached = MARKET_CACHE.get(cleaned_symbol)
        now = time.time()
        if cached and now - cached["fetched_at"] < MARKET_CACHE_TTL_SECONDS:
            return JSONResponse({"ok": True, "symbol": cleaned_symbol, "points": cached["points"], "cached": True})

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{cleaned_symbol}"
        params = {"interval": "5m", "range": "1d"}
        headers = {"User-Agent": "IntentGuard/1.0 (+local-dev)"}

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            # Fallback to Stooq when Yahoo rejects free-rate requests.
            fallback_points = await _fetch_stooq_points(cleaned_symbol)
            if fallback_points:
                MARKET_CACHE[cleaned_symbol] = {"fetched_at": now, "points": fallback_points}
                return JSONResponse({"ok": True, "symbol": cleaned_symbol, "points": fallback_points, "source": "stooq"})
            if cached:
                return JSONResponse({"ok": True, "symbol": cleaned_symbol, "points": cached["points"], "cached": True})
            demo_points = _build_demo_points(cleaned_symbol)
            return JSONResponse({"ok": True, "symbol": cleaned_symbol, "points": demo_points, "source": "demo"})

        result = (payload.get("chart", {}).get("result") or [{}])[0]
        timestamps: List[int] = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quote.get("close") or []

        points = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            points.append({"t": int(ts), "c": float(close)})

        if not points:
            raise HTTPException(status_code=404, detail=f"No market data available for {cleaned_symbol}.")

        MARKET_CACHE[cleaned_symbol] = {"fetched_at": now, "points": points}
        return JSONResponse({"ok": True, "symbol": cleaned_symbol, "points": points})

    return app


async def _fetch_stooq_points(symbol: str):
    mapped_symbol = f"{symbol.lower()}.us"
    url = f"https://stooq.com/q/l/?s={mapped_symbol}&f=sd2t2ohlcv&h&e=csv"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, headers={"User-Agent": "IntentGuard/1.0 (+local-dev)"})
            response.raise_for_status()
            lines = response.text.strip().splitlines()
    except Exception:
        return []

    if len(lines) < 2:
        return []

    points = []
    for row in lines[1:]:
        cols = row.split(",")
        if len(cols) < 6:
            continue
        date_part = cols[1].strip()
        time_part = cols[2].strip() if len(cols) > 2 else "00:00:00"
        close = cols[6].strip() if len(cols) > 6 else ""
        if close in {"", "N/D"} or date_part in {"", "N/D"}:
            continue
        try:
            ts = int(time.mktime(time.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")))
            points.append({"t": ts, "c": float(close)})
        except Exception:
            continue
    return points[-120:]


def _build_demo_points(symbol: str):
    seed = sum(ord(ch) for ch in symbol)
    base_price = 80 + (seed % 220)
    now = int(time.time())
    points = []
    for idx in range(78):
        oscillation = ((idx % 9) - 4) * 0.18
        drift = idx * 0.03
        close = max(1.0, base_price + drift + oscillation)
        points.append({"t": now - (78 - idx) * 300, "c": round(close, 2)})
    return points


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


def _is_clarification_required(assistant_payload):
    summary = assistant_payload.get("summary", {})
    if summary.get("decision") != "ASK":
        return False
    return bool(summary.get("clarification", 0))


def _extract_primary_question(assistant_payload):
    details = assistant_payload.get("details", {})
    clarification = details.get("clarification", {})
    return clarification.get("primary_question", "")


def _merge_with_pending_clarification(pending, user_message):
    if not pending:
        return user_message
    original = str(pending.get("original_instruction", "")).strip()
    if not original:
        return user_message
    return f"{original}\nClarification from user: {user_message}"


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

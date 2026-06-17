from __future__ import annotations

import mimetypes
import os
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import identity, ingest, registry
from app.providers.telegram import TelegramProvider
from app.providers.webapp import WebappProvider
from app.providers.whatsapp import WhatsAppProvider
from app.schemas import SendRequest

_engine = create_engine(
    os.getenv("DATABASE_URL", "postgresql+psycopg://shepherd:shepherd@localhost:5432/shepherd")
)
_Session = sessionmaker(bind=_engine)

app = FastAPI(
    title="Channel Gateway",
    version="0.1.0",
    description="Multi-channel ingestion gateway (Telegram, Webapp; WhatsApp-ready).",
)

_telegram = TelegramProvider()
_webapp = WebappProvider()
registry.register(_telegram)
registry.register(_webapp)
registry.register(WhatsAppProvider())


def get_db():
    db = _Session()
    try:
        yield db
    finally:
        db.close()


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


@app.post("/telegram/webhook", tags=["telegram"])
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    update = await request.json()
    msg = update.get("message") or {}
    chat_id = str(msg.get("chat", {}).get("id", ""))

    # Contact share: bind channel_identities
    if "contact" in msg:
        contact = msg["contact"]
        phone = contact.get("phone_number", "")
        display = contact.get("first_name", "")
        identity.bind("telegram", chat_id, phone, db)
        db.commit()
        _telegram.send_message(chat_id, f"Thanks {display}! You're now registered.")
        return {"ok": True}

    # Resolve phone via channel_identities
    phone = identity.resolve_phone("telegram", chat_id, db)
    if phone is None:
        _telegram.request_contact(chat_id)
        return {"ok": True}

    display_name = msg.get("from", {}).get("first_name")
    req: dict = {"update": update, "phone": phone, "display_name": display_name}

    # Download media and upload to S3 before parse_inbound
    if "photo" in msg or "document" in msg:
        if "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            mime = "image/jpeg"
            ext = "jpg"
        else:
            doc = msg["document"]
            file_id = doc["file_id"]
            mime = doc.get("mime_type", "application/octet-stream")
            ext = (mimetypes.guess_extension(mime) or ".bin").lstrip(".")
        body = _telegram.download_media(file_id)
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        s3_key = f"inbox/telegram/{chat_id}/{ts}.{ext}"
        ingest.put_s3(s3_key, body, mime)
        req["s3_key"] = s3_key
        req["mime"] = mime

    payload = _telegram.parse_inbound(req)
    await ingest.forward(payload)
    return {"ok": True}


@app.post("/webapp/ingest", tags=["webapp"])
async def webapp_ingest(
    phone: str = Form(...),
    display_name: str | None = Form(None),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    req: dict = {"phone": phone, "display_name": display_name}

    if file is not None:
        body = await file.read()
        mime = file.content_type or "application/octet-stream"
        ext = (mimetypes.guess_extension(mime) or ".bin").lstrip(".")
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        s3_key = f"inbox/webapp/{phone}/{ts}.{ext}"
        ingest.put_s3(s3_key, body, mime)
        req["s3_key"] = s3_key
        req["mime"] = mime
        req["original_name"] = file.filename
    elif text:
        req["text"] = text
    else:
        raise HTTPException(status_code=400, detail="Provide either file or text")

    payload = _webapp.parse_inbound(req)
    await ingest.forward(payload)
    return {"ok": True}


@app.post("/send", tags=["outbound"])
def send_message(body: SendRequest):
    try:
        registry.send(body.channel_id, body.recipient, body.text, body.attachments)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}

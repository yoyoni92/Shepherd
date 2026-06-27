"""End-to-end Telegram simulator.

Acts *just like Telegram*: builds real aiogram `Update` objects (messages, callbacks,
contacts, voice/photo/video/document) and feeds them through the real dispatcher in
`app.main`. The Telegram Bot API is mocked at the session boundary (`Recorder`), so every
outgoing call the bot makes - `sendMessage`, `sendDice`, `sendDocument`, `setMyCommands`,
`getFile`, file download - is captured instead of hitting api.telegram.org. Fleet API is
mocked separately with respx. Nothing real leaves the process.
"""

from __future__ import annotations

import datetime
from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.types import (
    CallbackQuery,
    Chat,
    Contact,
    Document,
    File,
    Location,
    Message,
    PhotoSize,
    Update,
    User,
    Video,
    Voice,
)

# A syntactically valid bot token (never used to reach Telegram - the session is mocked).
TOKEN = "123456789:AAHe2eTESTTOKENabcdefghijklmnopqrstuvwx"

_NOW = datetime.datetime(2026, 6, 26, 10, 0, 0)


class Recorder(BaseSession):
    """Mocked Telegram transport. Records every Bot API method and returns canned results."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[Any] = []

    async def make_request(self, bot, method, timeout=None):  # noqa: ANN001
        self.requests.append(method)
        if type(method).__name__ == "GetFile":
            return File(file_id="f", file_unique_id="f", file_path="files/file.bin")
        # send_message / send_dice / send_document / set_my_commands / answer_callback:
        # the flows ignore the return value, so a truthy stand-in is enough.
        return True

    async def stream_content(  # noqa: ANN201
        self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True
    ):
        yield b"rawbytes"

    async def close(self) -> None:
        pass

    # --- assertion helpers ---
    def of(self, name: str) -> list[Any]:
        return [m for m in self.requests if type(m).__name__ == name]

    def sent_texts(self) -> list[str]:
        return [m.text for m in self.of("SendMessage")]

    def sent_to(self, chat_id: int) -> list[str]:
        return [m.text for m in self.of("SendMessage") if m.chat_id == chat_id]

    def dice_count(self) -> int:
        return len(self.of("SendDice"))

    def documents(self) -> list[Any]:
        return self.of("SendDocument")

    def reset(self) -> None:
        self.requests.clear()


class TelegramSim:
    """Drives the dispatcher with real Updates, one helper per kind of user action."""

    def __init__(self, bot: Bot, rec: Recorder, dispatcher) -> None:  # noqa: ANN001
        self.bot = bot
        self.rec = rec
        self.dp = dispatcher
        self._n = 0

    def _id(self) -> int:
        self._n += 1
        return self._n

    def _message(self, chat_id: int, **fields: Any) -> Message:
        return Message(
            message_id=self._id(),
            date=_NOW,
            chat=Chat(id=chat_id, type="private"),
            from_user=User(id=chat_id, is_bot=False, first_name="user"),
            **fields,
        )

    async def _feed(self, **update_fields: Any) -> None:
        await self.dp.feed_update(self.bot, Update(update_id=self._id(), **update_fields))

    # --- user actions (exactly what Telegram would deliver) ---
    async def text(self, chat_id: int, body: str) -> None:
        await self._feed(message=self._message(chat_id, text=body))

    async def command(self, chat_id: int, command: str) -> None:
        await self._feed(message=self._message(chat_id, text=f"/{command}"))

    async def start(self, chat_id: int) -> None:
        await self._feed(message=self._message(chat_id, text="/start"))

    async def tap(self, chat_id: int, data: str) -> None:
        cb = CallbackQuery(
            id=str(self._id()),
            from_user=User(id=chat_id, is_bot=False, first_name="user"),
            chat_instance="ci",
            message=self._message(chat_id, text="menu"),
            data=data,
        )
        await self._feed(callback_query=cb)

    async def share_contact(self, chat_id: int, phone: str) -> None:
        contact = Contact(phone_number=phone, user_id=chat_id, first_name="user")
        await self._feed(message=self._message(chat_id, contact=contact))

    async def share_location(self, chat_id: int, lat: float, lon: float) -> None:
        loc = Location(latitude=lat, longitude=lon)
        await self._feed(message=self._message(chat_id, location=loc))

    async def voice(self, chat_id: int) -> None:
        await self._feed(
            message=self._message(
                chat_id, voice=Voice(file_id="voiceid", file_unique_id="vu", duration=3)
            )
        )

    async def photo(self, chat_id: int) -> None:
        sizes = [PhotoSize(file_id="photoid", file_unique_id="pu", width=100, height=100)]
        await self._feed(message=self._message(chat_id, photo=sizes))

    async def video(self, chat_id: int) -> None:
        await self._feed(
            message=self._message(
                chat_id,
                video=Video(
                    file_id="videoid", file_unique_id="vvu", width=10, height=10, duration=5
                ),
            )
        )

    async def document(self, chat_id: int, file_name: str = "doc.pdf") -> None:
        doc = Document(file_id="docid", file_unique_id="du", file_name=file_name)
        await self._feed(message=self._message(chat_id, document=doc))

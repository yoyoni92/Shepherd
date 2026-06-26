# Research: Telegram location capture & "one-time allow"

**Question:** Can a Telegram bot get a user's location once ("allow once") and then
use it for later actions without re-prompting - ideally without the user really
noticing? Context: we want location attached to every DB-writing bot action,
admin-only, optional.

## TL;DR

- **There is no silent/background location in Telegram.** Every mechanism is
  user-initiated and visible at least once. A bot never sees the user's IP either
  (long-polling), so there's no fallback.
- There are **two families** of location access, and the "one-time allow" you heard
  about belongs to the second:
  1. **Plain chat bot (Bot API):** only **one-shot** shares. No persistent grant.
  2. **Mini App / Web App (Bot API 8.0, Nov 2024):** a real **persistent permission**
     via `LocationManager` - but it only works **while the Mini App is open**, and
     requires building a Mini App.

## 1. Plain chat bot (what we have today)

The bot is a long-polling chat bot. Its only location inputs:

- **`request_location` reply-keyboard button** - user taps "Share location", bot
  receives **one** `Message.location` (lat/lon) at that moment. Reply keyboards only
  (an inline button cannot request location). One-shot; no persistence; visible.
- **Live location** - the user manually shares live location via the attachment menu
  (📎 -> Location -> Share Live Location, for 15 min / 1 h / 8 h). A **bot cannot
  trigger** live-location sharing with a button; the user starts it themselves and
  sees it as "sharing" in the chat. In a direct chat the bot receives the initial
  pin and subsequent `edited_message` updates until `live_period` expires. (Some
  low-quality blogs claim bots get only one snapshot; the authoritative model is that
  edits are delivered in direct chats - but it's user-started and time-limited.)

Net: with the plain bot, the closest thing to "allow once" is **capture one
coordinate (or a live window) and cache it**, then attach that cached point to later
actions ourselves. The user still performs a visible share at least once, and the
point goes stale after the share / live window.

## 2. Mini App `LocationManager` - the actual "one-time allow" (Bot API 8.0)

Bot API 8.0 (Nov 2024) added geolocation to **Mini Apps** (the web view a bot can
open), via `WebApp.LocationManager`:

- `init()` then `getLocation(callback)` - requests/reads location. Permission is
  requested implicitly on first use.
- `isAccessGranted` (bool) - **"Shows whether permission to use location has been
  granted."** Access is **persistent once granted** (this is the "one-time allow").
- `openSettings()` - opens the location-access settings for the bot, to re-request if
  the user previously denied.
- `LocationData`: `latitude`, `longitude`, plus optional `altitude`, `course`,
  `speed`, and accuracy fields.
- Events: `locationManagerUpdated`, `locationRequested`.

**The catch:** a Mini App only runs **while the user has it open** (foreground). The
docs do **not** provide any background/closed access. So even with a persistent
permission, the bot can read location **only when the user is inside the Mini App** -
it does **not** silently cover ordinary chat-based actions (button taps, messages).
To benefit, the driver's actions would have to happen **inside the Mini App**, which
means building a Mini App (HTTPS-hosted web UI) and moving flows into it - a large
piece of work for a chat-first bot.

## 3. What this means for our requirement

| Want | Reality |
|---|---|
| Truly silent collection | **Impossible** on any Telegram surface. |
| "Allow once", then reuse | **Plain bot:** we cache a shared point/live window and reuse it - one visible share, stale after. **Mini App:** persistent permission, but only while the app is open. |
| Location on *every* DB action, no per-action prompt | **Plain bot:** yes, by attaching the last cached point to each write (best-effort, may be stale/empty). **Mini App:** only for actions done inside the app. |
| Admin-only, optional | Achievable either way - never echo it to the driver; null when absent. |

## Recommendation

For a chat-first bot where the WebUI is secondary, **don't build a Mini App just for
this.** Use the plain-bot path: obtain a location share **once** (a `request_location`
button at clock-in, or accept a user-started live location), **cache the last-known
point per chat**, and **attach it to every subsequent DB-writing action**, optional
(null if never shared), surfaced only in admin reports. Revisit the Mini App
`LocationManager` only if/when flows move into a Mini App for other reasons - then the
persistent "allow once" becomes genuinely useful.

## Sources

- [Telegram Mini Apps - LocationManager](https://core.telegram.org/bots/webapps)
- [Bot API changelog (8.0 geolocation)](https://core.telegram.org/bots/api-changelog)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Live geolocation (MTProto)](https://core.telegram.org/api/live-location)
- [aiogram editMessageLiveLocation](https://docs.aiogram.dev/en/latest/api/methods/edit_message_live_location.html)
- [Request location and a telegram bot (DEV)](https://dev.to/antonov_mike/request-location-and-telegram-bot-4emk)

"""Hebrew user-facing strings (ported from the n8n workflow)."""

ACCESS_DENIED = "הגישה למערכת מוגבלת. 🔒"

# Enrollment (no invites - match the shared phone to a driver/authorization)
CLAIM_REQUEST_PHONE = (
    "כדי להשלים את ההצטרפות, לחצ/י על הכפתור «📱 שיתוף מספר הטלפון» שמופיע למטה.\n"
    "⬇️⬇️⬇️"
)
CLAIM_SHARE_BUTTON = "📱 שיתוף מספר הטלפון"
# Shown when a driver types their number instead of tapping the share button. The
# number must be shared via the button so Telegram verifies it belongs to this account.
CLAIM_USE_BUTTON = (
    "⚠️ אין להקליד את המספר.\n"
    "כדי להצטרף יש ללחוץ על הכפתור «📱 שיתוף מספר הטלפון» שמופיע למטה 👇"
)
NOT_AUTHORIZED = (
    "❌ מספר הטלפון שלך לא מורשה לגישה למערכת.\n"
    "פנה/י למנהל כדי שיוסיף אותך כנהג פעיל."
)

WELCOME_DRIVER = (
    "🎉 ברוך/ה הבא/ה למערכת Shepherd!\n"
    "קיבלת הרשאת נהג. הפעולות הזמינות:\n\n"
    "⏱ כניסה/יציאה מעבודה\n"
    "🔧 דיווח תקלה ברכב\n"
    "🚨 דיווח תאונה\n"
    "✏️ עדכון פרטים אישיים\n"
    "📊 דוח נוכחות חודשי\n"
    "🚗 פרטי הרכב שלי\n\n"
    "אפשר לבחור מהתפריט למטה או דרך כפתור ☰."
)
WELCOME_ADMIN = (
    "🎉 ברוך/ה הבא/ה למערכת Shepherd!\n"
    "קיבלת הרשאת מנהל. הפעולות הזמינות:\n\n"
    "👥 נוכחות היום\n"
    "📢 שידור הודעה לנהגים\n"
    "🚗 סיכום צי\n"
    "✏️ עדכון נהג\n"
    "🔧 תחזוקה\n"
    "📄 סריקת מסמך\n\n"
    "אפשר לבחור מהתפריט למטה או דרך כפתור ☰."
)
WELCOME = {"driver": WELCOME_DRIVER, "admin": WELCOME_ADMIN}

# Menus
DRIVER_MENU_TITLE = "תפריט נהג - מה תרצה/י לעשות?"
ADMIN_MENU_TITLE = "תפריט מנהל - מה תרצה/י לעשות?"

# Clock
CLOCK_IN_OK = "✅ כניסה נרשמה בשעה {time}."
CLOCK_IN_ALREADY = "כבר נרשמת לכניסה היום."
CLOCK_OUT_OK = '✅ יציאה נרשמה בשעה {time}. סה"כ {hours} שעות.'
CLOCK_OUT_NO_OPEN = "לא נמצאה כניסה פתוחה להיום."
CLOCK_BLOCKED = "⛔ דיווח נוכחות אפשרי רק בין {start} ל-{end}."

# Vehicle issue
VEHICLE_ISSUE_PROMPT = "🔧 תאר/י את התקלה ברכב"
VEHICLE_ISSUE_DONE = "✅ התקלה נרשמה."
VEHICLE_ISSUE_FAILED = "⚠️ רישום התקלה נכשל. נסה/י שוב מאוחר יותר."
NO_VEHICLE = "לא נמצא רכב המשויך אליך."

# Accident
ACCIDENT_SAFE_PROMPT = "🚨 קודם כל - את/ה בטוח/ה?\n" "ודא/י שאת/ה במקום בטוח ועצרת, ואז המשך/י."
ACCIDENT_SAFE_BUTTON = "✅ אני במקום בטוח ועצרתי"
ACCIDENT_DESCRIPTION_PROMPT = "🎙️ תאר/י את האירוע בהודעה קולית או בטקסט."
ACCIDENT_ROAD_CLEAR_PROMPT = "🚗 כשהכביש פנוי, לחץ/י על הכפתור."
ACCIDENT_ROAD_CLEAR_BUTTON = "✅ הכביש פנוי"
ACCIDENT_INSURANCE_PROMPT = "📸 צלם/י את מסמך הביטוח של הצד השני."
ACCIDENT_DRIVER_LICENSE_PROMPT = "📸 צלם/י את רישיון הנהיגה של הצד השני."
ACCIDENT_CAR_LICENSE_PROMPT = "📸 צלם/י את רישיון הרכב של הצד השני."
ACCIDENT_VIDEOS_PROMPT = "🎥 שלח/י סרטון/ים של זירת התאונה. בסיום לחץ/י על הכפתור."
ACCIDENT_VIDEOS_DONE_BUTTON = "✅ סיום"
ACCIDENT_VIDEO_RECEIVED = "✅ הסרטון התקבל. שלח/י עוד, או לחץ/י על סיום."
ACCIDENT_MANAGER_PROMPT = "📞 צור/י קשר עם המנהל שלך עכשיו."
ACCIDENT_MANAGER_BUTTON = "✅ דיברתי עם המנהל"
ACCIDENT_COMPLETE = "✅ דיווח התאונה הושלם. המנהלים קיבלו עדכון."
ACCIDENT_ADMIN_NOTIFY = "🚨 דיווח תאונה חדש\n\nנהג: {driver}\nזמן: {time}"

# Update details / driver
UPDATE_FIELD_MENU = "מה תרצה/י לעדכן?"
UD_LICENSE_VALID = "📅 תוקף רישיון"
UD_LICENSE_NUMBER = "🔢 מספר רישיון"
UD_PHONE = "📱 טלפון"
UPDATE_VALUE_DATE = "הזן/י תאריך בפורמט DD/MM/YYYY"
UPDATE_VALUE_LICENSE = "הזן/י את מספר הרישיון"
UPDATE_VALUE_PHONE = "הזן/י מספר טלפון (לדוגמה 0501234567)"
UPDATE_DETAILS_DONE = "✅ הפרטים עודכנו."
UPDATE_DRIVER_DONE = "✅ פרטי הנהג עודכנו בהצלחה."
UPDATE_INVALID_DATE = "⚠️ תאריך לא תקין. נסה/י שוב בפורמט DD/MM/YYYY."
UPDATE_INVALID_PHONE = "⚠️ מספר טלפון לא תקין. נסה/י שוב."
UPDATE_INVALID_LICENSE = "⚠️ ערך לא תקין. נסה/י שוב."
UPDATE_DRIVER_PICK = "בחר/י נהג לעדכון"
UPDATE_DRIVER_SCAN_BTN = "📷 העלאת רישיון נהג (סריקה)"
UPDATE_DRIVER_SCAN_PROMPT = "📎 שלח/י צילום או קובץ של רישיון הנהג לניתוח."

# Attendance / summary
ATTENDANCE_TODAY_TITLE = "👥 נוכחות היום"
ATTENDANCE_EMPTY = "אין רישומי נוכחות להיום."
FLEET_SUMMARY_TITLE = "🚗 סיכום צי"
HEB_MONTHS = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]
ATTENDANCE_CSV_CAPTION = "נוכחות חודש {month}"
ATTENDANCE_CSV_FILENAME = "נוכחות {month} {year}.csv"

# My vehicle
MY_VEHICLE_TITLE = "🚗 הרכב שלי"

# Broadcast
BROADCAST_PROMPT = "📢 הקלד/י את ההודעה לשידור:"
BROADCAST_CONFIRM = "שולח ל-{count} נהגים. לאשר?"
BROADCAST_SEND = "✅ שלח"
BROADCAST_CANCEL = "❌ ביטול"
BROADCAST_SENT = "✅ ההודעה נשלחה."
BROADCAST_CANCELLED = "❌ השידור בוטל."

# Maintenance
MAINT_MENU = "🔧 תחזוקה - בחר/י פעולה:"
MAINT_OVERDUE_BTN = "⏰ תחזוקות באיחור"
MAINT_LOG_BTN = "📝 רישום תחזוקה"
MAINT_OVERDUE_TITLE = "🔧 תחזוקות באיחור"
MAINT_OVERDUE_EMPTY = "✅ אין תחזוקות באיחור."
MAINT_PICK_VEHICLE = "בחר/י רכב"
MAINT_PICK_TYPE = "בחר/י סוג תחזוקה"
MAINT_KM_PROMPT = 'הזן/י ק"מ בעת השירות:'
MAINT_KM_INVALID = '⚠️ ערך ק"מ לא תקין. נסה/י שוב.'
MAINT_LOGGED = "✅ אירוע התחזוקה נרשם."

# Document scan (admin, vision)
DOC_SCAN_PICK_TYPE = "📄 בחר/י סוג מסמך לסריקה:"
DOC_TYPE_VEHICLE_LICENSE = "🚗 רישיון רכב"
DOC_TYPE_INSURANCE = "🛡️ תעודת ביטוח"
DOC_TYPE_DRIVER_LICENSE = "🪪 רישיון נהג"
DOC_SCAN_PICK_DRIVER = "בחר/י נהג עבור רישיון הנהג:"
DOC_SCAN_SEND_FILE = "📎 שלח/י את צילום/קובץ המסמך."
DOC_SCAN_ANALYZING = "🔎 מנתח את המסמך..."
DOC_SCAN_CONFIRM_TITLE = "אנא אשר/י את הפרטים שחולצו:"
DOC_SCAN_CONFIRM_BTN = "✅ אישור"
DOC_SCAN_CANCEL_BTN = "❌ ביטול"
DOC_SCAN_APPLIED = "✅ המסמך עובד והרשומה עודכנה."
DOC_SCAN_REVIEW = "⚠️ לא נמצאה התאמה - נדרשת בדיקה ידנית."
DOC_SCAN_CANCELLED = "❌ הסריקה בוטלה."
DOC_SCAN_FAILED = "⚠️ לא הצלחתי לחלץ פרטים מהמסמך. נסה/י שוב."

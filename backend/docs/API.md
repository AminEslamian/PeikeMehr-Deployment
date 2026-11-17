# مستندات API — Safiremehr (Teacher Report)

منبع این سند خود کد است: `config/urls.py` و اپ‌های `accounts`، `reports`، `survey`، `blogs`، `tickets`، `adminpanel`.

- **Base URL (محلی):** `http://localhost:8000`
- **فرمت:** JSON مگر جایی که `multipart/form-data` ذکر شده باشد
- **اسلش انتهایی:** Django با تنظیم پیش‌فرض، مسیرها را با `/` می‌خواهد
- **احراز هویت پیش‌فرض DRF:** JWT (`Authorization: Bearer <access>`)
- **توکن:** Access حدود ۷ روز، Refresh حدود ۳۰ روز (`SIMPLE_JWT` در `config/settings.py`)
- **Swagger تعاملی:** `GET /api/docs/`
- **اسکیمای OpenAPI:** `GET /api/schema/`

هیچ مسیر `token/refresh` در پروژه ثبت نشده؛ رفرش‌توکن در پاسخ لاگین/ثبت‌نام برمی‌گردد ولی اندپوینت رفرش وجود ندارد.

`ProfileView` در `accounts/views.py` پیاده شده ولی به هیچ `urls.py` وصل نیست؛ بنابراین **اندپوینت پروفایل زنده نیست**.

---

## احراز هویت

| وضعیت | هدر |
|--------|------|
| عمومی (`AllowAny`) | لازم نیست |
| کاربر لاگین (`IsAuthenticated`) | `Authorization: Bearer <access>` |
| ادمین (`IsAdminUser`) | همان JWT؛ کاربر باید `is_staff=True` باشد |

شماره موبایل به فرمت `09xxxxxxxxx` ذخیره می‌شود. ورودی `+98...` به `0...` نرمال می‌شود.

---

## ۱) احراز هویت معلم — `/api/auth/`

همه این مسیرها **عمومی** هستند (`AllowAny`).

### `POST /api/auth/login/send-otp/`

ارسال OTP برای کاربری که از قبل ثبت شده.

**بدنه**

```json
{ "phone_number": "09123456789" }
```

| فیلد | نوع | الزامی | محدودیت |
|------|------|--------|----------|
| `phone_number` | string | بله | حداکثر ۱۱ کاراکتر |

**پاسخ‌ها**

| کد | معنی |
|----|------|
| `200` | `{ "detail": "OTP sent successfully." }` |
| `404` | شماره در سیستم نیست |
| `429` | کمتر از ۱ دقیقه از OTP قبلی گذشته |
| `400` | اعتبارسنجی فیلدها |

OTP چهاررقمی است، ۱ دقیقه اعتبار دارد، حداکثر ۵ تلاش اشتباه.

---

### `POST /api/auth/login/verify-otp/`

تأیید OTP و صدور JWT.

**بدنه**

```json
{
  "phone_number": "09123456789",
  "code": "1234"
}
```

**موفق `200`**

```json
{
  "access": "<jwt>",
  "refresh": "<jwt>",
  "teacher": {
    "id": 1,
    "phone_number": "09123456789",
    "first_name": "...",
    "last_name": "..."
  },
  "redirect_url": "/main/"
}
```

`redirect_url` برای سوپریوزر `/admin-panel/` است، وگرنه `/main/`.

**خطا `400`:** `{ "error_code": "..." }`  
مقادیر ممکن: `No active OTP found.` / `Too many attempts. Please request a new OTP.` / `OTP has expired.` / `Invalid OTP code.`

---

### `POST /api/auth/register/send-otp/`

ارسال OTP ثبت‌نام. اگر شماره یا کد ملی تکراری باشد رد می‌شود.

**بدنه**

```json
{
  "phone_number": "09123456789",
  "first_name": "علی",
  "last_name": "محمدی",
  "province": "تهران",
  "city": "تهران",
  "village": "",
  "school": "مدرسه نمونه",
  "grade": ["grade1"],
  "position": "teacher",
  "gender": "man",
  "national_id": "0012345678"
}
```

| فیلد | الزامی | توضیح |
|------|--------|--------|
| `phone_number` | بله | حداکثر ۱۱ |
| `first_name` / `last_name` | بله | حداکثر ۱۰۰ |
| `province` / `city` | بله | |
| `village` | خیر | می‌تواند خالی باشد |
| `school` | بله | حداکثر ۲۵۵ |
| `grade` | بله | آرایه غیرخالی از `Grade.value` |
| `position` | بله | مقادیر مدل: `teacher`, `Instructor`, `Amin Program Educator`, `Independent Preacher` |
| `gender` | بله | `man` یا `woman` |
| `national_id` | بله | حداکثر ۱۰ (مدل انتظار ۱۰ رقم دارد) |

**موفق `200`:** OTP ارسال شد.  
**خطا `400`:** شماره/کد ملی تکراری یا اعتبارسنجی.  
**خطا `429`:** محدودیت نرخ ۱ دقیقه‌ای.

---

### `POST /api/auth/register/verify-otp/`

همان فیلدهای ثبت‌نام به‌علاوه `code`. کاربر ساخته می‌شود و JWT برمی‌گردد.

**موفق `201`**

```json
{
  "access": "<jwt>",
  "refresh": "<jwt>",
  "teacher": {
    "id": 1,
    "phone_number": "09123456789",
    "first_name": "علی",
    "last_name": "محمدی"
  }
}
```

توجه: `_generate_tokens` خودش هم کلید `teacher` می‌سازد و ویو دوباره همان کلید را بازنویسی می‌کند.

---

## ۲) گزارش‌ها — `/api/reports/`

### `GET /api/reports/tags/` — عمومی

لیست تگ‌ها.

**پاسخ:** آرایه `{ "id": 1, "name": "..." }`

---

### `GET /api/reports/points/` — JWT

امتیازهای کاربر جاری.

```json
{
  "total": 120,
  "points": [
    { "id": 1, "score": 10, "reason": "...", "created_at": "..." }
  ]
}
```

---

### گزارش‌های معلم (`ReportViewSet`) — JWT + `multipart/form-data`

فقط گزارش‌های خود کاربر.

| متد | مسیر | توضیح |
|-----|------|--------|
| `GET` | `/api/reports/` | لیست |
| `POST` | `/api/reports/` | ایجاد |
| `GET` | `/api/reports/{id}/` | جزئیات |
| `PUT` | `/api/reports/{id}/` | جایگزینی کامل (سریالایزر خواندنی `ReportSerializer`) |
| `PATCH` | `/api/reports/{id}/` | به‌روزرسانی جزئی |
| `DELETE` | `/api/reports/{id}/` | حذف |

**ایجاد (`POST`) — `ReportCreateSerializer`**

| فیلد | نوع | الزامی |
|------|------|--------|
| `text` | string | بله |
| `tags` | لیست PK تگ | خیر |
| `media` | لیست فایل | خیر |

محدودیت رسانه: حداکثر ۲۰ فایل، هر فایل حداکثر ۳۰۰MB، فقط `image/*` یا `video/*`. تصویر در `ReportImage` و ویدیو در `ReportVideo` ذخیره می‌شود.

**پاسخ لیست/جزئیات (`ReportSerializer`)**

```json
{
  "id": 1,
  "text": "...",
  "tags": [{ "id": 1, "name": "..." }],
  "images": [{ "id": 1, "image": "/media/...", "created_at": "..." }],
  "videos": [{ "id": 1, "video": "/media/...", "created_at": "..." }],
  "created_at": "...",
  "updated_at": "..."
}
```

`PUT`/`PATCH` از `ReportSerializer` استفاده می‌کنند (فیلدهای `tags`/`images`/`videos` فقط خواندنی‌اند)؛ عملاً بیشتر `text` قابل تغییر است.

---

## ۳) نظرسنجی — `/api/surveys/`

JWT. فقط نظرسنجی‌های `is_active=True`. فقط خواندنی به‌جز اکشن `submit`.

| متد | مسیر | توضیح |
|-----|------|--------|
| `GET` | `/api/surveys/` | لیست: `id`, `title`, `description`, `created_at` |
| `GET` | `/api/surveys/{id}/` | جزئیات با سوالات، `has_submitted`, `previous_answers` |
| `POST` | `/api/surveys/{id}/submit/` | ثبت یا به‌روزرسانی پاسخ‌ها |

**جزئیات موفق**

```json
{
  "id": 1,
  "title": "...",
  "description": "...",
  "questions": [
    {
      "id": 10,
      "text": "...",
      "question_type": "text | single_choice | multiple_choice",
      "is_required": true,
      "order": 0,
      "options": [{ "id": 1, "text": "...", "order": 0 }]
    }
  ],
  "has_submitted": false,
  "previous_answers": []
}
```

**ثبت پاسخ `POST .../submit/`**

```json
{
  "answers": [
    {
      "question_id": 10,
      "text_answer": "پاسخ تشریحی",
      "selected_options": []
    },
    {
      "question_id": 11,
      "text_answer": "",
      "selected_options": [3]
    }
  ]
}
```

| نوع سوال | قانون |
|----------|--------|
| `text` | `text_answer`؛ نباید گزینه داشته باشد |
| `single_choice` | حداکثر یک `selected_options`؛ بدون متن |
| `multiple_choice` | یک یا چند گزینه؛ بدون متن |

سوالات اجباری باید در بدنه باشند. اگر قبلاً سابمیت شده باشد، پاسخ‌ها به‌روز می‌شوند (یک سابمیشن به‌ازای هر کاربر/نظرسنجی).

**موفق `201`:** `{ "detail": "پاسخ‌های شما با موفقیت ثبت شد." }`

---

## ۴) بلاگ — `/api/blogs/`

| متد | مسیر | دسترسی |
|-----|------|--------|
| `GET` | `/api/blogs/` | JWT |
| `GET` | `/api/blogs/{id}/` | JWT |
| `POST` | `/api/blogs/` | ادمین (`IsAdminUser`) |
| `PUT` / `PATCH` | `/api/blogs/{id}/` | ادمین |
| `DELETE` | `/api/blogs/{id}/` | ادمین |

**فیلدها:** `id`, `title`, `content`, `media`, `created_at`, `updated_at`

پسوند مجاز `media`: `.jpg` `.jpeg` `.png` `.gif` `.webp` `.mp4` `.webm` `.mov`

---

## ۵) تیکت معلم — `/api/tickets/`

JWT. فقط تیکت‌هایی که `phone_number` برابر شماره کاربر جاری است.

| متد | مسیر |
|-----|------|
| `GET` | `/api/tickets/` |
| `POST` | `/api/tickets/` |
| `GET` | `/api/tickets/{id}/` |
| `PUT` / `PATCH` | `/api/tickets/{id}/` |
| `DELETE` | `/api/tickets/{id}/` |

**ایجاد:** کلاینت `title` و `content` می‌فرستد. `first_name` / `last_name` / `phone_number` از کاربر ست می‌شود.

**خواندنی برای معلم:** `answer`, `is_answered`, `id`, `created_at`, `updated_at`

---

## ۶) API پنل ادمین — `/admin-panel/api/`

پیشوند: `/admin-panel/api/`  
تقریباً همه ViewSetها `IsAdminUser` هستند، **به‌جز تیکت ادمین** که `permission_classes = []` دارد (بدون کنترل دسترسی در سطح ویو).

پجینیشن استاندارد (جایی که فعال است): `page_size=5`، کوئری `?page=` و `?page_size=` (سقف ۱۰۰).

### CRUD استاندارد ViewSet

برای هر منبع زیر، مگر خلافش گفته شود:

`GET /` لیست · `POST /` ایجاد · `GET /{id}/` · `PUT /{id}/` · `PATCH /{id}/` · `DELETE /{id}/`

### معلمان — `/admin-panel/api/teachers/`

فیلتر: `province`, `city`, `position`  
جستجو (`?search=`): `first_name`, `last_name`, `phone_number`, `national_id`  
پجینیشن: بله

**خروجی:** `id`, `first_name`, `last_name`, `full_name`, `phone_number`, `national_id`, `province`, `city`, `village`, `school`, `grade` (لیست نام پایه‌ها), `position`, `gender`, `report_count`, `point_total`

---

### تگ‌ها — `/admin-panel/api/tags/`

جستجو روی `name`. پجینیشن پیش‌فرض DRF (کلاس اختصاصی روی این ویوست نیست).

فیلدها: `id`, `name`, `created_at`

---

### گزارش‌ها — `/admin-panel/api/reports/`

فیلتر: `teacher`, `teacher__province`, `teacher__city`  
جستجو: متن گزارش و نام/شماره معلم  
پجینیشن: بله

خروجی شامل اطلاعات معلم، تگ‌ها، URL مطلق تصاویر/ویدیوها، `images_count`, `videos_count`.

---

### تصاویر گزارش — `/admin-panel/api/report-images/`

فیلتر: `report`, `report__teacher`, `report__teacher__province`, `report__teacher__city`  
پجینیشن: بله  
`media_type` همیشه `"image"`.

---

### ویدیوهای گزارش — `/admin-panel/api/report-videos/`

مشابه تصاویر؛ `media_type` برابر `"video"`.

---

### رسانه تجمیعی — `GET /admin-panel/api/media-list/`

فقط `list` (ViewSet سفارشی). JWT ادمین.

**کوئری**

| پارامتر | معنی |
|---------|------|
| `media_type` | `image` یا `video` — فیلد مقابل از پاسخ حذف می‌شود |
| `province` / `city` / `teacher` | فیلتر روی معلم گزارش |
| `search` | نام معلم یا متن گزارش |
| `all` | اگر ست شود، بدون پجینیشن کل لیست برمی‌گردد |
| `page` / `page_size` | پجینیشن وقتی `all` نباشد |

پاسخ آیتم: `id`, `teacher`, `text`, `images`, `videos`, `created_at`

---

### امتیازها — `/admin-panel/api/points/`

فیلدها: `id`, `teacher`, `teacher_name`, `score`, `reason`, `created_at`  
`id` / `teacher_name` / `created_at` فقط خواندنی.

---

### نظرسنجی‌ها — `/admin-panel/api/surveys/`

`id`, `title`, `description`, `is_active`, `question_count`, `submission_count`, `created_at`

---

### سوال‌ها — `/admin-panel/api/questions/`

فیلتر: `?survey=`  
فیلدها: `id`, `survey`, `text`, `question_type`, `is_required`, `order`, `options` (تو در تو، فقط خواندنی)

---

### گزینه‌ها — `/admin-panel/api/options/`

`id`, `question`, `text`, `order`

---

### سابمیشن‌ها — `/admin-panel/api/submissions/`

فیلتر: `survey`, `user`  
`id`, `survey`, `survey_title`, `user`, `user_name`, `user_phone`, `created_at`

---

### پاسخ‌ها — `/admin-panel/api/answers/`

فیلتر: `submission`  
`id`, `submission`, `question`, `question_text`, `text_answer`, `selected_options`

---

### تیکت ادمین — `/admin-panel/api/tickets/`

**مجوز در ویو خالی است.** فقط فیلد `answer` قابل نوشتن است؛ بقیه فیلدها `read_only`. با PATCH روی `answer`، اگر متن غیرخالی باشد `is_answered=true` می‌شود.

---

## ۷) مستندات ماشین‌خوان

| متد | مسیر | دسترسی |
|-----|------|--------|
| `GET` | `/api/schema/` | طبق پیش‌فرض DRF معمولاً نیاز به JWT دارد مگر تنظیم جدا |
| `GET` | `/api/docs/` | Swagger UI |

---

## ۸) صفحات HTML (API نیستند)

این مسیرها تمپلیت برمی‌گردانند، نه JSON:

`/` · `/contact/` · `/login/` · `/login/verify/` · `/register/` · `/register/verify/` · `/main/` · `/dashboard/` · `/survey/` · `/admin/` (Django Admin) · `/admin-panel/` و زیرمسیرهای UI پنل (`reports`, `surveys`, `teachers`, `tickets`, `blogs/create`, …)

در حالت `DEBUG` فایل‌های `/media/` سرو می‌شوند.

---

## فهرست فشرده اندپوینت‌های JSON

| متد | مسیر | Auth |
|-----|------|------|
| POST | `/api/auth/login/send-otp/` | عمومی |
| POST | `/api/auth/login/verify-otp/` | عمومی |
| POST | `/api/auth/register/send-otp/` | عمومی |
| POST | `/api/auth/register/verify-otp/` | عمومی |
| GET | `/api/reports/tags/` | عمومی |
| GET | `/api/reports/points/` | JWT |
| GET POST | `/api/reports/` | JWT |
| GET PUT PATCH DELETE | `/api/reports/{id}/` | JWT |
| GET | `/api/surveys/` | JWT |
| GET | `/api/surveys/{id}/` | JWT |
| POST | `/api/surveys/{id}/submit/` | JWT |
| GET | `/api/blogs/` | JWT |
| GET | `/api/blogs/{id}/` | JWT |
| POST | `/api/blogs/` | ادمین |
| PUT PATCH DELETE | `/api/blogs/{id}/` | ادمین |
| GET POST | `/api/tickets/` | JWT |
| GET PUT PATCH DELETE | `/api/tickets/{id}/` | JWT |
| CRUD | `/admin-panel/api/teachers/` | ادمین |
| CRUD | `/admin-panel/api/tags/` | ادمین |
| CRUD | `/admin-panel/api/reports/` | ادمین |
| CRUD | `/admin-panel/api/report-images/` | ادمین |
| CRUD | `/admin-panel/api/report-videos/` | ادمین |
| GET | `/admin-panel/api/media-list/` | ادمین |
| CRUD | `/admin-panel/api/points/` | ادمین |
| CRUD | `/admin-panel/api/surveys/` | ادمین |
| CRUD | `/admin-panel/api/questions/` | ادمین |
| CRUD | `/admin-panel/api/options/` | ادمین |
| CRUD | `/admin-panel/api/submissions/` | ادمین |
| CRUD | `/admin-panel/api/answers/` | ادمین |
| CRUD | `/admin-panel/api/tickets/` | **بدون permission در ویو** |
| GET | `/api/schema/` | DRF default |
| GET | `/api/docs/` | DRF default |

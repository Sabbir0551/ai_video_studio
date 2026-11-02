# 🎬 AI Video Studio (ব্যক্তিগত এআই ভিডিও স্টুডিও)

> **সম্পূর্ণ স্বয়ংসম্পূর্ণ (Self-Hosted), উচ্চমানের ব্রডকাস্ট ভিডিও জেনারেশন ও মাল্টিমোডাল অটো-এডিটিং স্টুডিও**  
> স্থানীয় বাংলা (`bn-BD`) ও আন্তর্জাতিক ইংরেজি (`en-US`) ভাষার নির্ভুল টাইপোগ্রাফি ও ব্রডকাস্ট স্ট্যান্ডার্ড অডিও সহ।

---

## 🌟 প্রধান বৈশিষ্ঠ্যসমূহ (Core Features)

### 1. মডিউল ক: টেক্সট-টু-ভিডিও জেনারেটর (Module A)
- **স্ক্রিপ্ট ও স্টোরিবোর্ড**: হুক, বডি ও কল-টু-অ্যাকশন (CTA) স্ট্রাকচার অনুযায়ী সিন জেনারেশন।
- **প্রাকৃতিক ভয়েসওভার**: মাইক্রোসফটের উচ্চমানের নিউরাল ভয়েস (`bn-BD-PradeepNeural`, `bn-BD-NabanitaNeural`, `en-US-ChristopherNeural`) ইন্টিগ্রেশন (১০০% ফ্রি ও লাইসেন্সবান্ধব)।
- **কেন বার্নস মোশন ইঞ্জিন**: প্রতিটি ভিজ্যুয়াল ক্লিপে সূক্ষ্ম জুম-ইন ও স্মুথ প্যানিং অ্যানিমেশন।
- **১০০% নির্ভুল বাংলা সাবটাইটেল**: FFmpeg `libass` + `libharfbuzz` ইঞ্জিন দিয়ে যুক্তাক্ষর (`ক্ষ`, `জ্ঞ`, `ব্র`), হসন্ত (`্`), ও কার-চিহ্নের (`ি`, `ু`, `ো`) পারফেক্ট শেইপিং।
- **ব্রডকাস্ট অডিও মাস্টারিং**: EBU R128 (-14.0 LUFS) ইন্টিগ্রেটেড লাউডনেস এবং স্পিচের সাথে ব্যাকগ্রাউন্ড মিউজিকের সাইডচেইন ডাকিং (`sidechain ducking`)।
- **ব্র্যান্ড কিট ও ওয়াটারমার্ক**: ডায়নামিক সেমি-ট্রান্সপারেন্ট লোগো ও ব্র্যান্ড কালার প্যালেট।
- **থাম্বনেইল ও এসইও কিট**: স্বয়ংক্রিয় ইউটিউব/ফেসবুক থাম্বনেইল (`.jpg`), এসইও টাইটেল, ডেসক্রিপশন, ট্যাগস ও টাইমস্ট্যাম্প চ্যাপ্টার।

### 2. মডিউল খ: মাল্টিমোডাল ইনজেস্ট ও অটো-এডিটর (Module B)
- **মাল্টিমোডাল অ্যানালাইসিস**: 
  - স্পিচ ও ফিলার ডিটেকশন (বাংলা: `মানে`, `ইয়ে`, `আসলে`, `ধরেন`; ইংরেজি: `um`, `uh`, `like`)।
  - অডিও কোয়ালিটি অ্যানালাইসিস (FFmpeg `silencedetect` দিয়ে অপ্রয়োজনীয় পজ ডিটেকশন)।
  - ভিজ্যুয়াল সিন কাট ও কীফ্রেম এক্সট্র্যাকশন।
- **কাট ভ্যালিডেটর রুল ইঞ্জিন**: শব্দের মাঝে যেন কোনো কাট না পড়ে (`no mid-word cuts`), ন্যাচারাল ক্যাডেন্স বজায় রাখতে ১০% প্যাডিং এবং মিনিমাম ক্লিপ লেংথ গার্ডরেল।
- **EDL ও টাইমলাইন কম্পাইলার**: 
  - কাটের স্থানে জাম্প-কাট দূর করতে অল্টারনেটিং পাঞ্চ-ইন জুম (`112% punch-in`)।
  - স্বয়ংক্রিয় রি-টাইমিং সহ সাবটাইটেল সিঙ্ক।
  - ব্যাকগ্রাউন্ড মিউজিক লেয়ারিং ও অটো-রিফ্রেমিং (16:9 বা 9:16 Shorts/Reels)।

### 3. লাইভ ওয়েব ইন্টারফেস ও রেস্ট এপিআই (Module C)
- সিঙ্গেল পেজ ইন্টারেক্টিভ ড্যাশবোর্ড (Tailwind CSS, Dark Mode, Lucide Icons)।
- রিয়েল-টাইম রেন্ডার স্ট্যাটাস, প্রিভিউ প্লেয়ার ও হিস্ট্রি গ্যালারি।
- ফুল রেস্টফুল এপিআই (`/health`, `/api/v1/presets`, `/api/v1/renders`, `/api/v1/create-video`, `/api/v1/edit-video`)।

---

## 🚀 কুইক স্টার্ট গাইড (Quick Start)

### ১. পরিবেশ ও ডিপেনডেন্সি
- **Python**: 3.11+
- **FFmpeg**: 6.0+ (`libass` ও `libharfbuzz` সহ)
- **সিস্টেম ফন্ট**: Noto Sans Bengali (রেপোজিটরিতে `assets/fonts/` এ অন্তর্ভুক্ত)

### ২. ইন্সটলেশন
```bash
# প্রজেক্ট ডিরেক্টরিতে যান
cd "c:\All Projects\ai-video-studio"

# ভার্চুয়াল এনভায়রনমেন্ট তৈরি ও সক্রিয় করুন
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # Linux/macOS

# প্যাকেজ ইন্সটল করুন
pip install -r requirements.txt
```

### ৩. সিস্টেম ডায়াগনস্টিক চেক
```bash
# পরিবেশ ও FFmpeg যাচাই করতে রান করুন:
python -m backend.app.cli.main doctor

# বাংলা হরফ ও সাবটাইটেল টেস্ট:
python -m backend.app.cli.main test-bangla
```

### ৪. লাইভ সার্ভার চালু করুন (Web UI)
```bash
# FastAPI লাইভ সার্ভার রান করুন:
python -m uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000
```
ব্রাউজারে যান: 👉 **[http://localhost:8000](http://localhost:8000)**

---

## 💻 সিএলআই কমান্ডসমূহ (CLI Usage)

```bash
# হেল্প মেন্যু দেখুন
python -m backend.app.cli.main --help

# ১. টেক্সট থেকে বাংলা ভিডিও তৈরি করুন
python -m backend.app.cli.main create \
  --prompt "কৃত্রিম বুদ্ধিমত্তা এবং ভবিষ্যৎ প্রযুক্তির দিগন্ত" \
  --lang bn \
  --preset clean_corporate \
  --aspect 16:9 \
  --watermark \
  --out data/renders/my_bangla_video.mp4

# ২. ৯:১৬ শর্টস ভিডিও তৈরি করুন (দ্রুত প্রিভিউ মোডে)
python -m backend.app.cli.main create \
  --prompt "Quantum Computing in 60 Seconds" \
  --lang en \
  --preset short_hype \
  --aspect 9:16 \
  --preview \
  --out data/renders/quantum_preview.mp4

# ৩. ভিডিও ফাইল অ্যানালাইসিস করুন
python -m backend.app.cli.main analyze \
  --video data/renders/bangla_demo_mvp.mp4 \
  --lang bn

# ৪. অপ্রয়োজনীয় পজ ও ফিলার বাদ দিয়ে স্বয়ংক্রিয় এডিট করুন
python -m backend.app.cli.main edit \
  --video data/renders/bangla_demo_mvp.mp4 \
  --lang bn \
  --punch-zooms \
  --captions \
  --music \
  --out data/renders/my_edited_video.mp4
```

---

## 🧪 স্বয়ংক্রিয় টেস্ট স্যুট (Automated Tests)

সমস্ত ইউনিটি এবং ইন্টিগ্রেশন টেস্ট সম্পূর্ণ গ্রিন এবং ভেরিফাইড:

```bash
pytest backend/tests -v
```

| টেস্ট স্যুট | কভারেজ | স্ট্যাটাস |
|:---|:---|:---:|
| `test_bangla_rendering.py` | বাংলা সংখ্যা রূপান্তর, নর্মালাইজেশন, HarfBuzz রেন্ডারিং | ✅ PASSED |
| `test_config.py` | সেটিংস ও পাথ ইনিশিয়ালাইজেশন | ✅ PASSED |
| `test_create_video_pipeline.py` | টেক্সট-টু-ভিডিও এন্ড-টু-এন্ড পাইপলাইন (বাংলা ও ইংরেজি) | ✅ PASSED |
| `test_doctor.py` | সিস্টেম হেলথ ডায়াগনস্টিক সিএলআই | ✅ PASSED |
| `test_phase3_features.py` | প্রিসেট, থাম্বনেইল, ওয়াটারমার্ক, এসইও মেটাডাটা, কস্ট ট্র্যাকার | ✅ PASSED |
| `test_phase4_analysis.py` | মাল্টিমোডাল স্পিচ, সাইলেন্স ডিটেকশন, ভিজ্যুয়াল সিন কাট | ✅ PASSED |
| `test_phase5_auto_edit.py` | কাট ভ্যালিডেটর, EDL টাইমলাইন কম্পাইলার, পাঞ্চ-ইন জুম | ✅ PASSED |
| `test_phase6_web_api.py` | রেস্ট এপিআই ও ওয়েব ইউআই ইন্টিগ্রেশন | ✅ PASSED |
| `test_timeline_schema.py` | ক্যানোনিকাল টাইমলাইন স্কিমা ও ইনভ্যালিড ক্লিপ ভ্যালিডেশন | ✅ PASSED |
| `test_queue.py` | ব্যাকগ্রাউন্ড ইন-মেমোরি জব কিউ ও রিট্রাই মেকানিজম | ✅ PASSED |

---

## 🐳 ডকার ডিপ্লয়মেন্ট (Docker Deployment)

```bash
# ডকার কম্পোজ দিয়ে কন্টেইনার বিল্ড ও রান করুন:
docker-compose up --build -d

# কন্টেইনারের লগ দেখুন:
docker-compose logs -f
```

---

## 📁 প্রজেক্ট আর্কিটেকচার

```
ai-video-studio/
├── assets/
│   ├── audio/              # ব্যাকগ্রাউন্ড মিউজিক ও SFX
│   └── fonts/              # Noto Sans Bengali & Roboto ভেরিয়েবল ফন্ট
├── backend/
│   ├── app/
│   │   ├── analysis/       # ভিডিও ইনজেস্ট, স্পিচ ও সাইলেন্স অ্যানালাইজার
│   │   ├── api/            # FastAPI রেস্ট রাউটস ও লাইফস্প্যান
│   │   ├── cli/            # Typer রিচ সিএলআই
│   │   ├── core/           # কনফিগ, ডাটাবেজ, কিউ, লগার, কস্ট ট্র্যাকার
│   │   ├── media/          # FFmpeg র‍্যাপার, বাংলা হার্ফবাজ শেইপার, থাম্বনেইল
│   │   ├── models/         # Pydantic ক্যানোনিকাল টাইমলাইন, প্রজেক্ট, জব
│   │   ├── pipelines/      # CreateVideo & AutoEdit সমন্বিত পাইপলাইন
│   │   ├── presets/        # ৪টি প্রফেশনাল স্টাইল প্রিসেট
│   │   └── static/         # ওয়েব অ্যাপ সিঙ্গেল-পেজ ইউআই (HTML/JS)
│   └── tests/              # ৩০টি কমপ্রিহেনসিভ পাইটেস্ট টেস্ট
├── data/
│   ├── projects/           # প্রজেক্ট ওয়ার্কস্পেস ও স্টোরিবোর্ড
│   └── renders/            # জেনারেটেড এমপিফোর ভিডিও ও থাম্বনেইল
├── docs/                   # আর্কিটেকচার ও ADR ডকুমেন্টস
├── Dockerfile              # প্রোডাকশন ডকার বিল্ড
├── docker-compose.yml      # ওয়ান-ক্লিক ডিপ্লয়মেন্ট
└── README.md
```

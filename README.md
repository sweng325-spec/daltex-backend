# Daltex Asset & Organization Management API

مشرع إدارة الأصول والمخزن المركزي لشركة دالتكس (**Daltex Group**)، وهو عبارة عن خلفية برمجية (Backend API) قوية مبنية باستخدام **Django 6** و **Django Rest Framework (DRF)**. يوفر النظام إدارة متكاملة لجرد الإكسسوارات، تتبع الأصول الصلبة (Hardware Assets)، وإدارة الهيكل الإداري والتنظيمي للشركة بشكل مركزي ومؤمن بالكامل بالصلاحيات.

---

## 🚀 الميزات الرئيسية (Key Features)

* **إدارة أصول المخزن (`inventory`):** تتبع كميات قطع الغيار والإكسسوارات مع نظام لوج (Audit Log) آلي لتسجيل كل حركات الإضافة والعجز والتعديل مع فحص صلاحيات صارم (`view_inventoryitem`, `add_inventoryitem`, `change_inventoryitem`, `delete_inventoryitem`).
* **إدارة الهيكل التنظيمي (`organization`):** نظام مرن لإدارة الفروع (Branches)، القطاعات (Sectors)، والإدارات (Departments) وربطهم ديناميكيًا عبر جدول هيكلي موحد (`BranchStructure`) ومؤمن بالكامل بصلاحيات القراءة، الإضافة، التعديل، والحذف لكل موديل.
* **تأمين صارم للبيانات (Granular Security):** حماية كاملة لكافة المسارات (Endpoints) باستخدام فحص الصلاحيات الافتراضي من Django ومصادقة **JWT Tokens**.
* **قاعدة بيانات مهيأة للإنتاج:** متوافق بالكامل مع قواعد بيانات **PostgreSQL** عبر محرك `psycopg3`.

---

## 🛠️ تقنيات المشروع (Tech Stack)

* **Framework:** Django 6.0.6 & Django REST Framework 3.17.1
* **Database Driver:** Psycopg 3.3.4 (PostgreSQL)
* **Authentication:** SimpleJWT (JSON Web Tokens)
* **CORS Handling:** django-cors-headers

---

## 📋 متطلبات التشغيل (Prerequisites)

تأكد من تثبيت الأدوات التالية على نظامك قبل البدء:
* **Python 3.10+**
* **PostgreSQL Database Server**

---

## 🔧 خطوات إعداد وتشغيل المشروع (Setup & Installation)

تابع الخطوات التالية بدقة لإعداد بيئة العمل المحلية:

### 1. استنساخ المستودع والدخول للمجلد
```bash
git clone <repository_url>
cd DALTEX_ASSET_APP

### 2.
python -m venv venv
.\venv\Scripts\activate

### 3.
python3 -m venv venv
source venv/bin/activate

### 4.
pip install --upgrade pip
pip install -r req.txt

### 5.
python manage.py makemigrations
python manage.py migrate

### 6.
python manage.py createsuperuser

### 7.
python manage.py runserver
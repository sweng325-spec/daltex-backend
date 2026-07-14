# Daltex Asset & Organization Management API

The central Asset and Inventory Management system for **Daltex Group**, built as a robust Backend API using **Django 6** and **Django REST Framework (DRF)**. This system provides integrated management for accessory stock tracking, hardware asset tracking, and centralized organization structure management (Branches, Sectors, Departments), all fully secured with granular permission controls.

---

## 🚀 Key Features

* **Inventory Asset Management (`inventory`):** Track spare parts and accessory quantities with an automated transaction audit log to record additions, adjustments, and deductions, secured by strict Django permission checks (`view_inventoryitem`, `add_inventoryitem`, `change_inventoryitem`, `delete_inventoryitem`).
* **Organization Structure Management (`organization`):** A flexible system to manage Branches, Sectors, and Departments, linking them dynamically via a unified mapping table (`BranchStructure`). Fully secured with View, Add, Change, and Delete permissions for each individual model.
* **Granular Security:** Comprehensive protection for all endpoints utilizing Django's built-in model permissions combined with **JWT Token** authentication.
* **Production-Ready Database:** Fully compatible with **PostgreSQL** databases using the modern `psycopg3` database adapter.

---

## 🛠️ Tech Stack

* **Framework:** Django 6.0.6 & Django REST Framework 3.17.1
* **Database Driver:** Psycopg 3.3.4 (PostgreSQL)
* **Authentication:** djangorestframework-simplejwt 5.5.1 (JSON Web Tokens)
* **CORS Handling:** django-cors-headers 4.9.0

---

## 📋 Prerequisites

Ensure you have the following installed on your system before proceeding:
* **Python 3.10+**
* **PostgreSQL Database Server**

---

## 🔧 Setup & Installation

Follow these steps carefully to configure and run your local development environment:

### 1. Clone the Repository and Navigate to the Project Folder
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
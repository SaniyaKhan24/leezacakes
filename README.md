# Leeza Cakes

E-commerce platform for Leeza Cakes, a made-to-order cake studio: browse, customise in 3D, pick a pickup slot, pay by UPI, and track the order while staff verify payment and move it through the kitchen.

## Project structure

- `backend/` — Django 5.2 + Django REST Framework API (accounts, catalogue, customisation, cart, orders, payments, notifications, search, enquiries). See [backend/README.md](backend/README.md).
- `frontend/` — Next.js 16 + TypeScript storefront with procedural 3D cakes and motion design. See [frontend/README.md](frontend/README.md).

## Quick start (sample shop)

```bash
# Backend (Python 3.12)
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirement/development.txt
export DEV_USE_SQLITE=True DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py migrate
python manage.py seed_demo          # 14 cakes, options, demo accounts, sample orders
python manage.py runserver 127.0.0.1:8000

# Frontend
cd ../frontend
npm install
npm run dev                          # http://localhost:3000
```

Sign in as `demo@leezacakes.test` / `LeezaDemo!2026`, or staff `studio@leezacakes.test` / `LeezaStudio!2026` at http://127.0.0.1:8000/admin/.

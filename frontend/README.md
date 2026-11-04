# Leeza Cakes — storefront

Next.js 16 (App Router, React 19, TypeScript) storefront for the Leeza Cakes Django API.

- **Motion:** `motion` for page, text and layout animation, `lenis` for inertial scrolling, and a custom cursor that labels interactive surfaces.
- **3D:** every cake on the menu is a procedural model (`three`, `@react-three/fiber`, `@react-three/drei`). The same models drive the hero, the product turntable, the "inside" slice view, the cake designer and the catalogue photographs.

## Run it locally

You need the backend running first (see `../backend/README.md`; `DEV_USE_SQLITE=True` + `python manage.py seed_demo` gives you a full sample shop).

```bash
npm install
npm run dev            # http://localhost:3000
```

The browser only talks to this origin. `next.config.ts` rewrites `/api/*`, `/media/*` and `/health/*` to Django at `BACKEND_ORIGIN` (default `http://127.0.0.1:8000`), so the guest-cart session cookie is first-party and no CORS setup is needed.

Demo accounts created by `seed_demo`:

| Who | Email | Password |
| --- | --- | --- |
| Customer | `demo@leezacakes.test` | `LeezaDemo!2026` |
| Staff (Django admin at `http://127.0.0.1:8000/admin/`) | `studio@leezacakes.test` | `LeezaStudio!2026` |

## The customer journey

1. **Browse** `/shop` (filter, search, sort) → **customise** on `/shop/[slug]` or in the designer at `/custom`. Size, eggless, message, finishing touches and candles all update the 3D cake and the price live.
2. **Bag** — a guest cart held in Django's session; it merges into the account on sign-in.
3. **Account** — register → confirm the email link (in development the link is printed in the `runserver` console) → sign in.
4. **Checkout** `/checkout` — pickup slots come from `/api/v1/orders/pickup-slots/` and respect each cake's notice period. Orders are placed with an `Idempotency-Key`.
5. **Pay** on `/orders/[id]` — UPI QR + ID, then upload a screenshot. The page polls for updates.
6. **Staff** verify the proof in Django admin (Payments → "Accept latest proof and verify payment"), then move the order through Start preparing → Mark ready → Mark completed. The customer's timeline follows.

Bespoke cakes and questions go through `/custom` and `/contact` to `/api/v1/enquiries/`.

## Code map

```
src/app/(site)/          pages with the shared header, footer, cart drawer and page transition
src/app/studio/render/   dev-only photo studio used to render catalogue images
src/components/cake/     procedural cake engine: designs.ts (art direction per cake),
                         geometry.ts, textures.ts, cake-model.tsx, cake-stage.tsx, lazy-cake.tsx
src/components/motion.tsx  SplitText, FadeIn, ImageReveal, Magnetic, Marquee, RollingNumber, Cursor
src/components/cake-builder.tsx  size/options state → API selections, price and 3D extras
src/lib/api.ts           typed API client (JWT + transparent refresh)
```

## Regenerating the catalogue photographs

Product photos are rendered from the 3D models, so a new cake design only needs an entry in `src/components/cake/designs.ts`:

```bash
npm run dev
node scripts/render-cakes.mjs --out /tmp/renders           # transparent PNGs (headless Chromium)
python ../backend/scripts/compose_product_photos.py /tmp/renders   # studio backdrops → seed assets + posters
python ../backend/manage.py seed_demo_catalog                # re-attach changed images
```

## Checks

```bash
npm run lint
npx tsc --noEmit
npx prettier --check "src/**/*.{ts,tsx,css}"
npm run build
```

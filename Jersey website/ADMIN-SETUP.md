# Store Admin Setup

The admin page requires the Flask backend; do not publish this as a static-only site if you need inventory or order records.

## Netlify deployment

Netlify hosts the static website, not this Flask API. Deploy the API separately before expecting sign-in, products, or orders to work:

1. Create a Render web service from this repository using the included `render.yaml`. The persistent disk keeps the SQLite database and uploaded product images across restarts. This service uses Render's paid Starter plan because its persistent disk is required for store data.
2. After the service is created, copy its exact public `onrender.com` URL. In `netlify.toml`, replace `https://dej-jersey-store-api.onrender.com` in both redirects with that URL.
3. Deploy the repository to Netlify, with the site publish directory set to the repository root. Redeploy Netlify whenever the API URL changes.
4. Check `https://YOUR-RENDER-SERVICE.onrender.com/api/health`; it should return `{"status":"ok",...}`. Then open the Netlify site's `/admin.html` directly and sign in with `OSE`.

The `/api/*` redirect sends sign-in and store API requests to Flask. The `/images/products/*` redirect serves photos uploaded in the admin page from the same persistent disk. Deploying only to Netlify will not run the backend and cannot provide admin sign-in or order management.

## Local setup

In PowerShell, from the Jersey website folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python backend.py
```

Sign in with the username `OSE`. No password is required.

Open `http://127.0.0.1:8000/` for the shop and `http://127.0.0.1:8000/admin.html` for inventory and orders. The first run creates `instance/store.sqlite3`; it is intentionally excluded from source control.

## Using the admin page

1. Keep the PowerShell window running; it is running the shop server.
2. Open the Admin link on the Help page or go to `/admin.html` directly, enter `OSE`, and sign in. A successful login remains active in that browser tab for up to eight hours.
3. Use **Add a jersey** to upload a JPEG, PNG, or WebP product photo up to 5 MB, enter jersey details, price, and stock by size, then publish it. At least one size must have stock above zero.
4. Open a jersey row, enter the quantity you actually have for each size, and choose **Save stock**. Leave a size blank if you have not started tracking it; enter `0` if it is sold out.
5. Use **Archive jersey** to remove a sold-out listing from the public shop while retaining its order history. Restore it when it is available again.
6. Open an order to see the jersey, size, badge, customer contact, and delivery address. Confirming an order deducts the tracked size quantity.

The admin page is separate from the customer shop and should only be shared with the shop owner. Generate a new code for production hosting.

## Admin and stock notes

- Admin access uses the username `OSE` without a password. Anyone who knows this username can sign in, so do not expose the admin page publicly.
- Admin credentials are checked server-side. The Admin link is a convenience, not an access control mechanism.
- Uploaded jersey images are limited to JPEG, PNG, or WebP and 5 MB. New products are added to the live catalog immediately.
- Enter actual stock counts by size in the admin page. A blank size means inventory is untracked; `0` means sold out.
- Orders begin as pending confirmation. Confirming an order requires tracked stock and deducts the quantities. Cancelling a confirmed order restores its stock.
- Customer orders and contact details are stored in the SQLite database. Restrict server and database access, back up the database securely, and set a retention policy before handling real customer data.
- Payments are not processed online. Orders continue to WhatsApp after the server saves the request.

This local SQLite setup is a starter for one small shop instance. For a multi-instance production deployment, use a managed database and a production WSGI server.
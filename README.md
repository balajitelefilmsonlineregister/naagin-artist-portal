# Naagin Season 8 Artist Registration Portal

A deployable Flask application with public artist registration, private application tracking, photo upload, admin authentication, application search, and status management.

## Important deployment gate
This code is a technical portal starter, not proof of affiliation with Balaji Telefilms or authorization to conduct casting. Before public launch, confirm written authorization to use the name/marks and to collect artist data. Add the legally approved privacy notice, retention policy, contact details, and any required consent language. Do not collect fees or publish payment QR/UPI details until the authorized merchant account and payment provider integration are verified.

## Run locally
1. Install Python 3.10+.
2. Create a virtual environment and activate it.
3. Run `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env`; set a long random `SECRET_KEY`, `ADMIN_USERNAME`, and a strong `ADMIN_PASSWORD`.
5. Run `python app.py`.
6. Open `http://127.0.0.1:5000`.

The first run creates `portal.db` and the admin account from the environment variables.

## Production deployment
Deploy on a reputable HTTPS-enabled Python host. Configure environment variables in the host dashboard; do not upload `.env` or `portal.db` to public source control. Use a managed PostgreSQL database by setting `DATABASE_URL`. Set `COOKIE_SECURE=1`. Configure backups, access logging, rate limiting/WAF, monitoring, and a documented data deletion process. Use a private object-storage bucket for applicant photos in production; the local `uploads/` folder is suitable only for a single-server deployment.

## Included
- Artist form: name, DOB, gender, phone, email, city, experience, optional profile photo.
- Submission confirmation with unique application ID and private tracking code.
- Applicant status lookup requiring both ID and private tracking code.
- Admin login, searchable dashboard, status counts, applicant detail and status updates.
- CSRF protection, password hashing, upload extension checks, upload size limit, and secure session cookie options.

## Not yet connected
- Email/SMS/WhatsApp notifications: requires verified sender/provider credentials and consent-compliant messaging setup.
- Online payments: intentionally not enabled. Requires verified merchant ownership, gateway credentials, webhook signature validation, refunds/reconciliation, and approved fee policy.
- Multi-user staff roles and audit logs: should be added before multiple staff members use the dashboard.
- Export/reporting: can be added after defining who may access applicant data.

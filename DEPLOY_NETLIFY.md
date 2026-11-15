# MitraCare deployment: Netlify frontend + Render API

MitraCare is a full-stack FastAPI application. Netlify hosts the static browser UI; the Python API and PostgreSQL database run as a separate Render Blueprint. `netlify.toml` proxies `/api/*` through the Netlify origin so the browser continues to use same-origin requests and HTTP-only session cookies.

## Deploy the API first

1. In Render, choose **New → Blueprint** and connect `https://github.com/shashankkumar8/MitraCare`.
2. Render detects the root `render.yaml`. Review the resources before applying: one Free Python web service and one Free Postgres database in Singapore.
3. Apply the Blueprint and wait until the service is live. Its expected origin is `https://mitracare-api-shashank-k8r3.onrender.com`, as configured in `netlify.toml`.
4. Verify `https://mitracare-api-shashank-k8r3.onrender.com/api/health` returns JSON with `status: ok`.
5. The service start command runs the idempotent synthetic demo seeder before Uvicorn. Demo login: profile code `MTDEMO26`, patient PIN `246810`, caregiver PIN `135790`. This is public synthetic data only; never enter real health information into the demo account.

## Deploy the frontend to Netlify

1. In Netlify, choose **Add new project → Import an existing project → GitHub** and select `shashankkumar8/MitraCare`.
2. Keep the repository root as the base directory. Netlify reads the root `netlify.toml`; it runs the static copy command and publishes `dist`.
3. Deploy. No build environment variables are required for the static frontend.
4. After deployment, test `https://YOUR-SITE.netlify.app/api/health`. It must return the Render API health JSON through the Netlify proxy.
5. Open the root site, sign in with the synthetic demo patient or caregiver account, create a separate test profile, add a medication and appointment, and verify logout/login.

## Important free-plan limitations

- Render Free web services spin down when idle, so the first request after inactivity can be slow. Background reminder processing is not dependable while the instance is asleep.
- Render Free Postgres expires 30 days after creation and does not include backups. Upgrade the database to a paid plan before relying on long-lived records.
- SMTP is not configured by this Blueprint. Reminder records work in-app; email delivery requires SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD and SMTP_FROM configured as protected service environment variables, followed by a redeploy.
- This is a hackathon prototype with synthetic data. It is not clinically validated or approved for real patient records.

## Build output

The build creates:

```text
dist/
├── index.html
├── _headers
└── static/
    ├── app.js
    └── styles.css
```

The API proxy is a Netlify rewrite with status `200`, keeping `/api` same-origin in the browser.

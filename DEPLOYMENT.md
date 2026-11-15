# Running a shared AlertMe installation

The API hosts the website and serves native clients. Deployment is manual; CI
checks the code and does not publish a website or provision a database.

## API and website

Use Python 3.12+ and a separately managed MongoDB 8 instance. Install
`Alertme/requirements-api.txt`, configure `Alertme/.env` or host-managed variables,
and serve the factory with Waitress from the repository root:

```bash
waitress-serve --call --host=127.0.0.1 --port=5000 Alertme.src.backend.app:create_app
```

Put the service behind an HTTPS endpoint for remote users and set
`ALERTME_ENV=production`. Serve the website and API under the same origin at the
host root. Configure CORS only if a separately hosted browser origin is actually
needed. Limit database access to the application environment and use the host's
verified TLS connection settings.

`/health` reports process liveness; `/ready` checks MongoDB connectivity. Verify
signup, sign-in, deadline updates, publishing, subscriptions, contact verification
and exports using the actual origin and native client before inviting users.

## Native clients

Install the full `Alertme/requirements.txt` on a supported desktop environment.
Set `ALERTME_API_URL` to the shared HTTPS API root. Run `python Alertme/main.py`.
The application is a native Qt client, not an embedded browser. Tested desktop
sizes are 1440×960 and 1024×768; the browser interface provides the mobile layout.
Prebuilt Windows/macOS installers are not included.

On minimal Linux hosts, install the Qt runtime libraries required by the host
platform. The offscreen CI job explicitly installs `libegl1`, `libopengl0`,
`libgl1`, `libxkbcommon0` and `libfontconfig1`; a graphical X11/Wayland session may
need additional platform packages supplied by the desktop distribution.

## Reminder process

Run `python -m Alertme.src.backend.services.deadline_scanner` under a process
supervisor, separately from the API. Configure a valid `APP_TIMEZONE` and the
provider settings from `.env.example`. Verify actual delivery in accounts you
control. Local and CI tests substitute provider adapters; they do not establish
real SMTP/Twilio setup or provider availability.

The worker records one attempt for each occurrence/channel. Review failed or
interrupted attempts operationally; do not assume a successful delivery from an
unverified provider response. Keep backups and monitor service health.

## Existing installations

Back up both configured databases before rollout. The application reads personal
deadlines from both retained stores and preserves their record IDs. It introduces
partial account indexes and subscription/delivery metadata, without intentionally
deleting existing account or deadline rows. Review duplicate email/phone values
before startup if an existing installation cannot satisfy the indexes.

Legacy mirror records without contact fields are retained. New accounts also
retain an `original_id` value for compatibility with older identifier indexes.
There is no automatic account reassignment based on subscriber email lists.
Users should follow their published deadlines again in the new workspace to
create the current subscription records; existing legacy lists remain untouched.

Production data migration, cloud hosting, real-provider delivery and packaged
installers were not performed as part of the repository changes.

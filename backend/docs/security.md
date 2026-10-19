# Security

Keep .env, backups, private keys and .venv untracked. Existing local source was
backed up in ignored .local-backups before rewrites; no .env copy was made.
Filename/history inspection found no tracked .env; this is not a full history
secret scan. If any credential was committed, rotate it first, remove it from
history with coordinated remediation, and invalidate affected sessions/tokens.

Production enforces HTTPS, secure cookies, nosniff, frame denial, strong secrets
and explicit host/origin lists. HSTS is one year for the configured host only;
preload and includeSubDomains are disabled pending domain ownership review.
CORS controls browser reading, not authorization. CSRF remains enabled for
cookie authentication. Cross-origin credentialed authentication is intentionally
not configured; define its requirements before changing cookies or CORS.

DRF throttles use local memory and are not an abuse/security boundary. Before
scaling, choose a shared cache and edge rate limits, and set proxy client-IP trust
deliberately. Logs allow time, severity, logger, HTTP status and exception type;
raw messages, request bodies, query strings and tracebacks are discarded. Add
reviewed event IDs/correlation and redacted monitoring before production operations.

Uploads remain unimplemented. Require size limits, image decode/re-encode, pixel
limits, MIME/content validation, randomized names and non-executable isolated
storage before exposing upload endpoints. Serve media from a separate origin.
Payments must verify provider signatures and reconcile status server-side.

Bandit checks executable backend infrastructure. pip-audit --strict fails for both
known vulnerabilities and tool/network errors: read its output to distinguish CVE
findings from resolution/connectivity failures. Fix/upgrade affected dependencies,
regenerate all locks and re-run checks. Do not suppress advisories to get green CI.

GitHub manual settings:
- Enable dependency graph, Dependabot alerts/security updates.
- Enable secret scanning and push protection where the repository plan supports it.
- Require Backend CI (both OS jobs) and Backend security via branch rulesets.
- Require reviewed PRs, prevent force-push, and restrict Actions permissions.
- Dependency review runs for public repositories; for eligible private repos enable
  the feature and set DEPENDENCY_REVIEW_ENABLED=true. pip-audit always runs.
- Configure a protected production environment with reviewers if deployment is
  later automated; no deployment workflow is included.

Admin remains /admin/: restrict ingress to trusted networks/SSO, require strong
credentials and a reviewed MFA solution before production. Do not rely on obscurity.

Audits use --require-hashes --disable-pip on complete transitive pip-tools locks.
This audits every locked package without repeating pip resolution/downloads;
installation still verifies hashes and pip check validates compatibility.

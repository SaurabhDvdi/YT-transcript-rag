# Security Policy

## Supported Versions

Only the latest release branch receives security patches and updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

---

## Reporting a Vulnerability

The YouTube AI Assistant team takes security and user privacy seriously. If you believe you have found a security vulnerability in this project, please follow these responsible disclosure steps:

1. **Do NOT open a public issue.** Public disclosure puts users and deployments at risk before a fix is available.
2. **Report Privately**: Please use GitHub Private Vulnerability Reporting via the **Security** tab of the repository (`Security > Advisory > Report a vulnerability`).
3. If GitHub Private Vulnerability Reporting is unavailable, contact the repository maintainers directly via repository mechanisms.

Please include the following details in your report:

- Type of vulnerability (e.g., prompt injection escape, cross-user authorization bypass, SSRF, XSS).
- Exact steps or proof-of-concept (PoC) payload to reproduce the behavior.
- Affected component(s) (`apps/backend` or `apps/extension`).
- Potential impact of the issue.

---

## Security Practices in this Repository

- **Zero Client-Side Secrets**: The browser extension contains zero API keys or backend admin secrets.
- **Untrusted Transcript Framing**: Video transcripts are treated as untrusted user data and enclosed in isolated prompt boundaries (`<transcript_context>`) to prevent injection escapes.
- **Strict Tenant & User Scoping**: All database operations scope records by authenticated `user_id` or cryptographic `session_id`.
- **Constant-Time Verification**: Password hashes and administrative signatures are verified using constant-time comparisons (`hmac.compare_digest`).
- **No Remote JavaScript**: The browser extension uses strict Content Security Policy (CSP) with zero dynamic script evaluation (`eval`, `new Function`).

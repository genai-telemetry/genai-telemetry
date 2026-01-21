# Security Policy

GenAI Telemetry takes security seriously. We appreciate your efforts to responsibly disclose your findings.

## Supported Versions

The following versions of GenAI Telemetry are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:

**security@genai-telemetry.io**

Please include the following information in your report:

1. **Type of issue** (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
2. **Full paths of source file(s)** related to the manifestation of the issue
3. **Location of the affected source code** (tag/branch/commit or direct URL)
4. **Step-by-step instructions** to reproduce the issue
5. **Proof-of-concept or exploit code** (if possible)
6. **Impact of the issue**, including how an attacker might exploit it

## Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution Target**: Within 90 days (depending on severity)

## Disclosure Policy

We follow coordinated disclosure:

1. Reporter submits vulnerability to security@genai-telemetry.io
2. We confirm receipt within 48 hours
3. We investigate and determine severity
4. We develop and test a fix
5. We coordinate disclosure date with reporter
6. We release the fix and publish security advisory
7. We credit the reporter (unless they prefer anonymity)

## Security Advisories

Security advisories are published via:

- [GitHub Security Advisories](https://github.com/genai-telemetry/genai-telemetry/security/advisories)
- Project mailing list announcements
- CHANGELOG.md entries

## CVE Assignment

For qualifying vulnerabilities, we will request CVE assignment through appropriate channels.

## Security Best Practices for Users

When using GenAI Telemetry:

1. **Keep Updated**: Always use the latest stable version
2. **Secure Credentials**: Never commit API keys or tokens to source control
3. **Environment Variables**: Use environment variables for sensitive configuration
4. **Network Security**: Use TLS/SSL when exporting telemetry data
5. **Access Control**: Restrict access to telemetry endpoints
6. **Data Sanitization**: Be aware of sensitive data in prompts/responses

## Security Features

GenAI Telemetry includes these security features:

- No storage of API keys in telemetry data
- Configurable PII redaction
- Support for encrypted transport (TLS)
- No phone-home or telemetry collection by the SDK itself

## Acknowledgments

We would like to thank the following individuals for responsibly disclosing security issues:

*No acknowledgments yet.*

---

Thank you for helping keep GenAI Telemetry and its users safe!

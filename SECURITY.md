# Security Policy

## Supported Versions

We support **only the latest stable release** of the TestRail CLI. Older versions do not receive security updates and may contain unpatched vulnerabilities.

> **Note:** As of **version 1.9.0**, the TestRail CLI requires **Python 3.10 or newer**. Please ensure your environment meets this requirement before reporting any issues.

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it **privately** by emailing **compliance@gurock.io**.  
Please **do not** file a public GitHub issue, as that could expose the vulnerability before a fix is available. For more details, see our [official security disclosure guidelines](https://www.ideracorp.com/Legal/Gurock/SecurityStatement#:~:text=IV%20%2D%20Reporting%20Security%20Issues).

We aim to acknowledge reports within **2 business days** and will work to assess and address the issue as promptly as possible.

## Disclosure Policy

- All reports are reviewed thoroughly and prioritized based on severity and impact.
- Confirmed vulnerabilities will be addressed as quickly as possible.
- We may coordinate public disclosure with the reporter, and will credit them in the release notes unless anonymity is requested.

## Security Best Practices

To help keep your systems secure while using the TestRail CLI:

- Always use the latest version of the CLI.
- Always install the CLI from trusted sources and verify before installation.
- Ensure your environment uses a supported version of Python (currently 3.10 or newer).
- Avoid storing or sharing sensitive credentials in plain text (e.g., config files).
- Run the CLI inside a virtual environment, Docker container, or dedicated environment, especially on shared systems. If using on CI/CD, restrict access to that environment and monitor usage.
- Limit permissions when accessing TestRail using a service account, Use a least privilege API token — one that only has access to what the CLI needs.
- Follow your organization's secure development and software usage policies.
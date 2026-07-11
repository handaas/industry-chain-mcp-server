# Security Policy

## Credentials

Never commit `.env`, platform tokens, `secret_id`, `secret_key`, signatures, or
raw signed requests. Use `.env.example` for placeholders only.

## Reporting

Report suspected vulnerabilities privately to the repository maintainers.
Do not open a public issue containing credentials, tokens, customer data, or
reproduction output with sensitive fields.

## Supported versions

Security fixes are applied to the latest `main` branch. Remote deployments
should be updated and restarted after a security fix.

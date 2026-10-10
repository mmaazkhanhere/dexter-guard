# Spec 003 quality gates

The following checks are part of the release review for this feature:

- Candidate note bodies over 50,000 Unicode code points must fail before a
  provider call with `REQUEST_TOO_LARGE`.
- Secret scanning must run with `gitleaks detect --redact --no-banner` (or an
  equivalent approved scanner) and must report no findings.
- Dependency vulnerability scanning must run with `pip-audit` against the
  resolved environment and must report no unaccepted vulnerabilities.
- Python security linting must run with `bandit -r src` and all findings must
  be reviewed or fixed before release.

These commands are release gates; this repository does not claim a successful
security scan unless the command has actually been executed in the target CI
environment.


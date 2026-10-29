# Quality tooling setup

RepoPilot's GitHub Actions workflow already produces `coverage.xml` and conditionally uploads it to Codecov. Upload is skipped until the repository secret `CODECOV_TOKEN` is configured.

## Codecov

1. Sign in to Codecov using the GitHub account that has access to this repository.
2. Add/import `vankudothuadhinaik/RepoPilot` in Codecov.
3. Copy the repository upload token from Codecov.
4. In GitHub, open **Settings → Secrets and variables → Actions → New repository secret**.
5. Name it `CODECOV_TOKEN` and paste the token value. Never commit the token into this repository.
6. Re-run the CI workflow. The Codecov upload step should run instead of being skipped.

The `codecov.yml` thresholds start at 65% project coverage and 60% patch coverage. Adjust them only when the team deliberately changes its quality policy; do not weaken them just to make a failing build green.

## CodeScene

CodeScene is an optional external GitHub integration, not a package dependency in this repository. To connect it:

1. Open CodeScene and choose its GitHub integration / repository onboarding flow.
2. Authorize only the GitHub repository access required for analysis.
3. Select `vankudothuadhinaik/RepoPilot` and enable the desired code-health, hotspot, and pull-request analysis.
4. Review its first baseline report before setting quality gates.
5. If CodeScene provides a GitHub status/check, verify it appears on a test pull request and document the expected gate here.

This repository's connected GitHub API does not expose secrets or third-party account administration, so I have not claimed to install Codecov or CodeScene on your behalf. Codecov upload remains conditional until you add its token; CodeScene must be authorized in its own UI.

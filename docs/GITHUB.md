# Publish

Unzip the project and open a terminal inside fairfreeze:

```bash
git init -b main
git add .
git commit -m "Build FairFreeze synthetic fraud-chain review prototype"
gh auth login
gh repo create FairFreeze --public --source=. --remote=origin --push
```

Use --private for a private repository. Only supplied synthetic snapshots and derived reports are included. Do not add credentials or customer records. No license is assigned automatically; choose one if granting reuse rights. GitHub Actions runs unit tests and compilation. Open reports/dashboard.html locally; repository viewers do not execute it.

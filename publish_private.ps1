$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$repoName = 'charleszon/supply-chain-analytics-demo'

gh auth switch --hostname github.com --user charleszon
if ($LASTEXITCODE -ne 0) { throw 'Could not select the personal GitHub account.' }
$login = gh api user --jq '.login'
if ($LASTEXITCODE -ne 0 -or $login.Trim() -ne 'charleszon') {
    throw 'Authenticated GitHub identity must be charleszon.'
}

python scripts/scan_publication.py
if ($LASTEXITCODE -ne 0) { throw 'Publication scan failed.' }
$changes = git status --porcelain
if ($LASTEXITCODE -ne 0 -or $changes) { throw 'The publication checkout must be clean.' }
$commits = git rev-list --all --count
if ($LASTEXITCODE -ne 0 -or $commits.Trim() -ne '1') {
    throw 'Expected exactly one fresh portfolio commit; inspect history before publishing.'
}
$remotes = git remote
if ($remotes) { throw 'Expected a new checkout without an existing remote.' }

$existing = gh repo view $repoName --json nameWithOwner 2>$null
if ($LASTEXITCODE -eq 0) { throw 'Destination already exists. Stop and inspect it.' }

gh repo create $repoName --private --source . --remote origin --description 'Independent supply chain analytics portfolio with entirely synthetic data'
if ($LASTEXITCODE -ne 0) { throw 'Private repository creation failed.' }
$metadata = gh api "repos/$repoName" | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $metadata.private -ne $true -or $metadata.owner.login -ne 'charleszon') {
    throw 'Destination privacy or ownership check failed; no push performed.'
}
git push --set-upstream origin main
if ($LASTEXITCODE -ne 0) { throw 'Push failed; inspect the destination before retrying.' }
gh repo view $repoName --json nameWithOwner,isPrivate,url

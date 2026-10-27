# Publishing to GitHub

The video (often 100 MB+, above GitHub's 100 MB per-file push limit) ships as a
**Release asset**; the skill code itself is pushed to the repo normally.

## One-time setup

The user's git credential manager already holds a PAT (`git credential fill`
against `github.com`). Use it for both git and the REST API:

```powershell
$cred = "protocol=https`nhost=github.com`n" | git credential fill
$token = ($cred | Select-String "^password=").Line.Substring("password=".Length)
$headers = @{ Authorization = "token $token"; Accept = "application/vnd.github+json" }
```

Do not print or persist the token beyond the command that needs it; prefer
letting `git push` use the credential manager directly.

## Push the skill

```powershell
git init
git add SKILL.md scripts references assets agents
git commit -m "english-listening-video skill"
git remote add origin https://github.com/<user>/english-listening-video.git
git push -u origin main
```

Create the repo first if it does not exist:

```powershell
Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post `
  -Headers $headers -Body (@{ name = "english-listening-video"; description = "..."; private = $false } | ConvertTo-Json)
```

## Attach the video as a release asset

```powershell
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/<user>/english-listening-video/releases" `
  -Method Post -Headers $headers -Body (@{ tag_name = "v1.0"; name = "One-hour listening video"; body = "..." } | ConvertTo-Json)
curl.exe -s -X POST "$($release.upload_url -replace '\{\?name,label\}', '?name=english-listening-1hour.mp4')&label=1-hour%20listening%20video" `
  -H "Authorization: token $token" -H "Content-Type: video/mp4" `
  --data-binary @"C:\path\to\english-listening-1hour.mp4"
```

Release assets allow up to 2 GB per file, which covers multi-hour builds.
Include the manifest JSON and SRT in the repo or the release notes so learners
can read along.

## Checklist before publishing

- Confirm the video duration and SRT match (`ffprobe` + sample spot-checks).
- Public-domain attribution present in README and video description.
- No temporary build dirs (`_build/`, `corpus/`) committed - see .gitignore.

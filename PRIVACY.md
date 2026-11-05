# Privacy Policy — Automation Recipes Uploader

_Last updated: 5 November 2026_

**Automation Recipes Uploader** is a private, internal script operated by Neeraj Sharma, owner of the YouTube channel **Automation Recipes** (https://www.youtube.com/@automationrecipes). It uploads videos produced for that channel to that same channel only. It is not offered to, or used by, anyone else.

## What the tool uses YouTube API Services for
- `videos.insert` — upload my own videos to my own channel
- `thumbnails.set` — set the thumbnail of those videos
- read-only channel lookups for my own channel

The tool uses YouTube API Services. By using YouTube features you agree to the YouTube Terms of Service (https://www.youtube.com/t/terms) and Google's Privacy Policy (https://policies.google.com/privacy).

## Data collected
- The tool does **not** collect, store or share personal data of any YouTube user or viewer.
- The only credential is an OAuth refresh token for my own Google account. It is stored as an encrypted GitHub Actions secret, never in code, and is used only to upload to my channel.
- No YouTube API data is stored, sold, shared with third parties, or used for advertising.

## Revoking access
Access can be revoked at any time at https://myaccount.google.com/permissions or via Google's security settings page (https://security.google.com/settings/security/permissions).

## Contact
Open an issue at https://github.com/automationrecipes/youtube-pipeline/issues

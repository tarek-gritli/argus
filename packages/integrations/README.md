# Argus Integrations

External service integrations for code platforms and notifications.

## Services

- **GitHub** - GitHub App client, PR comments, webhook handling
- **GitLab** - Merge Request client, comments, events
- **Slack** - Notification adapter for review results
- **Notion** - Documentation sync adapter

## Usage

```python
from argus_integrations import GitHubClient, GitLabClient, SlackNotifier

gh = GitHubClient(app_id=..., private_key=...)
slack = SlackNotifier(webhook_url=...)
```
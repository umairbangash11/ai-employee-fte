# Research: Gmail API OAuth Sentinel

**Feature**: 003-gmail-api-oauth
**Date**: 2026-02-28
**Status**: Complete

## Research Topics

### R1: Gmail API Authentication & OAuth 2.0 Flow

**Question**: What is the best approach for OAuth 2.0 authentication with Gmail API for a local desktop application?

**Findings**:

The Gmail API uses OAuth 2.0 for authentication. For installed/desktop applications, Google provides the `InstalledAppFlow` class in `google-auth-oauthlib` that handles the complete OAuth flow:

1. **Credential Types**:
   - **OAuth 2.0 Client ID (Desktop app)**: User downloads `credentials.json` from Google Cloud Console
   - Contains: `client_id`, `client_secret`, `redirect_uris` (typically `urn:ietf:wg:oauth:2.0:oob` or `http://localhost`)

2. **Token Flow**:
   ```python
   from google_auth_oauthlib.flow import InstalledAppFlow

   SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
   flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
   credentials = flow.run_local_server(port=0)  # Opens browser, handles callback
   ```

3. **Token Storage**:
   - `credentials.to_json()` returns JSON string
   - Store in `token.json` with restricted permissions (chmod 600)

4. **Token Refresh**:
   - Access tokens expire (typically 1 hour)
   - Refresh token is long-lived
   - `credentials.refresh(google.auth.transport.requests.Request())` handles refresh

**Decision**: Use `InstalledAppFlow.run_local_server()` for initial auth (opens browser on port 0 for automatic port selection). Store token as JSON.

**References**:
- https://developers.google.com/gmail/api/quickstart/python
- https://google-auth.readthedocs.io/en/latest/reference/google_auth_oauthlib.flow.html

---

### R2: Gmail API Message Retrieval

**Question**: How to efficiently retrieve unread messages via Gmail API?

**Findings**:

1. **List Messages** (metadata only, lightweight):
   ```python
   service = build('gmail', 'v1', credentials=creds)
   results = service.users().messages().list(
       userId='me',
       q='is:unread',
       maxResults=100
   ).execute()
   messages = results.get('messages', [])  # Returns [{'id': '...', 'threadId': '...'}]
   ```

2. **Get Full Message** (per message, heavier):
   ```python
   msg = service.users().messages().get(
       userId='me',
       id=message_id,
       format='full'  # or 'metadata', 'minimal', 'raw'
   ).execute()
   ```

3. **Batch Requests** (for multiple messages):
   - Gmail API supports batch requests to reduce HTTP overhead
   - Up to 100 requests per batch

4. **Pagination**:
   - `nextPageToken` returned when more results exist
   - Pass `pageToken` parameter to get next page

5. **Labels for Urgency**:
   - `labelIds` field contains: `['UNREAD', 'INBOX', 'STARRED', 'IMPORTANT', ...]`
   - Check `'STARRED' in labelIds` or `'IMPORTANT' in labelIds`

**Decision**: Use two-phase retrieval: first `list()` for IDs, then `get()` for full content. Process incrementally to avoid memory issues with large inboxes.

---

### R3: Email Body Parsing

**Question**: How to extract plain text body from Gmail API message payload?

**Findings**:

Gmail API returns messages with a nested payload structure:

```python
# Message structure
{
    "id": "...",
    "labelIds": ["UNREAD", "INBOX"],
    "payload": {
        "mimeType": "multipart/alternative",
        "headers": [...],
        "parts": [
            {"mimeType": "text/plain", "body": {"data": "base64-encoded"}},
            {"mimeType": "text/html", "body": {"data": "base64-encoded"}}
        ]
    }
}
```

**Parsing Strategy**:
1. Check `payload.mimeType`:
   - `text/plain`: Body directly in `payload.body.data`
   - `multipart/*`: Recurse into `payload.parts`
2. Prefer `text/plain` over `text/html`
3. Decode base64url: `base64.urlsafe_b64decode(data).decode('utf-8')`

**Decision**: Implement recursive `get_message_body()` that prefers plain text, falls back to HTML (stripped of tags), truncates to reasonable length.

---

### R4: Rate Limits & Quotas

**Question**: What are Gmail API rate limits and how to handle them?

**Findings**:

1. **Default Quotas**:
   - 250 quota units per user per second
   - 1 billion quota units per day
   - `messages.list`: 5 units
   - `messages.get`: 5 units

2. **For Personal Use** (our case):
   - Polling every 5 minutes = 12 polls/hour
   - ~50 messages per poll = 50 × 5 + 5 = 255 units/poll
   - ~3,060 units/hour << daily limit

3. **Error Handling**:
   - HTTP 429: Rate limit exceeded
   - HTTP 403 with `quotaExceeded`: Daily quota exceeded
   - Implement exponential backoff for retries

**Decision**: Personal email monitoring is well within quotas. Implement exponential backoff for transient 429 errors. Log actionable message for quota exceeded errors.

---

### R5: Secure Token Storage

**Question**: Best practices for storing OAuth tokens securely on local filesystem?

**Findings**:

1. **File Permissions**:
   - Use `os.chmod(path, 0o600)` (read/write owner only)
   - Verify permissions before reading

2. **Directory Structure**:
   ```
   ./secrets/
   └── gmail/
       ├── credentials.json  # OAuth client config (user downloads)
       └── token.json        # Generated token (chmod 600)
   ```

3. **Gitignore**:
   - Add `secrets/` to `.gitignore`
   - Never commit tokens or credentials

4. **Token JSON Format**:
   ```json
   {
       "token": "ya29.a0...",
       "refresh_token": "1//0g...",
       "token_uri": "https://oauth2.googleapis.com/token",
       "client_id": "...",
       "client_secret": "...",
       "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
       "expiry": "2026-02-28T12:00:00Z"
   }
   ```

**Decision**: Store tokens as JSON with chmod 600. Create directory structure automatically. Add to `.gitignore`.

---

### R6: Header Parsing for Email Metadata

**Question**: How to extract From, Subject, Date from Gmail API message headers?

**Findings**:

Headers are returned as a list of name-value pairs:

```python
headers = message['payload']['headers']
# [{"name": "From", "value": "sender@example.com"}, ...]

def get_header(headers, name):
    for h in headers:
        if h['name'].lower() == name.lower():
            return h['value']
    return None

sender = get_header(headers, 'From')
subject = get_header(headers, 'Subject')
date = get_header(headers, 'Date')
```

**RFC 2822 Date Parsing**:
- Dates are in RFC 2822 format: `"Fri, 28 Feb 2026 10:30:00 -0500"`
- Use `email.utils.parsedate_to_datetime()` for parsing

**Decision**: Implement `get_header()` helper. Use `email.utils` for date parsing.

---

### R7: Attachment Detection

**Question**: How to detect and list attachments without downloading them?

**Findings**:

Attachments appear in message parts:

```python
def get_attachments(parts, attachments=None):
    if attachments is None:
        attachments = []
    for part in parts:
        if part.get('filename'):
            attachments.append({
                'filename': part['filename'],
                'mimeType': part['mimeType'],
                'size': part['body'].get('size', 0)
            })
        if 'parts' in part:
            get_attachments(part['parts'], attachments)
    return attachments
```

**Decision**: Extract attachment metadata (filename, MIME type, size) without downloading content. List in Markdown output per spec.

---

## Summary of Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| OAuth Library | `google-auth-oauthlib` + `google-api-python-client` | Official, well-maintained, built-in token refresh |
| Token Format | JSON in `./secrets/gmail/token.json` | Human-readable, native library support |
| Token Security | chmod 600, `.gitignore` | Standard practice for sensitive files |
| Message Retrieval | Two-phase (list IDs, then get details) | Memory efficient, handles large inboxes |
| Body Parsing | Recursive, prefer text/plain | Handles multipart messages correctly |
| Rate Limits | Exponential backoff for 429 | Standard API best practice |
| Deduplication | Use Gmail message ID | Unique, immutable, simpler than hash |
| Urgency Detection | Check for STARRED/IMPORTANT labels | Direct API support, reliable |

## Dependencies to Add

```toml
# pyproject.toml additions
google-api-python-client>=2.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=1.0
```

## Phase 0 Complete

All research questions resolved. Proceed to Phase 1 (data-model.md, contracts/, quickstart.md).

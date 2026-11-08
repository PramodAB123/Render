# Getting the YouTube refresh token in your browser (no local run needed)

1. Google Cloud Console > APIs & Services > Credentials > Create credentials > OAuth client ID
   > Application type **Web application**. Under "Authorized redirect URIs" add:
   `https://developers.google.com/oauthplayground` . Save, and copy the **Client ID** and **Client secret**.
2. Open https://developers.google.com/oauthplayground
3. Click the gear icon (top right) > tick **Use your own OAuth credentials** > paste the Client ID and secret.
4. In "Step 1", type this scope in the box and click **Authorize APIs**:
   `https://www.googleapis.com/auth/youtube.upload`
   Sign in with the Google account that owns your channel, pick the channel, and allow.
5. In "Step 2", click **Exchange authorization code for tokens**. Copy the **Refresh token**.
6. In your GitHub repo > Settings > Secrets and variables > Actions > New repository secret, add:
   `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

The OAuth consent screen must be **published** ("In production"), otherwise the refresh token stops working after 7 days.

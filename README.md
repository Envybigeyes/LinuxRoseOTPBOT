## Uploading a Custom Audio Script

You can personalize your call by uploading an MP3 or WAV file to be played as the script. Use any audio recording tool (e.g., Audacity, Voice Memos) and export the file in MP3 or WAV format. Upload via the dashboard and the bot will play it during the call.

## Adding More Preset Scripts

To add more preset scripts, edit the `PRESET_SCRIPTS` dictionary in `app.py`. Use `{victim_name}`, `{victim_phone}`, `{phone_last4}`, or `{bank}` for personalization.
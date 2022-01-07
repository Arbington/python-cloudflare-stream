# python-cloudflare-stream

> A basic Python API wrapper for working with Cloudflare Stream.

[Arbington.com](https://arbington.com) started off using Cloudflare Stream. We used their API very heavily and pulled out our code into a simple
client for others to use. It's not perfect, nor is it close to being complete. But it's a good start for anyone who wishes to contribute!

## Installation

```bash
pip install python-cloudflare-stream
```

## Setup
You will need a Cloudflare account with Stream minutes added. We recommend starting small with a $5 subscription just to get your feet wet.

Once you have your Cloudflare Stream subscription you'll need:
* Your Account ID, which you can find in your Cloudflare Dashboard.
* Your email address you used for Cloudflare
* Your API key
* Then run:
```python
from python_cloudflare_stream.client import StreamClient

keys = StreamClient.create_signing_keys()
print(keys)
```

That will give the PEM key you will need and the "signing token". Save these as they are only displayed once.

## Understanding Cloudflare Stream
Stream is a bit different from other platforms. It's very basic, fast, reliable and moderately priced.

Everytime you upload a video, the video receives a "UID". You'll want to store this UID as it's the only way to refer to a video through their API.

Here is some example code to get you started:

```python
from python_cloudflare_stream.client import StreamClient

keys = StreamClient.create_signing_keys('your-cloudflare-account-id', 'you@website.com', 'your-api-key')  # Gives you your PEM and signing_token (called an "id") if you don't have that already. These are only displayed once per API call and aren't shown when listing your keys

# Store these somewhere safe.
signing_token = keys['result']['id']
pem = keys['result']['pem']

# Init the client
client = StreamClient(
    auth_email='you@website.com',
    auth_api_key='qwertyqwertyqwertyqwertyqwertyqwerty',
    account_id='asdf1asdf2asdf3asdf4asdf5',
    pem='LS0TEASRASDASDa-VERY-long-string-here=',
    signing_token='qwertyqwertyqwertyqwertyqwerty',
)

# Sample download URL
download_url = 'https://yourwebsite.com/video.mp4'
# Tell Cloudflare to download the sample download URL from above
video_uid, all_data_dict = client.pull_from_url(download_url, 'Test video', require_signed_url=True, watermark_uid=None)

# Get details about a specific video from its video_uid
data = client.get_video(video_uid)

# Get the total minutes in your account, and the total remaining minutes
client.get_total_storage_minutes()
client.get_remaining_cloudflare_minutes()

# Create a download URL from Cloudflare. Wait until its ready, or return a URL that can be used sometime in the future.
download_url = client.get_download_url(video_uid, wait_until_ready=True)

# Delete a video
deleted = client.delete_video(video_uid)

# List up to 1000 videos at once
videos = client.get_all_videos()
```

## Contributing
Happy to accept contributions of any size!

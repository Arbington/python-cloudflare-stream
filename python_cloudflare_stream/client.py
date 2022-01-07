"""
See more at the official Cloudflare Stream docs:
https://api.cloudflare.com/#stream-videos-properties
"""

import requests
import time


class StreamClient:

    def __init__(self, auth_email: str=None, auth_api_key: str=None, account_id: str=None, pem: str=None, signing_token: str=None) -> None:
        self.AUTH_EMAIL = auth_email
        self.AUTH_API_KEY = auth_api_key
        self.ACCOUNT_ID = account_id
        self.PEM = pem
        self.SIGNING_TOKEN = signing_token

        # The standard request headers, minus the pem.
        self._request_headers = {
            "X-Auth-Email": self.AUTH_EMAIL,
            "X-Auth-Key": self.AUTH_API_KEY,
            "Content-Type": "application/json",
        }

    @classmethod
    def create_signing_keys(cls, account_id, account_email, cloudflare_api_key) -> dict:
        """
        An API call to create signing keys to use in this client.
            :account_id                 str         Your CloudFlare account ID
            :returns                    dict
            {
                "id":       "kajshdkashdakshdasda",  # This is your signing_token
                "pem":      "a massive string you'll want to save and use the PEM key in this client",
                "jwk":      "if you need a jwk it will be presented here as a massive string as well.
            }

        Usage:
        keys = StreamClient.create_signing_keys('youraccountidhere')
        """
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/stream/keys"
        response = requests.post(url, headers={
            "X-Auth-Email": account_email,
            "X-Auth-Key": cloudflare_api_key,
            "Content-Type": "application/json",
        })
        data = response.json()
        return data

    def delete_video(self, cloudflare_video_uid: str) -> int:
        """
        Return JSON data from CloudFlare Stream about a particular video.
            :cloudflare_video_uid       str         The Video UUID provided by Cloudflare

            :returns                    int         Returns the request's status code.
                                                    Returns 200 is the video was deleted.
        """
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/stream/{cloudflare_video_uid}/"
        res = requests.delete(url, headers=self._request_headers)  # noqa
        return res.status_code

    def get_total_storage_minutes(self) -> int:
        """
        Gets the total number of minutes available in your CloudFlare Stream plan.
            :returns                    int         Returns an int representing the total
                                                    minutes allotted in your account
        """
        url = f'https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/stream/storage-usage'
        res = requests.get(url, headers=self._request_headers)
        data = res.json()
        return int(data['result']['totalStorageMinutesLimit'] )

    def get_remaining_cloudflare_minutes(self) -> int:
        """
        Gets the total number of minutes remaining in your CloudFlare Stream plan.
            :returns                    int         Returns an int representing the total
                                                    minutes remaining in your account
        """
        url = f'https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/stream/storage-usage'
        res = requests.get(url, headers=self._request_headers)
        data = res.json()
        total_remaining = data['result']['totalStorageMinutesLimit'] - data['result']['totalStorageMinutes']
        return int(total_remaining)

    def get_video(self, cloudflare_video_uid: str) -> dict:
        """
        Return JSON data from CloudFlare Stream about a particular video.
            :cloudflare_video_uid       str         The Video UUID provided by Cloudflare
            :return                     dict        Returns a dictionary with all the video data.
        """
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/stream/{cloudflare_video_uid}/"
        res = requests.get(url, headers=self._request_headers)
        return res.json()

    def pull_from_url(self, url: str, video_title: str, require_signed_url: bool=False, watermark_uid: str=None) -> tuple:
        """
        Tell CloudFlare to download a video from a URL.
        By default the "state" of the video is "downloading" with Cloudflare Stream.
            :url                        str         The URL to download from. Must not be a protected URL.
            :video_title                str         The title of the video in CloudFlare Stream
            :require_signed_url         bool        Default: False. Signed urls need to be accessed through the API and
                                                    can only exist for a short period of time.
            :watermark_uid              str         Default: None. The watermark UID that Stream provides to watermark
                                                    your videos as they are transcoded.
            :returns                    tuple       Returns a tuple where the first value is the new Video UUID.
                                                    You will want to store the UID.
                                                    The second value is the entire JSON response, should you need to
                                                    know more about the video before transcoding starts.
        """
        payload = {
            "url": url,
            "requireSignedURLs": require_signed_url,
            "meta": {
                "name": video_title,
            },
            # "watermark": {
            #     "uid": "07ed42591c7cfdd630bf7a158c5fb1b0"
            # }
        }

        if watermark_uid:
            payload['watermark']['uid'] = watermark_uid

        response = requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/stream/copy",
            json=payload,
            headers=self._request_headers,
        )
        response_json = response.json()
        return (response_json["result"]["uid"], response_json,)

    def get_download_url(self, cloudflare_video_uid, wait_until_ready: bool=False) -> str:
        """
        Get the download URL from a video that requires signing. Cloudflare doesn't provide download links on the fly
        so we need to request a link, the video is processed, and then we can access the download URL later.

        For this we need a signing token, and a pem (both as a strings).

        Caveat: Download URLs are only available for up to 24 hours. Anything higher than that and Cloudflare returns
        a super annoying 403 response.

            :cloudflare_video_uid       str         The Video UUID provided by Cloudflare
            :wait_until_ready           bool        Default: False. Wait until the video is done processing before
                                                    returning the URL. Useful if you have patience; less useful for
                                                    anything in user-facing web development.
            :returns                    str         Returns the URL of the download link. Unless this times out after 300
                                                    seconds, then it will return None. But with 55,000+ videos, we've
                                                    never seen it take longer than that.
        """
        data = {
            "id": self.SIGNING_TOKEN,
            "pem": self.PEM,
            "exp": int(time.time()) + (60 * 60 * 24),  # Max 24 hours otherwise CloudFlare returns a 403 response
            "downloadable": True,
        }
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/stream/{cloudflare_video_uid}/token"
        res = requests.post(url, json=data, headers=self._request_headers)

        token = res.json()['result']['token']

        for _ in range(30):
            # 30x 10 second periods to wait for a video's download URL to be generated by Cloudflare
            response = requests.post(
                f"https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/stream/{cloudflare_video_uid}/downloads",
                headers=self._request_headers,
                json={
                    "authorization": f"Bearer {token}",
                },
            )

            if not wait_until_ready:
                # If you don't wait until the video is ready to be downloaded...
                # This can be useful if you're storing the URL for later use.
                return f'https://videodelivery.net/{token}/downloads/default.mp4'

            response_json = response.json()
            status = response_json['result']['default']['status']  # ie. `ready`

            if status == 'ready':
                return f'https://videodelivery.net/{token}/downloads/default.mp4'
            else:
                # percent_complete = response_json['result']['default']['percentComplete']
                # print(f"Not ready yet ({percent_complete}%).. waiting 10 seconds")
                time.sleep(10)

    def get_signed_url(self, cloudflare_video_uid: str) -> str:
        """
        If a video requires a signed URL, then sign it and return the signed link. Usually you would use:
        https://iframe.videodelivery.net/{cloudflare_video_uid} to stream a video. But with a signed URL, you would use:
        https://iframe.videodelivery.net/{client.get_signed_url()} - replacing the normal uid with a signed UID.

        Signed videos are valid for 60 minutes by default.

            :cloudflare_video_uid       str         The Video UUID provided by Cloudflare
            :return                     str         Returns the signed token whih should replace the cloudflare_video_uid
                                                    when attempting to stream a video.
        """
        url = f"https://util.cloudflarestream.com/sign/{cloudflare_video_uid}"
        data = {
            "id": self.SIGNING_TOKEN,
            "pem": self.PEM,
            "exp": int(time.time() + (60 * 60)),
        }
        res = requests.post(url, json=data)
        return res.text

    def get_all_videos(self) -> dict:
        """
        Returns 1000 videos in a massive dictionary.
        The videos will be found in the response_json['result'] item.
        """

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/stream/"
        response = requests.get(url, headers=self._request_headers)
        response_json = response.json()
        return response_json

    def list_signing_keys(self) -> dict:
        """
        Returns a list of your signing keys. Any key can sign for any video.

        Caveat: Listing your keys will not display your PEM or JWK again. Those are created and shown ONCE.
        """
        response = requests.get(f"https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/stream/keys", headers=self._request_headers)
        data = response.json()
        return data

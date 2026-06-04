import base64
import hashlib
import hmac
import json
import time
import httpx


class BaiduOCRProvider:
    """百度云 OCR — 通用文字识别（高精度版）。"""

    def __init__(self, api_key: str, secret_key: str):
        if not api_key:
            raise ValueError("百度 OCR API Key 未配置。请设置 BAIDU_OCR_API_KEY 环境变量。")
        if not secret_key:
            raise ValueError("百度 OCR Secret Key 未配置。请设置 BAIDU_OCR_SECRET_KEY 环境变量。")
        self.api_key = api_key
        self.secret_key = secret_key
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.secret_key,
                },
            )
        if resp.status_code != 200:
            raise RuntimeError(f"百度 OCR 获取 token 失败: {resp.text}")
        self._access_token = resp.json()["access_token"]
        return self._access_token

    async def analyze(self, image: str, prompt: str) -> dict:
        token = await self._get_access_token()

        # 提取 base64 数据
        if image.startswith("data:"):
            image_data = image.split(",", 1)[1]
        else:
            image_data = image

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic",
                params={"access_token": token},
                data={"image": image_data},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if resp.status_code != 200:
            raise RuntimeError(f"百度 OCR 调用失败 ({resp.status_code}): {resp.text}")

        data = resp.json()
        words = [item["words"] for item in data.get("words_result", [])]
        return {
            "text": "\n".join(words),
            "model": "baidu-ocr",
            "usage": {"total_words": data.get("words_result_num", len(words))},
        }


class TencentOCRProvider:
    """腾讯云 OCR — 通用印刷体识别。"""

    def __init__(self, secret_id: str, secret_key: str):
        if not secret_id:
            raise ValueError("腾讯云 OCR SecretId 未配置。请设置 TENCENT_SECRET_ID 环境变量。")
        if not secret_key:
            raise ValueError("腾讯云 OCR SecretKey 未配置。请设置 TENCENT_SECRET_KEY 环境变量。")
        self.secret_id = secret_id
        self.secret_key = secret_key

    def _sign(self, payload: str, timestamp: int) -> str:
        service = "ocr"
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        credential = f"{self.secret_id}/{date}/{service}/tc3_request"
        string_to_sign = f"TC3-HMAC-SHA256\n{timestamp}\n{credential}\n" + hashlib.sha256(payload.encode()).hexdigest()
        secret_date = hmac.new(f"TC3{self.secret_key}".encode(), date.encode(), hashlib.sha256).digest()
        secret_service = hmac.new(secret_date, service.encode(), hashlib.sha256).digest()
        secret_signing = hmac.new(secret_service, "tc3_request".encode(), hashlib.sha256).digest()
        return hmac.new(secret_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    async def analyze(self, image: str, prompt: str) -> dict:
        if image.startswith("data:"):
            image_base64 = image.split(",", 1)[1]
        else:
            image_base64 = image

        body = json.dumps({"ImageBase64": image_base64})
        timestamp = int(time.time())
        signature = self._sign(body, timestamp)
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://ocr.tencentcloudapi.com",
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": f"TC3-HMAC-SHA256 Credential={self.secret_id}/{date}/ocr/tc3_request, SignedHeaders=content-type;host;x-tc-action, Signature={signature}",
                    "Host": "ocr.tencentcloudapi.com",
                    "X-TC-Action": "GeneralAccurateOCR",
                    "X-TC-Timestamp": str(timestamp),
                    "X-TC-Version": "2018-11-19",
                },
                content=body,
            )

        if resp.status_code != 200:
            raise RuntimeError(f"腾讯云 OCR 调用失败 ({resp.status_code}): {resp.text}")

        data = resp.json()
        detections = data.get("Response", {}).get("TextDetections", [])
        texts = [d["DetectedText"] for d in detections]
        return {
            "text": "\n".join(texts),
            "model": "tencent-ocr",
            "usage": {"total_detections": len(detections)},
        }

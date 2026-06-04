from typing import Any

import requests


class ShagoClientError(Exception):
    pass


class ShagoClient:
    def __init__(
        self,
        api_url: str,
        token: str = "",
        timeout: int = 120,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "shagoai-cli",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    def request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.api_url}{path}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers(),
                json=json_body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ShagoClientError(
                f"Cannot connect to Shago AI Server: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise ShagoClientError(
                f"Shago AI Server error {response.status_code}: {response.text}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise ShagoClientError(
                f"Invalid JSON response from Shago AI Server: {response.text}"
            ) from exc

    def health(self) -> dict[str, Any]:
        return self.request("GET", "/v1/health")

    def models(self) -> dict[str, Any]:
        return self.request("GET", "/v1/models")

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str = "default",
        temperature: float = 0.2,
        max_turns: int = 8,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "max_turns": max_turns,
        }

        return self.request("POST", "/v1/chat", payload)

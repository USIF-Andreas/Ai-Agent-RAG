import json
import os
import time

import requests


BASE_URL = os.getenv(
    "AGENTS_BASE_URL",
    "http://127.0.0.1:8018",
).rstrip("/")
PROCESS_URL = f"{BASE_URL}/api/agents/process"
HEALTH_URL = f"{BASE_URL}/docs"
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 440
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def build_headers() -> dict:
    headers = {"Accept": "application/json"}

    # Some deployments protect /api endpoints with bearer auth.
    auth_token = os.getenv("AGENTS_AUTH_TOKEN")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    # GitHub Codespaces forwarded URLs may require an extra token header.
    github_token = os.getenv("CODESPACES_AUTH_TOKEN")
    if github_token and ".app.github.dev" in BASE_URL:
        headers["X-GitHub-Token"] = github_token

    return headers


def build_payload() -> dict:
    ts = int(time.time())
    return {
        "text": (
            "I reviewed the strategic operational matrix with Marwa and Salim before dawn, "
            "then discussed with them updates on regulatory compliance and the digital transformation plan at headquarters, "
            "and after that I met them at the archive to review notes on accumulated risks."
        ),
        "space_slug": f"complex-ar-test-{ts}",
        "message_id": f"msg-complex-ar-test-{ts}",
        "conversation_title": "complex arabic request",
    }


def ensure_server_up() -> None:
    try:
        resp = requests.get(HEALTH_URL, timeout=(CONNECT_TIMEOUT, 10))
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            "API server is not reachable. "
            "Start it on 127.0.0.1:8018 or set AGENTS_BASE_URL to your running endpoint."
        ) from exc


def main() -> None:
    payload = build_payload()
    headers = build_headers()

    try:
        ensure_server_up()
        print(f"Server reachable at {BASE_URL}. Sending request...")
        if ".app.github.dev" in BASE_URL and "X-GitHub-Token" not in headers:
            print(
                "Tip: this looks like a Codespaces forwarded URL. "
                "If you get 401, set CODESPACES_AUTH_TOKEN or use AGENTS_BASE_URL=http://127.0.0.1:8018."
            )

        resp = None
        for attempt in range(1, MAX_RETRIES + 1):
            resp = requests.post(
                PROCESS_URL,
                json=payload,
                headers=headers,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

            # 504 from a gateway/proxy is often transient for long processing.
            if resp.status_code == 504 and attempt < MAX_RETRIES:
                wait_s = RETRY_BACKOFF_SECONDS * attempt
                print(f"Attempt {attempt}/{MAX_RETRIES} got 504. Retrying in {wait_s}s...")
                time.sleep(wait_s)
                continue

            resp.raise_for_status()
            break
    except requests.Timeout:
        print(
            "Request timed out while waiting for response. "
            "Try a shorter input sentence or increase READ_TIMEOUT."
        )
        return
    except RuntimeError as exc:
        print(str(exc))
        return
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        print(f"HTTP error after retries: {status} - {exc}")
        if exc.response is not None and exc.response.text:
            print("Response body:")
            print(exc.response.text[:2000])
        return
    except requests.RequestException as exc:
        print(f"HTTP request failed: {exc}")
        return
    except KeyboardInterrupt:
        print("Request interrupted by user (Ctrl+C).")
        return

    print("status:", resp.status_code)
    try:
        data = resp.json()
        print(json.dumps(data.get("stats", {}), ensure_ascii=False, indent=2))
    except ValueError:
        print("Response is not valid JSON:")
        print(resp.text)


if __name__ == "__main__":
    main()
# Deploying VyaparAI on Alibaba Cloud

The hackathon requires the project to run on **Alibaba Cloud** and to use **Qwen Cloud
APIs** (we already do — see `backend/agent/qwen_client.py`). Pick **one** path below.

## Environment variables (both paths)
Never commit these. Set them on the platform, not in a file inside the image/repo.

| Var | Value |
|---|---|
| `QWEN_API_KEY` | your `sk-ws-...` key |
| `QWEN_BASE_URL` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |
| `QWEN_MODEL` | `qwen-plus` |
| `SELLER_GSTIN` | `29ABCDE1234F1Z5` (demo) |

---

## Path A — Function Compute (serverless, recommended)
Managed HTTPS URL, no idle cost, scales to zero. Needs Docker locally + a Container
Registry (ACR) repo.

1. **Create an ACR repo** — Alibaba Cloud console → Container Registry → Personal
   Edition (free) → create a namespace (e.g. `vyapar`) and image repo `vyapar`.
2. **Build, tag, push** (replace `<region>` e.g. `ap-southeast-1`, `<ns>`):
   ```bash
   docker build -t vyapar .
   docker login registry.<region>.aliyuncs.com          # ACR username/password
   docker tag vyapar registry.<region>.aliyuncs.com/<ns>/vyapar:latest
   docker push registry.<region>.aliyuncs.com/<ns>/vyapar:latest
   ```
3. **Create the function** — Function Compute console → Create Function →
   **Container Image** → pick the pushed image.
   - **Listening port:** `9000`
   - **Environment variables:** add the four vars from the table above.
   - **Trigger:** enable **HTTP trigger**, auth = **anonymous** (so judges can open it).
4. **Deploy → copy the public URL.** Open it — you should see the review UI.

> CLI alternative: install [Serverless Devs](https://www.alibabacloud.com/help/en/functioncompute/fc/developer-reference/install-serverless-devs-and-docker)
> (`npm i -g @serverless-devs/s`), author an `s.yaml` for an `fc3` custom-container
> function on port 9000, then `s deploy`.

---

## Path B — ECS virtual machine (simplest, no Docker)
A small VM with a public IP. Surest way to get a stable link fast; coupon covers it.

1. **Create the instance** — ECS console → Create Instance → Ubuntu 22.04,
   smallest burstable type (e.g. `ecs.t6`), **assign public IPv4**, pay-as-you-go.
2. **Security group** — add inbound rules allowing TCP **22** (SSH) and **8000**
   (app) from `0.0.0.0/0`.
3. **SSH in and set up:**
   ```bash
   ssh root@<public-ip>
   apt update && apt install -y python3-venv python3-pip git
   git clone <your-repo-url> vyapar && cd vyapar
   python3 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Add env file** `/etc/vyapar.env` (the four vars, `KEY=value` per line).
5. **Run as a service** (auto-restart, survives reboot):
   ```bash
   cp deploy/vyapar.service /etc/systemd/system/vyapar.service
   systemctl daemon-reload && systemctl enable --now vyapar
   systemctl status vyapar        # should be active (running)
   ```
6. **Open** `http://<public-ip>:8000` — the review UI should load.

---

## Capture your deployment proof (for Devpost)
- A screenshot of the **Function Compute function / ECS instance** in the Alibaba
  Cloud console.
- The **live URL** open in a browser showing the working app.
- Note in your submission that reasoning runs on **Qwen models via Qwen Cloud**
  (`qwen-plus`, OpenAI-compatible endpoint) — the required-API proof.

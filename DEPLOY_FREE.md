# Deploying Soil Analytics for free

> **No card?** Use [DEPLOY_RENDER.md](DEPLOY_RENDER.md) (Render + Neon, one container) or Path C (laptop demo) below. Oracle (Path A) and AWS (Path B) need a Visa/Mastercard/Amex card.

This is the shortest free path. It uses the files already in the project (`docker-compose.prod.yml`, `deploy/Caddyfile`,
`.env.prod.example`). For the full details (buckets, backups, troubleshooting) see [DEPLOYMENT.md](DEPLOYMENT.md).

## What is free and what is not (checked 18 Nov 2026, prices change, confirm on each page)

| Need | Free option | Catch |
|---|---|---|
| Server | **Oracle Cloud Always Free, Arm VM: 2 OCPU, 12 GB RAM, 200 GB disk, 10 TB/month traffic** | Needs a card for identity check. Oracle may reclaim a VM that stays idle for 7 days (CPU, network and memory all under 20%). New VMs can show "out of capacity": retry later or try another availability domain. |
| Server (alternative) | **AWS Free Plan**: $100 credit at sign-up plus up to $100 more for completing 5 tasks | Lasts 6 months or until credits run out, then you must upgrade or stop. Use a 4 GB instance. |
| HTTPS certificate | **Caddy + Let's Encrypt** (already in the project) | None. |
| Web address | **DuckDNS** free subdomain (`yourname.duckdns.org`) or `sslip.io` | Not a custom brand name. |
| Database | **PostgreSQL in Docker on the same server** | Back it up (`deploy/backup.sh`). |
| Photos | **The server's disk** (`STORAGE_BACKEND=local`) or **Cloudflare R2** (S3 compatible, free tier) | Local disk is lost if the VM is deleted. |
| Voice | Sarvam AI | **Needs credit**, it is not free. Without a key the Listen button is hidden. |
| Code | GitHub | None. |

Options that do **not** work for this project:
- **Hugging Face Spaces**: Docker Spaces need a paid plan (Hugging Face's own docs), and the free disk is not persistent.
- **Neon / Supabase free database + free app hosts**: free app hosts have too little memory for PyTorch (the image model), and Neon's free database sleeps after 5 minutes idle and has 1 GB storage.
- **Google Cloud e2-micro**: only 1 GB RAM, too small to load the models.

## Lighter image model (ONNX), for small free servers
The server no longer needs PyTorch. The image model is converted once to ONNX (`backend/scripts/export_onnx.py`) and runs on
ONNX Runtime; Grad-CAM is calculated directly from the last layer. In a test on a sample of images it matched the PyTorch
results (probabilities within 0.00004) and used about 310 MB of memory for the API, instead of well over 1 GB. This is what could
make a 512 MB free host possible. It has not yet been tried on a real free host, and the web app also needs hosting
(about 100 MB more if it shares the server).

```bash
cd backend
pip install -r requirements-dev.txt            # torch is only needed for this one-time step
python scripts/export_onnx.py models/soil_cnn_D_hard_negatives.pt models
# creates models/soil_cnn.onnx and models/soil_cnn_head.npz; the server uses them automatically
```

## Path A: Oracle Cloud Always Free (recommended)

### 1. Create the account and the server
1. Sign up at <https://www.oracle.com/cloud/free/>. Choose a home region near you (for example Mumbai or Hyderabad). It cannot be changed later.
2. Compute > Instances > **Create instance**:
   - Image: **Ubuntu 24.04** (aarch64).
   - Shape: **Ampere, VM.Standard.A1.Flex, 2 OCPU, 12 GB** (the Always Free limit).
   - Boot volume: 50 to 100 GB.
   - Networking: assign a public IPv4 address. Download the SSH private key when asked.
3. Networking > your VCN > Security List > **Add ingress rules** from `0.0.0.0/0`: TCP **80**, TCP **443**, UDP **443**. (Port 22 is already open.)
4. Optional but useful: Networking > Reserved public IPs > attach one so the address never changes.

### 2. Open the server's own firewall (Oracle Ubuntu images block ports by default)
```bash
ssh -i ~/Downloads/your-key.key ubuntu@YOUR_SERVER_IP
sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -p udp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

### 3. Free web address (DuckDNS)
1. Go to <https://www.duckdns.org>, sign in, create a subdomain such as `soilapp`, and set its IP to your server's public IP.
2. Your address is now `soilapp.duckdns.org`. Quick check: `ping soilapp.duckdns.org`.
   (No sign-up alternative: use `YOUR-IP-WITH-DASHES.sslip.io`, for example `129-154-10-20.sslip.io`.)

### 4. Install Docker and get the code
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER        # log out and back in
git clone https://github.com/<org>/<repo>.git soil-analytics
cd soil-analytics
git switch Team-C--milestone-3
```
For a private repository use a GitHub personal access token as the password when Git asks.

### 5. Copy the model files (they are not in Git) from your laptop
```bash
scp -i ~/Downloads/your-key.key backend/models/* ubuntu@YOUR_SERVER_IP:~/soil-analytics/backend/models/
```

### 6. Configure
```bash
cp .env.prod.example .env.prod && chmod 600 .env.prod
python3 -c "import secrets; print(secrets.token_urlsafe(48))"     # run twice: one for SECRET_KEY, one for POSTGRES_PASSWORD
nano .env.prod
```
Set `DOMAIN=soilapp.duckdns.org`, `POSTGRES_PASSWORD`, `SECRET_KEY`, keep `STORAGE_BACKEND=local`, and add `SARVAM_API_KEY` if you have credit.

### 7. Start
```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml ps     # backend should become "healthy"
```
The first build takes 10 to 20 minutes on the Arm server. Open `https://soilapp.duckdns.org`.

### 8. Check it works
Sign up, add a photo and lab values, run the analysis, open the fertiliser plan and PDF, then on a phone use **Install app** and test offline mode. The full checklist is in DEPLOYMENT.md section 6.

### 9. Keep it healthy
- Updates: `git pull` then the same `up -d --build` command.
- Backups: `crontab -e` and add `30 2 * * * cd ~/soil-analytics && sh deploy/backup.sh >> backups/backup.log 2>&1`. Copy `backups/` off the server now and then.
- Idle reclamation: Oracle may reclaim an unused free VM. Watch for its emails, and keep a copy of your backups and `.env.prod`.
- Add a free uptime monitor (for example UptimeRobot) on `https://soilapp.duckdns.org/api/v1/health` to be told when it is down.

### Not yet tested here
The Docker images, Caddy HTTPS and the Arm (aarch64) build have not been run on a real server. PyTorch, XGBoost and OpenCV publish Arm builds, so it should work, but the first run may need small fixes. Send the output of `docker compose ... logs backend` if something fails.

## Path B: AWS Free Plan (6 months)
Same steps as Path A, with these differences:
1. Create the account at <https://aws.amazon.com/free/>. Finish the tasks that earn the extra credit.
2. EC2 > **Launch instance**: Ubuntu 24.04, **4 GB RAM** (for example t3.medium, or the largest size the Free Plan allows), 30 GB disk, a key pair, and a security group allowing 22 (your IP), 80 and 443.
3. Attach an **Elastic IP** so the address stays the same, and delete the instance and IP when the credits end to avoid charges.
4. You do not need the `iptables` step. Everything else (DuckDNS, Docker, models, `.env.prod`, `up -d --build`) is identical.

## Path C: demo from your laptop (no server)
Good for a presentation when no cloud account is ready. Run the production stack on the laptop and share it over a free tunnel.
```bash
# in .env.prod use: DOMAIN=:80  (Caddy serves plain HTTP on port 80)
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
cloudflared tunnel --url http://localhost:80      # prints a temporary https://....trycloudflare.com address
```
Open that address on the phone. It changes every time and stops when you close the terminal, so it is for demos only.
This path is also untested here.

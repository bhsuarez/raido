# Download Gateway — VPN LXC Configuration

This document describes the Proxmox LXC container setup for the **Download Gateway**:
a hardened Mullvad WireGuard tunnel that routes all torrent traffic through a VPN
with a strict kill-switch, while remaining accessible via your local subnet and Tailscale.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  Proxmox Host                                            │
│                                                          │
│  ┌──────────────────────────┐   bind mount (instant)    │
│  │  Raido LXC (Clean)       │ ◄──────────────────────── │
│  │  - Lidarr :8686          │                 /mnt/music │
│  │  - Raido API (proxy)     │                            │
│  └────────────┬─────────────┘                            │
│               │ local LAN (192.168.1.x)                  │
│  ┌────────────▼─────────────┐                            │
│  │  Gateway LXC (VPN)       │                            │
│  │  - Prowlarr :9696        │                            │
│  │  - qBittorrent :8080     │                            │
│  │  - wg0 → Mullvad         │                            │
│  │  - kill-switch (nftables)│                            │
│  └──────────────────────────┘                            │
└──────────────────────────────────────────────────────────┘
```

**Key design principle:** Lidarr lives on the **clean** Raido LXC with no VPN,
while Prowlarr and the torrent client run inside the **gateway LXC** where ALL
traffic exits via the Mullvad tunnel. Lidarr talks to Prowlarr over the local LAN.

---

## 1. Gateway LXC Setup (Proxmox)

### Create the container

```bash
# On Proxmox host
pct create 200 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname raido-gateway \
  --memory 2048 \
  --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.201/24,gw=192.168.1.1 \
  --rootfs local-lvm:20 \
  --unprivileged 0 \
  --features keyctl=1,nesting=1

# Allow WireGuard TUN inside LXC (required)
# Edit /etc/pve/lxc/200.conf and add:
echo 'lxc.cgroup2.devices.allow: c 10:200 rwm' >> /etc/pve/lxc/200.conf
echo 'lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file' >> /etc/pve/lxc/200.conf
```

### Music library bind mount (instant local imports)

The gateway container mounts the completed downloads folder so Lidarr can
move imported files directly into the music library without network transfer.

```bash
# Add to /etc/pve/lxc/200.conf (on Proxmox host):
# mp0: /mnt/music,mp=/mnt/music,acl=1,backup=0
# mp1: /mnt/downloads,mp=/mnt/downloads,acl=1,backup=0

# Or via UI: Container → Resources → Add → Mount Point
# Source: /mnt/downloads (host path for completed downloads)
# Destination: /mnt/downloads (inside LXC)
```

### UID/GID alignment

Check the current UID/GID of your music folder on the host:

```bash
# On Proxmox host
ls -lna /mnt/music | head -5
# e.g. uid=1000 (raido user)

# Ensure the same UID owns the downloads folder
chown -R 1000:1000 /mnt/downloads
```

Inside the gateway LXC, create a matching user:

```bash
useradd -u 1000 -g 1000 -M -s /sbin/nologin media
```

---

## 2. WireGuard / Mullvad Setup (inside Gateway LXC)

```bash
apt update && apt install -y wireguard wireguard-tools nftables resolvconf

# Download your Mullvad config (replace with your account config)
# Place at /etc/wireguard/wg0.conf
```

### /etc/wireguard/wg0.conf

```ini
[Interface]
PrivateKey = <YOUR_MULLVAD_PRIVATE_KEY>
Address = 10.64.x.x/32
DNS = 10.64.0.1
PostUp = nft -f /etc/nftables-vpn-killswitch.conf
PreDown = nft flush ruleset

[Peer]
PublicKey = <MULLVAD_SERVER_PUBLIC_KEY>
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = <MULLVAD_SERVER_IP>:51820
PersistentKeepalive = 25
```

### Kill-switch (nftables)

Create `/etc/nftables-vpn-killswitch.conf`:

```nftables
# VPN Kill-Switch — block all traffic except WireGuard and local LAN
table inet vpn_killswitch {
  chain output {
    type filter hook output priority 0; policy drop;

    # Allow loopback
    oif "lo" accept

    # Allow WireGuard tunnel traffic (to Mullvad endpoint)
    udp dport 51820 accept

    # Allow LAN (so Lidarr on clean LXC can reach Prowlarr/qBittorrent)
    ip daddr 192.168.1.0/24 accept

    # Allow Tailscale (if installed)
    oif "tailscale0" accept

    # Allow established/related
    ct state established,related accept

    # Allow traffic through VPN tunnel
    oif "wg0" accept
  }

  chain input {
    type filter hook input priority 0; policy drop;
    iif "lo" accept
    iif "wg0" accept
    ct state established,related accept
    # Allow LAN access to Prowlarr and qBittorrent UIs
    ip saddr 192.168.1.0/24 accept
  }
}
```

Enable and start:

```bash
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Verify all traffic exits through Mullvad
curl --interface wg0 https://am.i.mullvad.net/json
```

---

## 3. Prowlarr (inside Gateway LXC)

```bash
# Install Prowlarr as a service
curl -sL https://services.sonarr.tv/v1/scripts/install.sh | bash -s prowlarr

# Prowlarr listens on port 9696 by default
# Configure indexers via web UI: http://192.168.1.201:9696
```

---

## 4. qBittorrent (inside Gateway LXC)

Mullvad does not support port forwarding. Configure qBittorrent for **passive mode**:

```bash
apt install -y qbittorrent-nox

# Run as the media user
sudo -u media qbittorrent-nox --webui-port=8080 &
```

### qBittorrent optimizations for no port forwarding

In Settings → Connection:
- **Listening port**: 6881 (not advertised, passive only)
- **Use UPnP / NAT-PMP**: Disabled
- **DHT**: Enabled (helps find peers without tracker)
- **PeX**: Enabled
- **Local Peer Discovery**: Enabled
- **Encryption**: Preferred (not required — more peers)
- **Max connections**: 500
- **Max upload slots**: 100

In Settings → BitTorrent:
- **Seeding**: Until ratio 1.0 (or as per your preference)

```ini
# /home/media/.config/qBittorrent/qBittorrent.conf (key settings)
[BitTorrent]
Session\DisableAutoTMMByDefault=false
Session\Port=6881
Session\UPnPEnabled=false
Session\NATEnabled=false
Session\DHT\Enabled=true
Session\PEX\Enabled=true
Session\LSD\Enabled=true
Session\Encryption=1
Session\MaxActiveDownloads=5
Session\SavePath=/mnt/downloads/complete
Session\TempPath=/mnt/downloads/incomplete
```

---

## 5. Lidarr Configuration (Raido LXC — clean side)

Lidarr runs in the Raido Docker Compose stack (see docker-compose.yml).
Configure Lidarr to talk to Prowlarr and qBittorrent over the LAN:

### In Lidarr UI → Settings → Download Clients

Add qBittorrent:
- **Host**: 192.168.1.201 (Gateway LXC IP)
- **Port**: 8080
- **Category**: lidarr
- **Remote Path Mappings**: `/mnt/downloads/complete` → `/mnt/downloads/complete`

### In Lidarr UI → Settings → Indexers → Add Prowlarr

- **Prowlarr Server**: `http://192.168.1.201:9696`
- **API Key**: (from Prowlarr Settings → General)
- Sync all indexers from Prowlarr

### MusicBrainz Metadata Profile

Lidarr should use the **Standard** metadata profile with:
- **MusicBrainz**: Enabled
- **AllMusic**: Enabled (for artist biographies)
- **Discogs**: Optional

This ensures the imported metadata matches the MusicBrainz IDs that Raido's
AI commentary system uses for enrichment.

---

## 6. Networking: Tailscale on the Gateway LXC

If you want to access Prowlarr/qBittorrent via Tailscale from outside:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --accept-routes

# The kill-switch nftables config above already allows tailscale0 interface
```

---

## 7. Verify Everything Works

```bash
# From inside Gateway LXC:
# Check VPN is active
ip route show table main | grep wg0

# Confirm all external traffic goes via Mullvad
curl https://am.i.mullvad.net/json | python3 -m json.tool

# Check Prowlarr is reachable from Raido LXC
curl http://192.168.1.201:9696/api/v1/system/status -H "X-Api-Key: <prowlarr_key>"

# Check bind-mounted downloads folder
ls /mnt/downloads/

# From Raido LXC (clean side):
curl http://lidarr:8686/api/v1/system/status -H "X-Api-Key: ${LIDARR_API_KEY}"
```

---

## Summary

| Service | LXC | IP | Port | VPN |
|---------|-----|----|------|-----|
| Lidarr | Raido (Docker) | internal / proxy | 8686 | No |
| Prowlarr | Gateway | 192.168.1.201 | 9696 | Yes (wg0) |
| qBittorrent | Gateway | 192.168.1.201 | 8080 | Yes (wg0) |
| Raido API | Raido (Docker) | internal | 8000 | No |

All torrent traffic is kill-switch protected. Lidarr on the clean side
communicates with the gateway only via LAN IPs (192.168.1.x), keeping
your clean subnet out of any VPN liability.

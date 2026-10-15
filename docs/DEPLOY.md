# Deploy

The game runs on one Oracle Cloud free-tier server at
`https://cards.parth.party`. The server can host more apps the same way.

## How the pieces fit

```
browser ──HTTPS──> Caddy (ports 80, 443) ──> card-game container (port 8000)
                     │
                     └──> any future app container
```

- **GitHub Actions** builds an ARM image on each push to `main` after the
  tests pass, and publishes it to `ghcr.io/parththakkar106/card-game`.
- **Docker** runs each app in its own container on the server.
- **Caddy** is the only container that listens on the internet. It gets free
  HTTPS certificates and forwards each subdomain to its app over the shared
  Docker network `web`.

## Server

| Setting | Value |
| --- | --- |
| Name | `main-server` |
| Shape | `VM.Standard.A1.Flex`, 2 OCPU, 12 GB |
| Image | Ubuntu 24.04 (`aarch64`) |
| Region | `ap-singapore-1`, AD-1 |
| Login | `ssh ubuntu@161.118.251.185` |

The tenancy quota policy caps A1 at the free amount. It needs both the
`standard-a1-*-count` and the `standard-a1-*-regional-count` lines, because
Oracle checks the regional names when you create an instance.

Folders on the server:

```
/srv/caddy/compose.yml      copy of deploy/caddy/compose.yml
/srv/caddy/Caddyfile        copy of deploy/caddy/Caddyfile
/srv/card-game/compose.yml  copy of deploy/compose.yml
```

## One-time server setup

1. Install Docker, and add `ubuntu` to the `docker` group.
2. Open ports 80 and 443 in the subnet's security list and in the server's
   `iptables` rules.
3. Create the shared network: `docker network create web`.
4. Start Caddy from `/srv/caddy`.
5. Point the DNS `A` record for `cards.parth.party` at the server's public IP.

## Deploy a new version

```bash
cd /srv/card-game
docker compose pull
docker compose up -d
```

`pull` downloads the newest image, and `up -d` replaces the running container.
Players in a game lose their room, because rooms live in memory.

## Add another app

1. Publish the app as a container image that listens on one port.
2. Create `/srv/<app>/compose.yml` that joins the external `web` network.
3. Add a block to `/srv/caddy/Caddyfile`, for example
   `blog.parth.party { reverse_proxy blog:3000 }`.
4. Add a DNS `A` record for the subdomain.
5. Run `docker compose up -d` in `/srv/<app>`, then
   `docker compose restart` in `/srv/caddy`.

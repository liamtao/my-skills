---
name: ben-a2b2-portal-https
description: "为 Ben 启动或维护本机 A2B2 Portal HTTPS 测试代理与 iPhone 证书安装入口。仅在明确要求 HTTPS 测试时使用；普通 Portal 启动沿用个人 ben-a2b2-start-dev。"
---

# Optional Portal HTTPS testing

Use this workflow only after the user explicitly requests HTTPS testing. Keep the ordinary Portal service and its configured backend; HTTPS is a local proxy in front of it.

## Inspect and start

1. Start or reuse the intended checkout's Portal on `3000` using the personal `.agents/skills/ben-a2b2-start-dev/SKILL.md` Portal-only route (which delegates to the team skill). Read `~/.config/a2b2/portal-https/start.sh` and `Caddyfile`. Inspect `3443` (HTTPS) and `3080` (certificate installation) with `lsof`, process arguments and ownership before starting anything. Reuse a healthy matching proxy; preserve unrelated listeners.
2. Discover the current LAN IPv4 and compare it with the Caddy site addresses, bind addresses, certificate SANs and installation-page links. Do not reuse a remembered IP. If the IP changed, update those local settings and reissue the server certificate with the existing CA in `~/.config/a2b2/portal-https/ca/`; keep that CA so the iPhone's existing trust remains valid. Restart only the matching HTTPS proxy when its configuration needs to change.
3. If the local setup is missing, prepare it within the authorized HTTPS request using `mkcert` and Caddy. Keep the CA and server keys outside the repository and public download directory. Configure TLS on `3443` to proxy `127.0.0.1:3000`, including WebSocket upgrades and streaming. Serve only the installation page and public root certificate/profile on `3080`. Preserve the Portal backend, HTTP port and normal startup commands.
4. Validate the actual configuration, then run the entry in a managed long-running terminal session when no matching proxy is running:

   ```sh
   caddy validate --config "$HOME/.config/a2b2/portal-https/Caddyfile" --adapter caddyfile
   "$HOME/.config/a2b2/portal-https/start.sh"
   ```

   Record the PID and session. Leave the services running; HTTPS remains an explicit option rather than a default startup dependency.

## iPhone trust

Deliver `http://<current-LAN-IPv4>:3080/` for installation and `https://<current-LAN-IPv4>:3443/` for Portal. The phone and Mac must be on the same LAN.

- Use Safari to download the **A2B2 Portal Local HTTPS** certificate profile from the installation page.
- In **Settings → General → VPN & Device Management**, install the profile.
- In **Settings → General → About → Certificate Trust Settings**, enable full trust for the matching local root. Read its current name from the certificate; do not assume a previous machine/IP label. Installation alone does not enable SSL trust. See [Apple's instructions](https://support.apple.com/en-us/102390).
- Open the HTTPS Portal in iPhone Chrome, sign in if needed, click Voice Input and allow microphone access. The user handles profile installation, trust and permission prompts. A new origin may require a fresh login; do not copy stored credentials between origins.

## Verify and report

- Verify the certificate chain and current IP with the local CA, without disabling TLS verification. Check the HTTPS page, API proxy and Vite WebSocket upgrade. Confirm the profile contains only the intended public root and private-key paths cannot be downloaded.
- Verify rendered behavior through the browser workflow. On a trusted origin, check `window.isSecureContext`, `MediaRecorder` and `navigator.mediaDevices.getUserMedia`; respect browser trust and permission prompts.
- Report the HTTPS and installation links, proxy/session state and any remaining iPhone trust or microphone verification. TLS/HTTP checks on the Mac do not prove real iPhone authorization or recording. Update the environment record without storing private keys or credentials.

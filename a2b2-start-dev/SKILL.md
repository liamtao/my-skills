---
name: a2b2-start-dev
description: "历史参考副本，不作为 Ben 本机启动入口；当前入口见项目 ben-a2b2-start-dev，团队规范以仓库 a2b2-start-dev 为准。"
---

# Archived local copy

For current Ben-local startup, read the project’s `.agents/skills/ben-a2b2-start-dev/SKILL.md` and use `/Users/ben/.config/a2b2/dev-tools/dev` for combined startup. The remaining text is historical reference; current team rules live in the checkout’s `.agents/skills/a2b2-start-dev/SKILL.md`.

# Start A2B2 development

Prepare the requested local surfaces and leave them running for development. Use the existing A2B2 checkout and backend configuration.

## Choose the target

| User request | Start or reuse |
| --- | --- |
| `ios`, `iOS 模拟器`, `mobile` | iOS Simulator, A2B2 native app, and Metro |
| `portal`, `Portal 服务`, `web` | Portal only |
| Explicit `Portal HTTPS` / `开启 HTTPS 测试` | Portal plus the optional HTTPS proxy |
| `启动官网`, `官网`, `marketing` | Marketing only |
| Multiple named targets | Only the requested targets |
| No target specified | iOS Simulator, A2B2 native app, Metro, and Portal |

An explicit narrower request takes precedence, such as Metro only. Do not start the other surface for a single-target request. Existing unrelated services can remain running.

Portal uses HTTP by default. Start HTTPS only when the user explicitly requests HTTPS testing; ordinary Portal startup, LAN access, or Voice Input testing alone does not enable it. Without that request, leave any existing HTTPS listener unchanged and skip HTTPS setup and startup.

## Check the environment

- Use the current A2B2 Git checkout. Outside it, locate the user-selected A2B2 checkout; ask if the intended checkout is ambiguous. Confirm Git root, branch, and working-tree state, then read root and selected app `AGENTS.md` files.
- Inspect selected ports before starting: Portal `3000`, Marketing `3001`, Metro `8081`. Use `lsof -nP -iTCP:<port> -sTCP:LISTEN`, process arguments, and `lsof -a -p <pid> -d cwd` to identify checkout and owner. Reuse a healthy service from the intended checkout. A port responding alone does not establish the correct checkout.
- Preserve existing listeners. If another checkout owns the required port, report the conflict and ask only for the needed restart or alternate environment decision. Do not kill it or silently choose another Portal port.
- Read only relevant public API/environment settings from each selected app's ignored `.env.local`; retain the configured backend. Do not print whole environment files or change SIT/local/prod targets to make startup succeed. Starting these clients does not require starting a local backend when their existing API URL is remote.
- If dependencies are missing, install from the root using the existing lockfile, for example `pnpm install --frozen-lockfile --filter portal`, `--filter marketing`, or `--filter mobile...`. Do not upgrade packages or regenerate the lockfile for startup.

Use managed long-running terminal sessions for new services. Keep their session IDs and PIDs for later diagnosis. Do not stop them when this startup task finishes.

## Portal

Run from `apps/portal` when no suitable service exists:

```sh
pnpm dev --host 0.0.0.0
```

Portal defaults to LAN listening (`0.0.0.0:3000`). Keep **`http://localhost:3000/`** for Mac navigation and deliver `http://<current-LAN-IPv4>:3000/` for phones on the same LAN. Discover the active interface/address rather than storing a fixed IP. Ben’s migrated local entry and Alfred’s “A2B2 开发环境” workflow use this default; `A2B2_DEV_HOST=localhost /Users/ben/.config/a2b2/dev-tools/dev` opts into loopback only. A healthy loopback-only listener is not LAN-ready. When LAN is requested, check the process owner before restarting the intended checkout’s managed Portal, preserving other services where possible.

Vite dev mode proxies `/api/`, `/connect/v1/`, and the configured `/agent-service/` upstreams through the frontend origin. It retains the selected `.env.local` backend (AWS SIT is `https://api-sit.a2b2.ai`) and removes the browser Origin on the server-to-server hop. Release builds retain their configured public API URLs. No remote CORS change is needed. The dev-only UUID compatibility shim uses `crypto.getRandomValues` for HTTP LAN browsers.

Verify the rendered page and authenticated reads from the LAN origin; an HTTP 200 from Vite alone is insufficient. When login verification is requested, test email/password login with authorized credentials, or state that only an existing session was verified. Report whether testing used a real phone or a desktop browser at the LAN origin. OAuth callbacks still use the backend’s configured frontend URL. HTTP LAN access does not enable microphone/PWA secure-context features; those require trusted HTTPS.

- Wait for Vite Ready and confirm the local page responds. Open or reuse the correct localhost browser tab and check that login or an authenticated page renders. Respect browser permission denials; do not switch tools to bypass them.
- If startup after dependency installation produces an invalid React hook error, inspect React resolution and Vite logs. When stale dependency optimization is confirmed, restart only this task's Vite with `pnpm dev --host 0.0.0.0 --force` and recheck rendering.
- For API connection errors, compare the actual browser origin with the backend's CORS response using a credential-free OPTIONS request to the affected endpoint. Do not alter remote CORS configuration as part of starting the environment.
- Leave account login to the user unless they ask to log in. Never store credentials in this skill or environment records.

### Optional Portal HTTPS

Only for an explicit HTTPS testing request, follow [Portal HTTPS startup](references/portal-https.md). The local entry is `~/.config/a2b2/portal-https/start.sh`; it runs a Caddy TLS proxy to the existing Portal on `3000` and a separate iPhone certificate-installation page. Read and validate its configuration before running it. This entry is separate from normal Portal startup and Alfred's default workflow.

## Marketing (官网)

Run from `apps/marketing` when no suitable service exists:

```sh
pnpm dev
```

The package's `dev` script starts Next.js on port `3001`. Use **`http://localhost:3001/`** for browser navigation and the delivered link.

- Retain existing local environment settings. Next.js reads `.env.local`; tracked `.env.green-sit` and `.env.prod` are AWS artifact-build inputs, not files to source for routine local startup.
- Wait for Next.js Ready and confirm the homepage returns HTTP 200. Open or reuse the localhost browser tab and check that the homepage renders. Respect browser permission denials and report any unverified rendering.
- A Marketing-only request starts this service only. Leave existing Portal and Metro services running.

## iOS and Metro

Run from `apps/mobile` when no suitable Metro exists:

```sh
pnpm start --localhost --port 8081
```

Wait for Metro to listen and confirm `http://localhost:8081/status` returns `packager-status:running`.

1. Discover devices with `xcrun simctl list devices available`. Reuse the intended booted iPhone. Otherwise select an available iPhone, boot its returned UDID, and wait for `xcrun simctl bootstatus <udid> -b`. Never hardcode a past UDID.
2. Show its native simulator window. Discover the installed host: newer Xcode uses **Device Hub** (`com.apple.dt.Devices`); other versions use Simulator (`com.apple.iphonesimulator`). Use the available native app tools or installed application path rather than assuming `/Applications/Xcode.app/Contents/Developer/Applications/Simulator.app` exists.
3. Read the current Mobile app configuration for its bundle ID, then use `xcrun simctl get_app_container <udid> <bundle-id> app` and `xcrun simctl launch <udid> <bundle-id>` to reuse the installed development app. Preserve its data and login state.
4. If no matching app is installed, or an identified new native module requires rebuilding, follow the current Mobile native-build guidance. The package's `ios` script uses Expo `run:ios`; select the intended device and reuse the running Metro with `--no-bundler`. Inspect existing ignored iOS signing and bundle identifiers before building, and preserve any physical-device setup. Do not run prebuild, rewrite signing, or reinstall merely because a reusable app exists.
5. For an app started before Metro was ready that shows “No script URL provided”, relaunch that app once after Metro is healthy. Do not clear app data or repeatedly rebuild for this error.
6. As the final iOS startup check, always attempt Maestro MCP connectivity after the simulator, native app and Metro are ready, including when reusing an existing environment. Call `list_devices`, select the intended simulator from its returned IDs, then call `inspect_screen`. A discovered device or `connected: true` alone is not sufficient: successful screen inspection establishes connectivity. Use Maestro screenshots when needed to verify native rendering. A JavaScript export alone does not prove the app loaded. Skip this check for Portal-only or Metro-only requests.

### Maestro connection failure

- Proactively tell the user if device discovery or screen inspection fails, or Maestro MCP tools are unavailable. Report the failing step and relevant error, and separate simulator/app readiness from failed Maestro verification. Do not silently skip the check or present it as passed.
- Give repair steps matched to the current failure. If the intended device is missing or not booted, ask the user to confirm the intended simulator is open and booted, then rerun device discovery. If MCP tools are unavailable, guide the user to enable or reconnect the Maestro MCP server in their client. For `Device became unreachable during deviceInfo` or a driver connection timeout, suggest reconnecting Maestro MCP, then retry `list_devices` and `inspect_screen` against the current device. If it still fails, use the current Maestro iOS runner logs to guide further diagnosis; do not assume OS incompatibility from this error alone.
- Follow the device verification policy in the selected checkout's `apps/mobile/AGENTS.md`, including its Computer Use (CUA) fallback rule. Preserve the existing environment while awaiting the user's choice.

## Completion

Report each requested surface separately: ready, reused, or blocked, with Portal's localhost and current LAN links or Marketing's localhost link and iOS device/Metro port. For iOS, include the Maestro MCP connectivity result (`PASS`, `FAIL`, or `BLOCKED`); on failure, include the error and suggested repair steps. Distinguish listener/HTTP readiness, native bundle loading, visible rendering, and authenticated verification. Report missing verification honestly; one blocked surface does not prevent preparing the other requested surface.

When claude-mem work-state tools are available, update the relevant environment record with checkout, branch, backend, URL/device, PID/session, and verification. Never record credentials. Leave services running and existing source changes intact.

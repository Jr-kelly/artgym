# Wuji video observation room

Static, dependency-free Chinese video gallery. Run `python3 -m http.server 8765 --directory docs/wuji-demo` from the repository root, or open index.html directly. Public deployment uses the isolated `wuji-demo-site` branch at its root with GitHub Pages.

The four original MP4 files are copied without transcoding; SHA256, duration and dimensions are in media-manifest.json. JPEG previews use frame 60. Source3/source11/shared come from the hold release; original comes from the multigrasp release. Labels distinguish actual representative outcomes and frozen aggregate results. No training or physics runs are started by this site.

Browser verification: Chromium desktop 1440px and mobile 390px; all four videos decode and play, switching updates labels, speed/loop/replay work, scene deep links work, no mobile horizontal overflow or JavaScript errors.

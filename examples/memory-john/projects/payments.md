# Payments project

- Payments and website share a 2026-10-15 launch deadline [source: https://example.com/sessions/102; added: 2026-09-03]
- Median request is 80 ms; the slowest 1% take 2.4 s [source: https://example.com/sessions/300; added: 2026-09-25]
- Cause found: the price cache refresh rebuilds a 2 GB table every 10 seconds, triggering a 400 ms GC freeze [source: https://example.com/sessions/301; added: 2026-10-01]
- Fix shipped: refresh only changed prices; p99 dropped to 310 ms [source: https://example.com/sessions/304; added: 2026-10-02]

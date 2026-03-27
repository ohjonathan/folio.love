---
id: tier2_platform_model_comparison_session_log
type: atom
status: complete
ontos_schema: 2.2
curation_level: 0
label: tier2_platform_model_comparison
created: 2026-03-27
---

# Tier 2 Platform Model Comparison Session Log

This canonical copy preserves the staged run chronology while sanitizing raw
source titles and machine-specific paths. Commands, timestamps, exit codes,
elapsed times, retries, and failure classes are preserved.

---

[2026-03-22 08:24:13] 

# Execution Run: both
[2026-03-22 08:24:13] Started: 2026-03-22T08:24:13.835725
[2026-03-22 08:24:13] Profiles: 15
[2026-03-22 08:24:13] Source files: 16
[2026-03-22 08:24:13] 
--- FULL CORPUS ---
[2026-03-22 08:24:13] 
============================================================
[2026-03-22 08:24:13] PROFILE: anthropic_opus4
[2026-03-22 08:24:13] ============================================================
[2026-03-22 08:24:13]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_opus4
[2026-03-22 08:27:41]   SUCCESS: exit=0 elapsed=207.7s
[2026-03-22 08:27:41]   CMD: folio convert SRC_02.pdf --llm-profile anthropic_opus4
[2026-03-22 08:37:41]   TIMEOUT after 600.1s
[2026-03-22 08:37:41]   CMD: folio convert SRC_03.pdf --llm-profile anthropic_opus4
[2026-03-22 08:42:15] 

# Execution Run: both
[2026-03-22 08:42:15] Started: 2026-03-22T08:42:15.798634
[2026-03-22 08:42:15] Profiles: 15
[2026-03-22 08:42:15] Source files: 16
[2026-03-22 08:42:15] 
--- FULL CORPUS ---
[2026-03-22 08:42:15] 
============================================================
[2026-03-22 08:42:15] PROFILE: anthropic_opus4
[2026-03-22 08:42:15] ============================================================
[2026-03-22 08:42:15]   SKIP: already converted (<cached output>)
[2026-03-22 08:42:15]   CMD: folio convert SRC_02.pdf --llm-profile anthropic_opus4
[2026-03-22 08:47:41]   TIMEOUT after 600.0s
[2026-03-22 08:47:41]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_opus4
[2026-03-22 08:53:46]   SUCCESS: exit=0 elapsed=691.0s
[2026-03-22 08:53:46]   CMD: folio convert SRC_03.pdf --llm-profile anthropic_opus4
[2026-03-22 08:54:07]   SUCCESS: exit=0 elapsed=385.4s
[2026-03-22 08:54:07]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_opus4
[2026-03-22 08:56:46]   SUCCESS: exit=0 elapsed=159.9s
[2026-03-22 08:56:46]   CMD: folio convert SRC_06.pdf --llm-profile anthropic_opus4
[2026-03-22 08:58:00]   SUCCESS: exit=0 elapsed=73.4s
[2026-03-22 08:58:00]   CMD: folio convert SRC_07.pdf --llm-profile anthropic_opus4
[2026-03-22 09:20:47]   SUCCESS: exit=0 elapsed=1367.3s
[2026-03-22 09:20:47]   CMD: folio convert SRC_08.pdf --llm-profile anthropic_opus4
[2026-03-22 09:27:08]   SUCCESS: exit=0 elapsed=380.4s
[2026-03-22 09:27:08]   CMD: folio convert SRC_09.pdf --llm-profile anthropic_opus4
[2026-03-22 09:31:04]   SUCCESS: exit=0 elapsed=236.4s
[2026-03-22 09:31:04]   CMD: folio convert SRC_10.pdf --llm-profile anthropic_opus4
[2026-03-22 09:36:01]   SUCCESS: exit=0 elapsed=296.7s
[2026-03-22 09:36:01]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_opus4
[2026-03-22 09:37:15]   SUCCESS: exit=0 elapsed=74.0s
[2026-03-22 09:37:15]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 09:40:55]   TIMEOUT after 2828.7s
[2026-03-22 09:40:55]   SKIP: already converted (<cached output>)
[2026-03-22 09:40:55]   SKIP: already converted (<cached output>)
[2026-03-22 09:40:55]   SKIP: already converted (<cached output>)
[2026-03-22 09:40:55]   SKIP: already converted (<cached output>)
[2026-03-22 09:40:55]   SKIP: already converted (<cached output>)
[2026-03-22 09:40:55]   SKIP: already converted (<cached output>)
[2026-03-22 09:40:55]   SKIP: already converted (<cached output>)
[2026-03-22 09:40:55]   SKIP: already converted (<cached output>)
[2026-03-22 09:40:55]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 09:47:15]   TIMEOUT after 600.0s
[2026-03-22 09:47:15]   CMD: folio convert SRC_13.pdf --llm-profile anthropic_opus4
[2026-03-22 09:53:43]   SUCCESS: exit=0 elapsed=388.7s
[2026-03-22 09:53:43]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_opus4
[2026-03-22 09:57:56]   SUCCESS: exit=0 elapsed=1021.2s
[2026-03-22 09:57:56]   SKIP: already converted (<cached output>)
[2026-03-22 09:57:56]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_opus4
[2026-03-22 10:03:43]   TIMEOUT after 600.0s
[2026-03-22 10:03:43]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_opus4
[2026-03-22 10:06:35]   SUCCESS: exit=0 elapsed=171.5s
[2026-03-22 10:06:35]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_opus4
[2026-03-22 10:16:08]   SUCCESS: exit=0 elapsed=572.9s
[2026-03-22 10:16:08]   SUMMARY: 12 success, 4 failed, 6714s total
[2026-03-22 10:16:08] 
============================================================
[2026-03-22 10:16:08] PROFILE: anthropic_sonnet4
[2026-03-22 10:16:08] ============================================================
[2026-03-22 10:16:08]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:16:09]   SUCCESS: exit=0 elapsed=1092.8s
[2026-03-22 10:16:09]   SKIP: already converted (<cached output>)
[2026-03-22 10:16:09]   SKIP: already converted (<cached output>)
[2026-03-22 10:16:09]   SUMMARY: 3 success, 13 failed, 5634s total
[2026-03-22 10:16:09] 
============================================================
[2026-03-22 10:16:09] PROFILE: anthropic_sonnet4
[2026-03-22 10:16:09] ============================================================
[2026-03-22 10:16:09]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:16:09]   ERROR: exit=1 elapsed=1.7s
[2026-03-22 10:16:09]   STDERR:  failed: Per-page rendering failed: [Errno 17] File exists: '<workspace>/validation/runs/anthropic_sonnet4/SRC_01/.slides_tmp'

[2026-03-22 10:16:09]   CMD: folio convert SRC_02.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:16:10]   ERROR: exit=1 elapsed=0.9s
[2026-03-22 10:16:10]   STDERR:  failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/anthropic_sonnet4/SRC_01/.slides_tmp/slide-005.png'

[2026-03-22 10:16:10]   CMD: folio convert SRC_02.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:16:26]   ERROR: exit=1 elapsed=16.1s
[2026-03-22 10:16:26]   STDERR:  failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/anthropic_sonnet4/SRC_02/.slides_tmp/slide-005.png'

[2026-03-22 10:16:26]   CMD: folio convert SRC_03.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:19:29]   ERROR: exit=-15 elapsed=199.9s
[2026-03-22 10:19:29]   STDERR: 9ac4-a74c-48de-b6aa-cfbc4cc7ac9d/v1/messages "HTTP/1.1 200 OK"
HTTP Request: POST https://anthropic.prod.ai-gateway.quantumblack.com/9d2b9ac4-a74c-48de-b6aa-cfbc4cc7ac9d/v1/messages "HTTP/1.1 200 OK"

[2026-03-22 10:19:29]   ERROR: exit=-15 elapsed=183.1s
[2026-03-22 10:19:29]   STDERR: ai-gateway.quantumblack.com/9d2b9ac4-a74c-48de-b6aa-cfbc4cc7ac9d/v1/messages "HTTP/1.1 200 OK"
Analyzing slide 12/20...
Image slide-012.png resized from 4800x2700 to 4096x2304 for provider submission

[2026-03-22 10:19:29]   CMD: folio convert SRC_03.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:19:29]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:20:04] 

# Execution Run: both
[2026-03-22 10:20:04] Started: 2026-03-22T10:20:04.807771
[2026-03-22 10:20:04] Profiles: 15
[2026-03-22 10:20:04] Source files: 16
[2026-03-22 10:20:04] 
--- FULL CORPUS ---
[2026-03-22 10:20:04] 
============================================================
[2026-03-22 10:20:04] PROFILE: anthropic_opus4
[2026-03-22 10:20:04] ============================================================
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SKIP: already converted (<cached output>)
[2026-03-22 10:20:04]   SUMMARY: 0 success, 16 failed, 0s total
[2026-03-22 10:20:04] 
============================================================
[2026-03-22 10:20:04] PROFILE: anthropic_sonnet4
[2026-03-22 10:20:04] ============================================================
[2026-03-22 10:20:04]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:21:29]   SUCCESS: exit=0 elapsed=85.0s
[2026-03-22 10:21:29]   SKIP: already converted (<cached output>)
[2026-03-22 10:21:29]   SKIP: already converted (<cached output>)
[2026-03-22 10:21:29]   SKIP: already converted (<cached output>)
[2026-03-22 10:21:29]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:22:20]   SUCCESS: exit=0 elapsed=51.1s
[2026-03-22 10:22:20]   CMD: folio convert SRC_06.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:22:55]   SUCCESS: exit=0 elapsed=205.8s
[2026-03-22 10:22:55]   SKIP: already converted (<cached output>)
[2026-03-22 10:22:55]   CMD: folio convert SRC_06.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:23:04]   SUCCESS: exit=0 elapsed=43.9s
[2026-03-22 10:23:04]   CMD: folio convert SRC_07.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:23:40]   SUCCESS: exit=0 elapsed=45.3s
[2026-03-22 10:23:40]   CMD: folio convert SRC_07.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:25:03]   SUCCESS: exit=0 elapsed=119.0s
[2026-03-22 10:25:03]   CMD: folio convert SRC_08.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:25:56]   SUCCESS: exit=0 elapsed=135.6s
[2026-03-22 10:25:56]   CMD: folio convert SRC_08.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:26:23]   SUCCESS: exit=0 elapsed=79.4s
[2026-03-22 10:26:23]   CMD: folio convert SRC_09.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:27:17]   SUCCESS: exit=0 elapsed=54.1s
[2026-03-22 10:27:17]   CMD: folio convert SRC_10.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:28:34]   SUCCESS: exit=0 elapsed=158.3s
[2026-03-22 10:28:34]   SKIP: already converted (<cached output>)
[2026-03-22 10:28:34]   CMD: folio convert SRC_10.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:28:38]   SUCCESS: exit=0 elapsed=81.3s
[2026-03-22 10:28:38]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 10:29:29]   SUCCESS: exit=0 elapsed=50.6s
[2026-03-22 10:29:29]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:29:29]   TIMEOUT after 600.0s
[2026-03-22 10:29:29]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:30:28]   SUCCESS: exit=0 elapsed=113.6s
[2026-03-22 10:30:28]   SKIP: already converted (<cached output>)
[2026-03-22 10:30:28]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:32:52]   SUCCESS: exit=0 elapsed=203.1s
[2026-03-22 10:32:52]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:34:09]   SUCCESS: exit=0 elapsed=76.4s
[2026-03-22 10:34:09]   CMD: folio convert SRC_06.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:34:58]   SUCCESS: exit=0 elapsed=48.8s
[2026-03-22 10:34:58]   CMD: folio convert SRC_07.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:36:56]   SUCCESS: exit=0 elapsed=118.6s
[2026-03-22 10:36:56]   CMD: folio convert SRC_08.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:38:19]   SUCCESS: exit=0 elapsed=83.3s
[2026-03-22 10:38:19]   CMD: folio convert SRC_09.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:39:12]   SUCCESS: exit=0 elapsed=52.7s
[2026-03-22 10:39:12]   CMD: folio convert SRC_10.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:40:13]   SUCCESS: exit=0 elapsed=60.4s
[2026-03-22 10:40:13]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 10:41:12]   SUCCESS: exit=0 elapsed=59.3s
[2026-03-22 10:41:12]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:44:10]   SUCCESS: exit=0 elapsed=881.6s
[2026-03-22 10:44:10]   CMD: folio convert SRC_13.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:45:51]   SUCCESS: exit=0 elapsed=922.7s
[2026-03-22 10:45:51]   CMD: folio convert SRC_13.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:49:16]   SUCCESS: exit=0 elapsed=305.2s
[2026-03-22 10:49:16]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_sonnet4
[2026-03-22 10:51:04]   SUCCESS: exit=0 elapsed=313.6s
[2026-03-22 10:51:04]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_sonnet4
[2026-03-22 10:51:12]   TIMEOUT after 600.0s
[2026-03-22 10:51:12]   CMD: folio convert SRC_13.pdf --llm-profile anthropic_sonnet4
[2026-03-22 10:56:19]   SUCCESS: exit=0 elapsed=307.1s
[2026-03-22 10:56:19]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_sonnet4
[2026-03-22 10:59:58]   SUCCESS: exit=0 elapsed=642.6s
[2026-03-22 10:59:58]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_sonnet4
[2026-03-22 11:01:41]   SUCCESS: exit=0 elapsed=636.3s
[2026-03-22 11:01:41]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_sonnet4
[2026-03-22 11:02:36]   SUCCESS: exit=0 elapsed=157.8s
[2026-03-22 11:02:36]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 11:04:12]   SUCCESS: exit=0 elapsed=151.9s
[2026-03-22 11:04:12]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 11:05:32]   SUCCESS: exit=0 elapsed=176.1s
[2026-03-22 11:05:32]   SUMMARY: 13 success, 3 failed, 2728s total
[2026-03-22 11:05:32] 
============================================================
[2026-03-22 11:05:32] PROFILE: anthropic_haiku45
[2026-03-22 11:05:32] ============================================================
[2026-03-22 11:05:32]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:06:19]   TIMEOUT after 600.0s
[2026-03-22 11:06:19]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_sonnet4
[2026-03-22 11:06:25]   SUCCESS: exit=0 elapsed=52.9s
[2026-03-22 11:06:25]   CMD: folio convert SRC_02.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:08:10]   SUCCESS: exit=0 elapsed=238.1s
[2026-03-22 11:08:10]   SUMMARY: 10 success, 6 failed, 3121s total
[2026-03-22 11:08:10] 
============================================================
[2026-03-22 11:08:10] PROFILE: anthropic_haiku45
[2026-03-22 11:08:10] ============================================================
[2026-03-22 11:08:10]   SKIP: already converted (<cached output>)
[2026-03-22 11:08:10]   CMD: folio convert SRC_02.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:08:49]   SUCCESS: exit=0 elapsed=149.7s
[2026-03-22 11:08:49]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 11:12:48]   SUCCESS: exit=0 elapsed=239.7s
[2026-03-22 11:12:48]   SUMMARY: 11 success, 5 failed, 3401s total
[2026-03-22 11:12:48] 
============================================================
[2026-03-22 11:12:48] PROFILE: anthropic_haiku45
[2026-03-22 11:12:48] ============================================================
[2026-03-22 11:12:48]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:13:38]   SUCCESS: exit=0 elapsed=50.0s
[2026-03-22 11:13:38]   CMD: folio convert SRC_02.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:14:25]   SUCCESS: exit=0 elapsed=374.3s
[2026-03-22 11:14:25]   CMD: folio convert SRC_03.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:14:36]   SUCCESS: exit=0 elapsed=490.6s
[2026-03-22 11:14:36]   CMD: folio convert SRC_03.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:15:17]   ERROR: exit=1 elapsed=41.5s
[2026-03-22 11:15:17]   STDERR:  failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/anthropic_haiku45/SRC_03/.slides_tmp/slide-001.png'

[2026-03-22 11:15:17]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:17:30]   SUCCESS: exit=0 elapsed=133.2s
[2026-03-22 11:17:30]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:18:26]   SUCCESS: exit=0 elapsed=55.4s
[2026-03-22 11:18:26]   CMD: folio convert SRC_06.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:19:28]   SUCCESS: exit=0 elapsed=349.7s
[2026-03-22 11:19:28]   CMD: folio convert SRC_03.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:19:28]   SUCCESS: exit=0 elapsed=62.5s
[2026-03-22 11:19:28]   CMD: folio convert SRC_07.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:20:51]   SUCCESS: exit=0 elapsed=82.4s
[2026-03-22 11:20:51]   CMD: folio convert SRC_08.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:22:49]   SUCCESS: exit=0 elapsed=117.9s
[2026-03-22 11:22:49]   CMD: folio convert SRC_09.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:24:16]   SUCCESS: exit=0 elapsed=87.6s
[2026-03-22 11:24:16]   CMD: folio convert SRC_10.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:26:29]   SUCCESS: exit=0 elapsed=132.9s
[2026-03-22 11:26:29]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 11:27:00]   SUCCESS: exit=0 elapsed=31.2s
[2026-03-22 11:27:00]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:29:24]   SUCCESS: exit=0 elapsed=899.2s
[2026-03-22 11:29:24]   SKIP: already converted (<cached output>)
[2026-03-22 11:29:24]   SKIP: already converted (<cached output>)
[2026-03-22 11:29:24]   SKIP: already converted (<cached output>)
[2026-03-22 11:29:24]   SKIP: already converted (<cached output>)
[2026-03-22 11:29:24]   SKIP: already converted (<cached output>)
[2026-03-22 11:29:24]   SKIP: already converted (<cached output>)
[2026-03-22 11:29:24]   SKIP: already converted (<cached output>)
[2026-03-22 11:29:24]   SKIP: already converted (<cached output>)
[2026-03-22 11:29:24]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:29:28]   TIMEOUT after 600.0s
[2026-03-22 11:29:28]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:31:48]   SUCCESS: exit=0 elapsed=139.5s
[2026-03-22 11:31:48]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:32:52]   SUCCESS: exit=0 elapsed=64.5s
[2026-03-22 11:32:52]   CMD: folio convert SRC_06.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:33:48]   SUCCESS: exit=0 elapsed=56.2s
[2026-03-22 11:33:48]   CMD: folio convert SRC_07.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:35:13]   SUCCESS: exit=0 elapsed=84.5s
[2026-03-22 11:35:13]   CMD: folio convert SRC_08.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:37:04]   SUCCESS: exit=0 elapsed=110.9s
[2026-03-22 11:37:04]   CMD: folio convert SRC_09.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:38:34]   SUCCESS: exit=0 elapsed=90.8s
[2026-03-22 11:38:34]   CMD: folio convert SRC_10.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:39:26]   SUCCESS: exit=0 elapsed=745.6s
[2026-03-22 11:39:26]   CMD: folio convert SRC_13.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:40:30]   SUCCESS: exit=0 elapsed=666.3s
[2026-03-22 11:40:30]   CMD: folio convert SRC_13.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:40:54]   SUCCESS: exit=0 elapsed=139.1s
[2026-03-22 11:40:54]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 11:41:27]   SUCCESS: exit=0 elapsed=33.1s
[2026-03-22 11:41:27]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:42:57]   SUCCESS: exit=0 elapsed=210.9s
[2026-03-22 11:42:57]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_haiku45
[2026-03-22 11:44:09]   SUCCESS: exit=0 elapsed=218.6s
[2026-03-22 11:44:09]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_haiku45
[2026-03-22 11:49:38]   SUCCESS: exit=0 elapsed=401.0s
[2026-03-22 11:49:38]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:50:57]   SUCCESS: exit=0 elapsed=408.2s
[2026-03-22 11:50:57]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:51:17]   SUCCESS: exit=0 elapsed=98.9s
[2026-03-22 11:51:17]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 11:51:27]   TIMEOUT after 600.0s
[2026-03-22 11:51:27]   CMD: folio convert SRC_13.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:52:37]   SUCCESS: exit=0 elapsed=99.5s
[2026-03-22 11:52:37]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 11:52:38]   ERROR: exit=1 elapsed=0.9s
[2026-03-22 11:52:38]   STDERR: t an error: The object you are trying to access does not exist (-1728)

If this file consistently fails, export it to PDF manually (File → Export → PDF, slides only) and run: folio convert <deck>.pdf

[2026-03-22 11:52:38]   SUMMARY: 6 success, 10 failed, 2667s total
[2026-03-22 11:52:38] 
============================================================
[2026-03-22 11:52:38] PROFILE: anthropic_haiku3
[2026-03-22 11:52:38] ============================================================
[2026-03-22 11:52:38]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:52:58]   SUCCESS: exit=0 elapsed=20.1s
[2026-03-22 11:52:58]   CMD: folio convert SRC_02.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:53:25]   SUCCESS: exit=0 elapsed=128.8s
[2026-03-22 11:53:25]   SUMMARY: 15 success, 1 failed, 2873s total
[2026-03-22 11:53:25] 
============================================================
[2026-03-22 11:53:25] PROFILE: anthropic_haiku3
[2026-03-22 11:53:25] ============================================================
[2026-03-22 11:53:25]   SKIP: already converted (<cached output>)
[2026-03-22 11:53:25]   SKIP: already converted (<cached output>)
[2026-03-22 11:53:25]   CMD: folio convert SRC_03.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:53:52]   SUCCESS: exit=0 elapsed=54.5s
[2026-03-22 11:53:52]   CMD: folio convert SRC_03.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:54:51]   SUCCESS: exit=0 elapsed=203.8s
[2026-03-22 11:54:51]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_haiku45
[2026-03-22 11:55:53]   SUCCESS: exit=0 elapsed=148.0s
[2026-03-22 11:55:53]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:02]   SUCCESS: exit=0 elapsed=8.9s
[2026-03-22 11:56:02]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:04]   ERROR: exit=1 elapsed=73.8s
[2026-03-22 11:56:04]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 11:56:04]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku45
[2026-03-22 11:56:08]   SUCCESS: exit=0 elapsed=5.4s
[2026-03-22 11:56:08]   CMD: folio convert SRC_06.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:13]   SUCCESS: exit=0 elapsed=5.1s
[2026-03-22 11:56:13]   CMD: folio convert SRC_07.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:17]   SUCCESS: exit=0 elapsed=144.8s
[2026-03-22 11:56:17]   SKIP: already converted (<cached output>)
[2026-03-22 11:56:17]   SKIP: already converted (<cached output>)
[2026-03-22 11:56:17]   SKIP: already converted (<cached output>)
[2026-03-22 11:56:17]   CMD: folio convert SRC_07.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:20]   SUCCESS: exit=0 elapsed=6.8s
[2026-03-22 11:56:20]   CMD: folio convert SRC_08.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:24]   SUCCESS: exit=0 elapsed=7.0s
[2026-03-22 11:56:24]   CMD: folio convert SRC_08.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:25]   SUCCESS: exit=0 elapsed=5.2s
[2026-03-22 11:56:25]   CMD: folio convert SRC_09.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:30]   SUCCESS: exit=0 elapsed=5.8s
[2026-03-22 11:56:30]   CMD: folio convert SRC_09.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:32]   SUCCESS: exit=0 elapsed=7.1s
[2026-03-22 11:56:32]   CMD: folio convert SRC_10.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:36]   SUCCESS: exit=0 elapsed=6.3s
[2026-03-22 11:56:36]   CMD: folio convert SRC_10.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:56:41]   SUCCESS: exit=0 elapsed=8.7s
[2026-03-22 11:56:41]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 11:56:43]   SUCCESS: exit=0 elapsed=6.7s
[2026-03-22 11:56:43]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 11:57:40]   SUCCESS: exit=0 elapsed=96.1s
[2026-03-22 11:57:40]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 11:57:42]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 11:57:42]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 11:57:42]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:57:44]   ERROR: exit=1 elapsed=61.4s
[2026-03-22 11:57:44]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 11:57:44]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:58:04]   ERROR: exit=1 elapsed=20.0s
[2026-03-22 11:58:04]   STDERR: g failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/anthropic_haiku3/SRC_12/.slides_tmp/slide-027.png'

[2026-03-22 11:58:04]   CMD: folio convert SRC_13.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:58:42]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 11:58:42]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 11:58:42]   SUMMARY: 12 success, 4 failed, 2754s total
[2026-03-22 11:58:42] 
============================================================
[2026-03-22 11:58:42] PROFILE: anthropic_haiku3
[2026-03-22 11:58:42] ============================================================
[2026-03-22 11:58:42]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:59:04]   SUCCESS: exit=0 elapsed=21.5s
[2026-03-22 11:59:04]   CMD: folio convert SRC_02.pdf --llm-profile anthropic_haiku3
[2026-03-22 11:59:36]   SUCCESS: exit=0 elapsed=91.6s
[2026-03-22 11:59:36]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_haiku3
[2026-03-22 11:59:56]   SUCCESS: exit=0 elapsed=51.9s
[2026-03-22 11:59:56]   CMD: folio convert SRC_03.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:00:17]   SUCCESS: exit=0 elapsed=154.4s
[2026-03-22 12:00:17]   SKIP: already converted (<cached output>)
[2026-03-22 12:00:17]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_haiku3
[2026-03-22 12:00:49]   ERROR: exit=1 elapsed=73.9s
[2026-03-22 12:00:49]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 12:00:49]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:01:30]   ERROR: exit=1 elapsed=73.5s
[2026-03-22 12:01:30]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 12:01:30]   SKIP: already converted (<cached output>)
[2026-03-22 12:01:30]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 12:01:51]   SUCCESS: exit=0 elapsed=61.1s
[2026-03-22 12:01:51]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 12:02:27]   SUCCESS: exit=0 elapsed=151.6s
[2026-03-22 12:02:27]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:02:32]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 12:02:32]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 12:02:32]   SUMMARY: 9 success, 7 failed, 546s total
[2026-03-22 12:02:32] 
============================================================
[2026-03-22 12:02:32] PROFILE: openai_gpt53
[2026-03-22 12:02:32] ============================================================
[2026-03-22 12:02:32]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 12:02:36]   SUCCESS: exit=0 elapsed=9.2s
[2026-03-22 12:02:36]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:02:42]   SUCCESS: exit=0 elapsed=5.2s
[2026-03-22 12:02:42]   CMD: folio convert SRC_06.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:02:48]   SUCCESS: exit=0 elapsed=6.1s
[2026-03-22 12:02:48]   CMD: folio convert SRC_07.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:02:52]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 12:02:52]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 12:02:52]   SUMMARY: 9 success, 7 failed, 615s total
[2026-03-22 12:02:52] 
============================================================
[2026-03-22 12:02:52] PROFILE: openai_gpt53
[2026-03-22 12:02:52] ============================================================
[2026-03-22 12:02:52]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 12:02:59]   SUCCESS: exit=0 elapsed=11.0s
[2026-03-22 12:02:59]   CMD: folio convert SRC_08.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:03:07]   SUCCESS: exit=0 elapsed=8.6s
[2026-03-22 12:03:07]   CMD: folio convert SRC_09.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:03:14]   SUCCESS: exit=0 elapsed=7.0s
[2026-03-22 12:03:14]   CMD: folio convert SRC_10.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:03:21]   SUCCESS: exit=0 elapsed=7.1s
[2026-03-22 12:03:21]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 12:03:22]   SUCCESS: exit=0 elapsed=50.2s
[2026-03-22 12:03:22]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt53
[2026-03-22 12:03:54]   SUCCESS: exit=0 elapsed=61.7s
[2026-03-22 12:03:54]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt53
[2026-03-22 12:04:23]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 12:04:23]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 12:04:23]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:06:59]   SUCCESS: exit=0 elapsed=155.8s
[2026-03-22 12:06:59]   CMD: folio convert SRC_13.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:07:42]   SUCCESS: exit=0 elapsed=260.3s
[2026-03-22 12:07:42]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt53
[2026-03-22 12:08:26]   SUCCESS: exit=0 elapsed=87.4s
[2026-03-22 12:08:26]   CMD: folio convert SRC_14.pptx --llm-profile anthropic_haiku3
[2026-03-22 12:08:47]   SUCCESS: exit=0 elapsed=292.6s
[2026-03-22 12:08:47]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt53
[2026-03-22 12:09:40]   ERROR: exit=1 elapsed=73.9s
[2026-03-22 12:09:40]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 12:09:40]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku3
[2026-03-22 12:10:35]   SUCCESS: exit=0 elapsed=54.4s
[2026-03-22 12:10:35]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 12:11:36]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 12:11:36]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 12:11:36]   SUMMARY: 13 success, 3 failed, 774s total
[2026-03-22 12:11:36] 
============================================================
[2026-03-22 12:11:36] PROFILE: openai_gpt53
[2026-03-22 12:11:36] ============================================================
[2026-03-22 12:11:36]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 12:12:33]   SUCCESS: exit=0 elapsed=56.2s
[2026-03-22 12:12:33]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt53
[2026-03-22 12:13:06]   SUCCESS: exit=0 elapsed=324.0s
[2026-03-22 12:13:06]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt53
[2026-03-22 12:15:37]   SUCCESS: exit=0 elapsed=150.4s
[2026-03-22 12:15:37]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt53
[2026-03-22 12:15:41]   SUCCESS: exit=0 elapsed=414.1s
[2026-03-22 12:15:41]   SKIP: already converted (<cached output>)
[2026-03-22 12:15:41]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt53
[2026-03-22 12:16:04]   SUCCESS: exit=0 elapsed=23.3s
[2026-03-22 12:16:04]   CMD: folio convert SRC_06.pdf --llm-profile openai_gpt53
[2026-03-22 12:16:05]   SUCCESS: exit=0 elapsed=28.7s
[2026-03-22 12:16:05]   CMD: folio convert SRC_06.pdf --llm-profile openai_gpt53
[2026-03-22 12:16:33]   SUCCESS: exit=0 elapsed=29.2s
[2026-03-22 12:16:33]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt53
[2026-03-22 12:16:35]   SUCCESS: exit=0 elapsed=30.1s
[2026-03-22 12:16:35]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt53
[2026-03-22 12:16:36]   ERROR: exit=1 elapsed=2.9s
[2026-03-22 12:16:36]   STDERR: _error...
✗ Error: [Errno 2] No such file or directory: '<workspace>/validation/runs/openai_gpt53/SRC_07/slides/slide-001.png'

[2026-03-22 12:16:36]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt53
[2026-03-22 12:16:51]   SUCCESS: exit=0 elapsed=15.1s
[2026-03-22 12:16:51]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt53
[2026-03-22 12:17:10]   SUCCESS: exit=0 elapsed=277.9s
[2026-03-22 12:17:10]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt53
[2026-03-22 12:17:13]   SUCCESS: exit=0 elapsed=21.9s
[2026-03-22 12:17:13]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt53
[2026-03-22 12:18:57]   SUCCESS: exit=0 elapsed=141.6s
[2026-03-22 12:18:57]   SKIP: already converted (<cached output>)
[2026-03-22 12:18:57]   SKIP: already converted (<cached output>)
[2026-03-22 12:18:57]   SKIP: already converted (<cached output>)
[2026-03-22 12:18:57]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 12:19:33]   SUCCESS: exit=0 elapsed=140.1s
[2026-03-22 12:19:33]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 12:19:59]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 12:19:59]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 12:19:59]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 12:20:35]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 12:20:35]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 12:20:35]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 12:25:20]   SUCCESS: exit=0 elapsed=489.8s
[2026-03-22 12:25:20]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt53
[2026-03-22 12:28:06]   SUCCESS: exit=0 elapsed=165.6s
[2026-03-22 12:28:06]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt53
[2026-03-22 12:28:34]   SUCCESS: exit=0 elapsed=28.4s
[2026-03-22 12:28:34]   CMD: folio convert SRC_06.pdf --llm-profile openai_gpt53
[2026-03-22 12:29:06]   SUCCESS: exit=0 elapsed=31.7s
[2026-03-22 12:29:06]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt53
[2026-03-22 12:31:47]   SUCCESS: exit=0 elapsed=161.1s
[2026-03-22 12:31:47]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt53
[2026-03-22 12:32:03]   SUCCESS: exit=0 elapsed=16.1s
[2026-03-22 12:32:03]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt53
[2026-03-22 12:32:17]   SUCCESS: exit=0 elapsed=14.1s
[2026-03-22 12:32:17]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt53
[2026-03-22 12:34:24]   SUCCESS: exit=0 elapsed=126.9s
[2026-03-22 12:34:24]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 12:35:09]   SUCCESS: exit=0 elapsed=873.5s
[2026-03-22 12:35:09]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt53
[2026-03-22 12:35:26]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 12:35:26]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 12:35:26]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 12:35:43]   SUCCESS: exit=0 elapsed=943.8s
[2026-03-22 12:35:43]   SKIP: already converted (<cached output>)
[2026-03-22 12:35:43]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt53
[2026-03-22 12:36:56]   ERROR: exit=1 elapsed=73.6s
[2026-03-22 12:36:56]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 12:36:56]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt53
[2026-03-22 12:39:29]   SUCCESS: exit=0 elapsed=153.0s
[2026-03-22 12:39:30]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 12:39:56]   SUCCESS: exit=0 elapsed=287.5s
[2026-03-22 12:39:56]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt53
[2026-03-22 12:40:32]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 12:40:32]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 12:40:32]   SUMMARY: 9 success, 7 failed, 2280s total
[2026-03-22 12:40:32] 
============================================================
[2026-03-22 12:40:32] PROFILE: openai_gpt41
[2026-03-22 12:40:32] ============================================================
[2026-03-22 12:40:32]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41
[2026-03-22 12:41:10]   ERROR: exit=1 elapsed=73.9s
[2026-03-22 12:41:10]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 12:41:10]   SKIP: already converted (<cached output>)
[2026-03-22 12:41:10]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 12:42:12]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 12:42:12]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 12:42:12]   SUMMARY: 10 success, 6 failed, 2360s total
[2026-03-22 12:42:12] 
============================================================
[2026-03-22 12:42:12] PROFILE: openai_gpt41
[2026-03-22 12:42:12] ============================================================
[2026-03-22 12:42:12]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41
[2026-03-22 12:42:25]   SUCCESS: exit=0 elapsed=113.8s
[2026-03-22 12:42:25]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt41
[2026-03-22 12:44:04]   SUCCESS: exit=0 elapsed=112.3s
[2026-03-22 12:44:04]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt41
[2026-03-22 12:45:26]   TIMEOUT after 600.0s
[2026-03-22 12:45:26]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt53
[2026-03-22 12:46:34]   SUCCESS: exit=0 elapsed=248.6s
[2026-03-22 12:46:34]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt41
[2026-03-22 12:49:50]   SUCCESS: exit=0 elapsed=264.0s
[2026-03-22 12:49:50]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt53
[2026-03-22 12:50:19]   SUCCESS: exit=0 elapsed=375.1s
[2026-03-22 12:50:19]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt41
[2026-03-22 12:51:04]   ERROR: exit=1 elapsed=74.0s
[2026-03-22 12:51:04]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 12:51:04]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt53
[2026-03-22 12:53:37]   SUCCESS: exit=0 elapsed=153.5s
[2026-03-22 12:53:37]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 12:54:39]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 12:54:39]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 12:54:39]   SUMMARY: 12 success, 4 failed, 2583s total
[2026-03-22 12:54:39] 
============================================================
[2026-03-22 12:54:39] PROFILE: openai_gpt41
[2026-03-22 12:54:39] ============================================================
[2026-03-22 12:54:39]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41
[2026-03-22 12:56:48]   SUCCESS: exit=0 elapsed=128.2s
[2026-03-22 12:56:48]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt41
[2026-03-22 13:01:08]   SUCCESS: exit=0 elapsed=260.2s
[2026-03-22 13:01:08]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt41
[2026-03-22 13:11:08]   TIMEOUT after 600.1s
[2026-03-22 13:11:08]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41
[2026-03-22 13:12:43]   SUCCESS: exit=0 elapsed=1569.3s
[2026-03-22 13:12:43]   SKIP: already converted (<cached output>)
[2026-03-22 13:12:43]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41
[2026-03-22 13:13:10]   SUCCESS: exit=0 elapsed=26.5s
[2026-03-22 13:13:10]   CMD: folio convert SRC_06.pdf --llm-profile openai_gpt41
[2026-03-22 13:13:35]   SUCCESS: exit=0 elapsed=25.1s
[2026-03-22 13:13:35]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt41
[2026-03-22 13:14:02]   SUCCESS: exit=0 elapsed=1423.1s
[2026-03-22 13:14:02]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41
[2026-03-22 13:14:08]   SUCCESS: exit=0 elapsed=180.5s
[2026-03-22 13:14:08]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41
[2026-03-22 13:14:31]   SUCCESS: exit=0 elapsed=22.5s
[2026-03-22 13:14:31]   CMD: folio convert SRC_06.pdf --llm-profile openai_gpt41
[2026-03-22 13:14:53]   SUCCESS: exit=0 elapsed=21.9s
[2026-03-22 13:14:53]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt41
[2026-03-22 13:15:31]   SUCCESS: exit=0 elapsed=116.1s
[2026-03-22 13:15:31]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt41
[2026-03-22 13:16:17]   SUCCESS: exit=0 elapsed=84.4s
[2026-03-22 13:16:17]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt41
[2026-03-22 13:16:42]   SUCCESS: exit=0 elapsed=71.1s
[2026-03-22 13:16:42]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt41
[2026-03-22 13:16:45]   SUCCESS: exit=0 elapsed=28.1s
[2026-03-22 13:16:45]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt41
[2026-03-22 13:16:54]   SUCCESS: exit=0 elapsed=171.7s
[2026-03-22 13:16:54]   SKIP: already converted (<cached output>)
[2026-03-22 13:16:54]   SKIP: already converted (<cached output>)
[2026-03-22 13:16:54]   SKIP: already converted (<cached output>)
[2026-03-22 13:16:54]   SKIP: already converted (<cached output>)
[2026-03-22 13:16:54]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt41
[2026-03-22 13:17:10]   SUCCESS: exit=0 elapsed=27.5s
[2026-03-22 13:17:10]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt41
[2026-03-22 13:17:12]   SUCCESS: exit=0 elapsed=26.7s
[2026-03-22 13:17:12]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt41
[2026-03-22 13:17:16]   SUCCESS: exit=0 elapsed=21.5s
[2026-03-22 13:17:16]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt41
[2026-03-22 13:18:05]   SUCCESS: exit=0 elapsed=55.3s
[2026-03-22 13:18:05]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 13:18:13]   SUCCESS: exit=0 elapsed=57.3s
[2026-03-22 13:18:13]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 13:18:24]   SUCCESS: exit=0 elapsed=72.1s
[2026-03-22 13:18:24]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 13:19:07]   ERROR: exit=1 elapsed=62.6s
[2026-03-22 13:19:07]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 13:19:07]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 13:19:15]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 13:19:15]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 13:19:15]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 13:19:26]   ERROR: exit=1 elapsed=61.4s
[2026-03-22 13:19:26]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 13:19:26]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 13:19:30]   ERROR: exit=1 elapsed=4.3s
[2026-03-22 13:19:30]   STDERR: ering failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/openai_gpt41/SRC_12/.slides_tmp/slide-013.png'

[2026-03-22 13:19:30]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt41
[2026-03-22 13:19:31]   ERROR: exit=1 elapsed=16.0s
[2026-03-22 13:19:31]   STDERR: ering failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/openai_gpt41/SRC_12/.slides_tmp/slide-019.png'

[2026-03-22 13:19:31]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt41
[2026-03-22 13:19:35]   ERROR: exit=1 elapsed=27.6s
[2026-03-22 13:19:35]   STDERR: 1 200 OK"
✗ Error: [Errno 2] No such file or directory: '<workspace>/validation/runs/openai_gpt41/SRC_12/slides/slide-001.png'

[2026-03-22 13:19:35]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt41
[2026-03-22 13:19:36]   ERROR: exit=1 elapsed=5.7s
[2026-03-22 13:19:36]   STDERR: ering failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/openai_gpt41/SRC_13/.slides_tmp/slide-001.png'

[2026-03-22 13:19:36]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt41
[2026-03-22 13:19:36]   ERROR: exit=1 elapsed=4.7s
[2026-03-22 13:19:36]   STDERR: ering failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/openai_gpt41/SRC_13/.slides_tmp/slide-001.png'

[2026-03-22 13:19:36]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt41
[2026-03-22 13:20:49]   ERROR: exit=1 elapsed=73.1s
[2026-03-22 13:20:49]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: Launch Services timed out opening SRC_14.pptx

[2026-03-22 13:20:49]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41
[2026-03-22 13:20:49]   ERROR: exit=1 elapsed=73.7s
[2026-03-22 13:20:49]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 13:20:49]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41
[2026-03-22 13:20:55]   ERROR: exit=1 elapsed=6.0s
[2026-03-22 13:20:55]   STDERR: ering failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/openai_gpt41/SRC_15/.slides_tmp/slide-011.png'

[2026-03-22 13:20:55]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 13:21:53]   SUCCESS: exit=0 elapsed=64.2s
[2026-03-22 13:21:53]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 13:21:57]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 13:21:57]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 13:21:57]   SUMMARY: 9 success, 7 failed, 1637s total
[2026-03-22 13:21:57] 
============================================================
[2026-03-22 13:21:57] PROFILE: openai_gpt41mini
[2026-03-22 13:21:57] ============================================================
[2026-03-22 13:21:57]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:22:55]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 13:22:55]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 13:22:55]   SUMMARY: 7 success, 9 failed, 2443s total
[2026-03-22 13:22:55] 
============================================================
[2026-03-22 13:22:55] PROFILE: openai_gpt41mini
[2026-03-22 13:22:55] ============================================================
[2026-03-22 13:22:55]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:23:28]   SUCCESS: exit=0 elapsed=232.7s
[2026-03-22 13:23:28]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt41
[2026-03-22 13:24:24]   SUCCESS: exit=0 elapsed=147.4s
[2026-03-22 13:24:24]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:24:42]   ERROR: exit=1 elapsed=74.0s
[2026-03-22 13:24:42]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 13:24:42]   SKIP: already converted (<cached output>)
[2026-03-22 13:24:42]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 13:25:00]   SUCCESS: exit=0 elapsed=125.3s
[2026-03-22 13:25:00]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:25:43]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 13:25:43]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 13:25:43]   SUMMARY: 10 success, 6 failed, 2712s total
[2026-03-22 13:25:43] 
============================================================
[2026-03-22 13:25:43] PROFILE: openai_gpt41mini
[2026-03-22 13:25:43] ============================================================
[2026-03-22 13:25:43]   SKIP: already converted (<cached output>)
[2026-03-22 13:25:43]   SKIP: already converted (<cached output>)
[2026-03-22 13:25:43]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:34:24]   TIMEOUT after 600.0s
[2026-03-22 13:34:24]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:35:48]   SUCCESS: exit=0 elapsed=648.2s
[2026-03-22 13:35:48]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:44:24]   TIMEOUT after 600.0s
[2026-03-22 13:44:24]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:48:36]   SUCCESS: exit=0 elapsed=252.1s
[2026-03-22 13:48:36]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:51:37]   SUCCESS: exit=0 elapsed=180.7s
[2026-03-22 13:51:37]   CMD: folio convert SRC_06.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:53:25]   SUCCESS: exit=0 elapsed=108.2s
[2026-03-22 13:53:25]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:53:41]   SUCCESS: exit=0 elapsed=1677.6s
[2026-03-22 13:53:41]   SKIP: already converted (<cached output>)
[2026-03-22 13:53:41]   SKIP: already converted (<cached output>)
[2026-03-22 13:53:41]   SKIP: already converted (<cached output>)
[2026-03-22 13:53:41]   SKIP: already converted (<cached output>)
[2026-03-22 13:53:41]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:56:39]   SUCCESS: exit=0 elapsed=193.5s
[2026-03-22 13:56:39]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt41mini
[2026-03-22 13:56:56]   SUCCESS: exit=0 elapsed=194.8s
[2026-03-22 13:56:56]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:00:11]   SUCCESS: exit=0 elapsed=195.6s
[2026-03-22 14:00:11]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:03:09]   SUCCESS: exit=0 elapsed=390.5s
[2026-03-22 14:03:09]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:04:56]   SUCCESS: exit=0 elapsed=284.5s
[2026-03-22 14:04:56]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-22 14:05:16]   SUCCESS: exit=0 elapsed=1767.7s
[2026-03-22 14:05:16]   SKIP: already converted (<cached output>)
[2026-03-22 14:05:16]   SKIP: already converted (<cached output>)
[2026-03-22 14:05:16]   SKIP: already converted (<cached output>)
[2026-03-22 14:05:16]   SKIP: already converted (<cached output>)
[2026-03-22 14:05:16]   SKIP: already converted (<cached output>)
[2026-03-22 14:05:16]   SKIP: already converted (<cached output>)
[2026-03-22 14:05:16]   SKIP: already converted (<cached output>)
[2026-03-22 14:05:16]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-22 14:05:58]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 14:05:58]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 14:05:58]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:06:18]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 14:06:18]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 14:06:18]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:06:34]   SUCCESS: exit=0 elapsed=204.9s
[2026-03-22 14:06:34]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:09:52]   SUCCESS: exit=0 elapsed=197.6s
[2026-03-22 14:09:52]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-22 14:10:54]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 14:10:54]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 14:10:54]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:20:54]   TIMEOUT after 600.0s
[2026-03-22 14:20:54]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:24:26]   SUCCESS: exit=0 elapsed=1088.1s
[2026-03-22 14:24:26]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:25:52]   SUCCESS: exit=0 elapsed=1194.2s
[2026-03-22 14:25:52]   SKIP: already converted (<cached output>)
[2026-03-22 14:25:52]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt41mini
[2026-03-22 14:27:06]   ERROR: exit=1 elapsed=74.0s
[2026-03-22 14:27:06]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 14:27:06]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:27:54]   SUCCESS: exit=0 elapsed=420.2s
[2026-03-22 14:27:54]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt41mini
[2026-03-22 14:29:07]   ERROR: exit=1 elapsed=73.5s
[2026-03-22 14:29:07]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 14:29:07]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41mini
[2026-03-22 14:29:18]   SUCCESS: exit=0 elapsed=131.8s
[2026-03-22 14:29:18]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-22 14:30:20]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 14:30:20]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 14:30:20]   SUMMARY: 6 success, 10 failed, 3876s total
[2026-03-22 14:30:20] 
============================================================
[2026-03-22 14:30:20] PROFILE: openai_gpt4o
[2026-03-22 14:30:20] ============================================================
[2026-03-22 14:30:20]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4o
[2026-03-22 14:31:07]   SUCCESS: exit=0 elapsed=119.2s
[2026-03-22 14:31:07]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-22 14:31:18]   SUCCESS: exit=0 elapsed=411.7s
[2026-03-22 14:31:18]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt41mini
[2026-03-22 14:31:31]   SUCCESS: exit=0 elapsed=71.6s
[2026-03-22 14:31:31]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt4o
[2026-03-22 14:32:08]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 14:32:08]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 14:32:08]   SUMMARY: 10 success, 6 failed, 4211s total
[2026-03-22 14:32:08] 
============================================================
[2026-03-22 14:32:08] PROFILE: openai_gpt4o
[2026-03-22 14:32:08] ============================================================
[2026-03-22 14:32:08]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4o
[2026-03-22 14:32:31]   ERROR: exit=1 elapsed=73.5s
[2026-03-22 14:32:31]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 14:32:31]   SKIP: already converted (<cached output>)
[2026-03-22 14:32:31]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-22 14:33:03]   SUCCESS: exit=0 elapsed=54.9s
[2026-03-22 14:33:03]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt4o
[2026-03-22 14:33:33]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 14:33:33]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 14:33:33]   SUMMARY: 5 success, 11 failed, 4238s total
[2026-03-22 14:33:33] 
============================================================
[2026-03-22 14:33:33] PROFILE: openai_gpt4o
[2026-03-22 14:33:33] ============================================================
[2026-03-22 14:33:33]   SKIP: already converted (<cached output>)
[2026-03-22 14:33:33]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt4o
[2026-03-22 14:34:54]   SUCCESS: exit=0 elapsed=202.5s
[2026-03-22 14:34:54]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt4o
[2026-03-22 14:36:16]   SUCCESS: exit=0 elapsed=163.1s
[2026-03-22 14:36:16]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt4o
[2026-03-22 14:36:59]   SUCCESS: exit=0 elapsed=235.7s
[2026-03-22 14:36:59]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt4o
[2026-03-22 14:46:59]   TIMEOUT after 600.0s
[2026-03-22 14:46:59]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4o
[2026-03-22 14:47:06]   SUCCESS: exit=0 elapsed=732.2s
[2026-03-22 14:47:06]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4o
[2026-03-22 14:47:51]   SUCCESS: exit=0 elapsed=695.5s
[2026-03-22 14:47:51]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4o
[2026-03-22 14:49:25]   SUCCESS: exit=0 elapsed=146.1s
[2026-03-22 14:49:25]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4o
[2026-03-22 14:49:38]   SUCCESS: exit=0 elapsed=13.1s
[2026-03-22 14:49:38]   CMD: folio convert SRC_06.pdf --llm-profile openai_gpt4o
[2026-03-22 14:49:58]   SUCCESS: exit=0 elapsed=171.7s
[2026-03-22 14:49:58]   SKIP: already converted (<cached output>)
[2026-03-22 14:49:58]   SKIP: already converted (<cached output>)
[2026-03-22 14:49:58]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt4o
[2026-03-22 14:50:03]   SUCCESS: exit=0 elapsed=131.1s
[2026-03-22 14:50:03]   SKIP: already converted (<cached output>)
[2026-03-22 14:50:03]   CMD: folio convert SRC_06.pdf --llm-profile openai_gpt4o
[2026-03-22 14:50:06]   SUCCESS: exit=0 elapsed=27.7s
[2026-03-22 14:50:06]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt4o
[2026-03-22 14:50:27]   SUCCESS: exit=0 elapsed=24.7s
[2026-03-22 14:50:27]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt4o
[2026-03-22 14:51:32]   SUCCESS: exit=0 elapsed=94.4s
[2026-03-22 14:51:32]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt4o
[2026-03-22 14:51:34]   SUCCESS: exit=0 elapsed=88.8s
[2026-03-22 14:51:34]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt4o
[2026-03-22 14:51:47]   SUCCESS: exit=0 elapsed=15.2s
[2026-03-22 14:51:47]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt4o
[2026-03-22 14:51:47]   SUCCESS: exit=0 elapsed=12.8s
[2026-03-22 14:51:47]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt4o
[2026-03-22 14:51:47]   ERROR: exit=1 elapsed=0.2s
[2026-03-22 14:51:47]   STDERR: rsion failed: Per-page rendering failed: [Errno 17] File exists: '<workspace>/validation/runs/openai_gpt4o/SRC_09/.slides_tmp'

[2026-03-22 14:51:47]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt4o
[2026-03-22 14:51:48]   ERROR: exit=1 elapsed=1.0s
[2026-03-22 14:51:48]   STDERR: ering failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/openai_gpt4o/SRC_09/.slides_tmp/slide-001.png'

[2026-03-22 14:51:48]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt4o
[2026-03-22 14:51:51]   SUCCESS: exit=0 elapsed=83.3s
[2026-03-22 14:51:51]   SKIP: already converted (<cached output>)
[2026-03-22 14:51:51]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt4o
[2026-03-22 14:52:26]   SUCCESS: exit=0 elapsed=38.0s
[2026-03-22 14:52:26]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-22 14:52:45]   SUCCESS: exit=0 elapsed=57.6s
[2026-03-22 14:52:45]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-22 14:53:15]   SUCCESS: exit=0 elapsed=84.0s
[2026-03-22 14:53:15]   SKIP: already converted (<cached output>)
[2026-03-22 14:53:15]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-22 14:53:28]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 14:53:28]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 14:53:28]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-22 14:53:47]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 14:53:47]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 14:53:47]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-22 14:53:48]   ERROR: exit=1 elapsed=20.3s
[2026-03-22 14:53:48]   STDERR: ering failed: [Errno 2] No such file or directory: '<workspace>/validation/runs/openai_gpt4o/SRC_12/.slides_tmp/slide-027.png'

[2026-03-22 14:53:48]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt4o
[2026-03-22 14:54:16]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 14:54:16]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 14:54:16]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-22 14:57:12]   SUCCESS: exit=0 elapsed=203.3s
[2026-03-22 14:57:12]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt4o
[2026-03-22 14:58:25]   ERROR: exit=1 elapsed=73.8s
[2026-03-22 14:58:25]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 14:58:25]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4o
[2026-03-22 14:59:31]   SUCCESS: exit=0 elapsed=66.0s
[2026-03-22 14:59:31]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4o
[2026-03-22 15:00:33]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 15:00:33]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 15:00:33]   SUMMARY: 10 success, 6 failed, 1705s total
[2026-03-22 15:00:33] 
============================================================
[2026-03-22 15:00:33] PROFILE: openai_gpt4omini
[2026-03-22 15:00:33] ============================================================
[2026-03-22 15:00:33]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:01:11]   SUCCESS: exit=0 elapsed=38.0s
[2026-03-22 15:01:11]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:02:12]   SUCCESS: exit=0 elapsed=476.2s
[2026-03-22 15:02:12]   SKIP: already converted (<cached output>)
[2026-03-22 15:02:12]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt4o
[2026-03-22 15:03:26]   ERROR: exit=1 elapsed=74.0s
[2026-03-22 15:03:26]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 15:03:26]   SKIP: already converted (<cached output>)
[2026-03-22 15:03:26]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4o
[2026-03-22 15:03:29]   SUCCESS: exit=0 elapsed=582.4s
[2026-03-22 15:03:29]   SKIP: already converted (<cached output>)
[2026-03-22 15:03:29]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt4o
[2026-03-22 15:04:29]   ERROR: exit=1 elapsed=62.9s
[2026-03-22 15:04:29]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 15:04:29]   SUMMARY: 7 success, 9 failed, 1856s total
[2026-03-22 15:04:29] 
============================================================
[2026-03-22 15:04:29] PROFILE: openai_gpt4omini
[2026-03-22 15:04:29] ============================================================
[2026-03-22 15:04:29]   SKIP: already converted (<cached output>)
[2026-03-22 15:04:29]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:04:43]   ERROR: exit=1 elapsed=73.7s
[2026-03-22 15:04:43]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 15:04:43]   SKIP: already converted (<cached output>)
[2026-03-22 15:04:43]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4o
[2026-03-22 15:05:44]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 15:05:44]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 15:05:44]   SUMMARY: 8 success, 8 failed, 2124s total
[2026-03-22 15:05:44] 
============================================================
[2026-03-22 15:05:44] PROFILE: openai_gpt4omini
[2026-03-22 15:05:44] ============================================================
[2026-03-22 15:05:44]   SKIP: already converted (<cached output>)
[2026-03-22 15:05:44]   SKIP: already converted (<cached output>)
[2026-03-22 15:05:44]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:07:05]   SUCCESS: exit=0 elapsed=353.7s
[2026-03-22 15:07:05]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:11:22]   SUCCESS: exit=0 elapsed=412.4s
[2026-03-22 15:11:22]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:17:05]   TIMEOUT after 600.0s
[2026-03-22 15:17:05]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:18:27]   SUCCESS: exit=0 elapsed=82.5s
[2026-03-22 15:18:27]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:18:38]   SUCCESS: exit=0 elapsed=11.0s
[2026-03-22 15:18:38]   CMD: folio convert SRC_06.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:18:46]   SUCCESS: exit=0 elapsed=7.8s
[2026-03-22 15:18:46]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:20:48]   SUCCESS: exit=0 elapsed=903.9s
[2026-03-22 15:20:48]   SKIP: already converted (<cached output>)
[2026-03-22 15:20:48]   SKIP: already converted (<cached output>)
[2026-03-22 15:20:48]   SKIP: already converted (<cached output>)
[2026-03-22 15:20:48]   SKIP: already converted (<cached output>)
[2026-03-22 15:20:48]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:22:54]   SUCCESS: exit=0 elapsed=126.2s
[2026-03-22 15:22:54]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:23:02]   SUCCESS: exit=0 elapsed=8.0s
[2026-03-22 15:23:02]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:24:59]   SUCCESS: exit=0 elapsed=373.0s
[2026-03-22 15:24:59]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:26:01]   SUCCESS: exit=0 elapsed=61.9s
[2026-03-22 15:26:01]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:26:10]   SUCCESS: exit=0 elapsed=8.6s
[2026-03-22 15:26:10]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:26:38]   SUCCESS: exit=0 elapsed=915.9s
[2026-03-22 15:26:38]   SKIP: already converted (<cached output>)
[2026-03-22 15:26:38]   SKIP: already converted (<cached output>)
[2026-03-22 15:26:38]   SKIP: already converted (<cached output>)
[2026-03-22 15:26:38]   SKIP: already converted (<cached output>)
[2026-03-22 15:26:38]   SKIP: already converted (<cached output>)
[2026-03-22 15:26:38]   SKIP: already converted (<cached output>)
[2026-03-22 15:26:38]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:29:15]   SUCCESS: exit=0 elapsed=373.2s
[2026-03-22 15:29:15]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4omini
[2026-03-22 15:30:17]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 15:30:17]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 15:30:17]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:31:07]   SUCCESS: exit=0 elapsed=269.1s
[2026-03-22 15:31:07]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4omini
[2026-03-22 15:31:34]   SUCCESS: exit=0 elapsed=324.6s
[2026-03-22 15:31:34]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4omini
[2026-03-22 15:32:08]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 15:32:08]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 15:32:08]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:32:36]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 15:32:36]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 15:32:36]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:42:36]   TIMEOUT after 600.0s
[2026-03-22 15:42:36]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:52:36]   TIMEOUT after 600.0s
[2026-03-22 15:52:36]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt4omini
[2026-03-22 15:53:51]   ERROR: exit=1 elapsed=74.5s
[2026-03-22 15:53:51]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 15:53:51]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4omini
[2026-03-22 15:55:02]   SUCCESS: exit=0 elapsed=71.8s
[2026-03-22 15:55:02]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-22 15:56:04]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 15:56:04]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 15:56:04]   SUMMARY: 10 success, 6 failed, 3331s total
[2026-03-22 15:56:04] 
============================================================
[2026-03-22 15:56:04] PROFILE: openai_gpt4turbo
[2026-03-22 15:56:04] ============================================================
[2026-03-22 15:56:04]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4turbo
[2026-03-22 15:56:18]   SUCCESS: exit=0 elapsed=14.2s
[2026-03-22 15:56:18]   CMD: folio convert SRC_02.pdf --llm-profile openai_gpt4turbo
[2026-03-22 15:56:55]   SUCCESS: exit=0 elapsed=36.3s
[2026-03-22 15:56:55]   CMD: folio convert SRC_03.pdf --llm-profile openai_gpt4turbo
[2026-03-22 15:58:43]   SUCCESS: exit=0 elapsed=108.0s
[2026-03-22 15:58:43]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4turbo
[2026-03-22 15:58:50]   SUCCESS: exit=0 elapsed=7.7s
[2026-03-22 15:58:50]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4turbo
[2026-03-22 15:58:55]   SUCCESS: exit=0 elapsed=4.8s
[2026-03-22 15:58:55]   CMD: folio convert SRC_06.pdf --llm-profile openai_gpt4turbo
[2026-03-22 15:59:00]   SUCCESS: exit=0 elapsed=5.0s
[2026-03-22 15:59:00]   CMD: folio convert SRC_07.pdf --llm-profile openai_gpt4turbo
[2026-03-22 15:59:06]   SUCCESS: exit=0 elapsed=5.3s
[2026-03-22 15:59:06]   CMD: folio convert SRC_08.pdf --llm-profile openai_gpt4turbo
[2026-03-22 15:59:10]   SUCCESS: exit=0 elapsed=4.7s
[2026-03-22 15:59:10]   CMD: folio convert SRC_09.pdf --llm-profile openai_gpt4turbo
[2026-03-22 15:59:11]   SUCCESS: exit=0 elapsed=1734.1s
[2026-03-22 15:59:11]   SKIP: already converted (<cached output>)
[2026-03-22 15:59:11]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt4omini
[2026-03-22 15:59:16]   SUCCESS: exit=0 elapsed=5.3s
[2026-03-22 15:59:16]   CMD: folio convert SRC_10.pdf --llm-profile openai_gpt4turbo
[2026-03-22 15:59:23]   SUCCESS: exit=0 elapsed=7.0s
[2026-03-22 15:59:23]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4turbo
[2026-03-22 15:59:35]   SUCCESS: exit=0 elapsed=12.1s
[2026-03-22 15:59:35]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4turbo
[2026-03-22 16:00:29]   SUCCESS: exit=0 elapsed=54.7s
[2026-03-22 16:00:29]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt4turbo
[2026-03-22 16:00:51]   SUCCESS: exit=0 elapsed=21.6s
[2026-03-22 16:00:51]   CMD: folio convert SRC_14.pptx --llm-profile openai_gpt4turbo
[2026-03-22 16:01:21]   SUCCESS: exit=0 elapsed=30.5s
[2026-03-22 16:01:21]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4turbo
[2026-03-22 16:01:39]   SUCCESS: exit=0 elapsed=17.8s
[2026-03-22 16:01:39]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4turbo
[2026-03-22 16:02:06]   SUCCESS: exit=0 elapsed=26.5s
[2026-03-22 16:02:06]   SUMMARY: 16 success, 0 failed, 362s total
[2026-03-22 16:02:06] 
============================================================
[2026-03-22 16:02:06] PROFILE: google_gemini25pro
[2026-03-22 16:02:06] ============================================================
[2026-03-22 16:02:06]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25pro
[2026-03-22 16:02:08]   TIMEOUT after 1800.0s
[2026-03-22 16:02:08]   CMD: folio convert SRC_13.pdf --llm-profile openai_gpt4omini
[2026-03-22 16:08:05]   SUCCESS: exit=0 elapsed=533.5s
[2026-03-22 16:08:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:08:05]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-22 16:09:59]   SUCCESS: exit=0 elapsed=473.1s
[2026-03-22 16:09:59]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini25pro
[2026-03-22 16:12:25]   SUCCESS: exit=0 elapsed=145.8s
[2026-03-22 16:12:25]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini25pro
[2026-03-22 16:16:05]   SUCCESS: exit=0 elapsed=479.7s
[2026-03-22 16:16:05]   SUMMARY: 7 success, 9 failed, 4220s total
[2026-03-22 16:16:05] 
============================================================
[2026-03-22 16:16:05] PROFILE: openai_gpt4turbo
[2026-03-22 16:16:05] ============================================================
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SUMMARY: 0 success, 16 failed, 0s total
[2026-03-22 16:16:05] 
============================================================
[2026-03-22 16:16:05] PROFILE: google_gemini25pro
[2026-03-22 16:16:05] ============================================================
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   SKIP: already converted (<cached output>)
[2026-03-22 16:16:05]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25pro
[2026-03-22 16:16:30]   SUCCESS: exit=0 elapsed=25.5s
[2026-03-22 16:16:30]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-22 16:18:52]   SUCCESS: exit=0 elapsed=141.6s
[2026-03-22 16:18:52]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini25pro
[2026-03-22 16:19:52]   SUCCESS: exit=0 elapsed=447.3s
[2026-03-22 16:19:52]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25pro
[2026-03-22 16:20:17]   SUCCESS: exit=0 elapsed=25.1s
[2026-03-22 16:20:17]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-22 16:21:32]   SUCCESS: exit=0 elapsed=1164.0s
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SUMMARY: 4 success, 12 failed, 4623s total
[2026-03-22 16:21:32] 
============================================================
[2026-03-22 16:21:32] PROFILE: openai_gpt4turbo
[2026-03-22 16:21:32] ============================================================
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SUMMARY: 0 success, 16 failed, 0s total
[2026-03-22 16:21:32] 
============================================================
[2026-03-22 16:21:32] PROFILE: google_gemini25pro
[2026-03-22 16:21:32] ============================================================
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   SKIP: already converted (<cached output>)
[2026-03-22 16:21:32]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini25pro
[2026-03-22 16:22:08]   SUCCESS: exit=0 elapsed=196.0s
[2026-03-22 16:22:08]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini25pro
[2026-03-22 16:22:34]   SUCCESS: exit=0 elapsed=25.8s
[2026-03-22 16:22:34]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini25pro
[2026-03-22 16:22:41]   SUCCESS: exit=0 elapsed=144.2s
[2026-03-22 16:22:41]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini25pro
[2026-03-22 16:24:40]   SUCCESS: exit=0 elapsed=187.5s
[2026-03-22 16:24:40]   SKIP: already converted (<cached output>)
[2026-03-22 16:24:40]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini25pro
[2026-03-22 16:24:53]   SUCCESS: exit=0 elapsed=139.0s
[2026-03-22 16:24:53]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini25pro
[2026-03-22 16:25:54]   SUCCESS: exit=0 elapsed=192.4s
[2026-03-22 16:25:54]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini25pro
[2026-03-22 16:26:18]   SUCCESS: exit=0 elapsed=24.2s
[2026-03-22 16:26:18]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini25pro
[2026-03-22 16:26:55]   SUCCESS: exit=0 elapsed=134.9s
[2026-03-22 16:26:55]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini25pro
[2026-03-22 16:27:15]   SUCCESS: exit=0 elapsed=142.6s
[2026-03-22 16:27:15]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini25pro
[2026-03-22 16:27:36]   SUCCESS: exit=0 elapsed=20.9s
[2026-03-22 16:27:36]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25pro
[2026-03-22 16:28:00]   SUCCESS: exit=0 elapsed=24.2s
[2026-03-22 16:28:00]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-22 16:28:33]   SUCCESS: exit=0 elapsed=134.9s
[2026-03-22 16:28:33]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini25pro
[2026-03-22 16:29:14]   SUCCESS: exit=0 elapsed=138.8s
[2026-03-22 16:29:14]   SKIP: already converted (<cached output>)
[2026-03-22 16:29:14]   SKIP: already converted (<cached output>)
[2026-03-22 16:29:14]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-22 16:30:54]   SUCCESS: exit=0 elapsed=141.6s
[2026-03-22 16:30:54]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini25pro
[2026-03-22 16:31:16]   SUCCESS: exit=0 elapsed=21.6s
[2026-03-22 16:31:16]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25pro
[2026-03-22 16:31:38]   SUCCESS: exit=0 elapsed=22.5s
[2026-03-22 16:31:38]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-22 16:39:04]   SUCCESS: exit=0 elapsed=663.9s
[2026-03-22 16:39:04]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini25pro
[2026-03-22 16:40:08]   SUCCESS: exit=0 elapsed=654.4s
[2026-03-22 16:40:08]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini25pro
[2026-03-22 16:41:38]   TIMEOUT after 600.0s
[2026-03-22 16:41:38]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini25pro
[2026-03-22 16:44:33]   SUCCESS: exit=0 elapsed=328.7s
[2026-03-22 16:44:33]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini25pro
[2026-03-22 16:45:17]   SUCCESS: exit=0 elapsed=308.7s
[2026-03-22 16:45:17]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini25pro
[2026-03-22 16:46:59]   SUCCESS: exit=0 elapsed=320.2s
[2026-03-22 16:46:59]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini25pro
[2026-03-22 16:51:35]   SUCCESS: exit=0 elapsed=422.5s
[2026-03-22 16:51:35]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-22 16:51:55]   SUCCESS: exit=0 elapsed=397.8s
[2026-03-22 16:51:55]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-22 16:53:30]   SUCCESS: exit=0 elapsed=390.9s
[2026-03-22 16:53:30]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-22 16:55:58]   SUCCESS: exit=0 elapsed=262.3s
[2026-03-22 16:55:58]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-22 16:56:43]   SUCCESS: exit=0 elapsed=288.9s
[2026-03-22 16:56:43]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-22 16:57:40]   SUCCESS: exit=0 elapsed=102.7s
[2026-03-22 16:57:40]   SUMMARY: 13 success, 3 failed, 2496s total
[2026-03-22 16:57:40] 
============================================================
[2026-03-22 16:57:40] PROFILE: google_gemini25flash
[2026-03-22 16:57:40] ============================================================
[2026-03-22 16:57:40]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-22 16:57:43]   SUCCESS: exit=0 elapsed=253.9s
[2026-03-22 16:57:43]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-22 16:57:45]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 16:57:45]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 16:57:45]   SUMMARY: 7 success, 9 failed, 2173s total
[2026-03-22 16:57:45] 
============================================================
[2026-03-22 16:57:45] PROFILE: google_gemini25flash
[2026-03-22 16:57:45] ============================================================
[2026-03-22 16:57:45]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-22 16:58:45]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 16:58:45]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 16:58:45]   SUMMARY: 14 success, 2 failed, 3400s total
[2026-03-22 16:58:45] 
============================================================
[2026-03-22 16:58:45] PROFILE: google_gemini25flash
[2026-03-22 16:58:45] ============================================================
[2026-03-22 16:58:45]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-22 17:03:40]   SUCCESS: exit=0 elapsed=360.1s
[2026-03-22 17:03:40]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini25flash
[2026-03-22 17:03:48]   SUCCESS: exit=0 elapsed=362.2s
[2026-03-22 17:03:48]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini25flash
[2026-03-22 17:04:01]   ERROR: exit=1 elapsed=13.0s
[2026-03-22 17:04:01]   STDERR: iled: [Errno 2] No such file or directory: '<workspace>/validation/runs/google_gemini25flash/SRC_02/.slides_tmp/slide-002.png'

[2026-03-22 17:04:01]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini25flash
[2026-03-22 17:04:28]   SUCCESS: exit=0 elapsed=342.9s
[2026-03-22 17:04:28]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini25flash
[2026-03-22 17:05:33]   SUCCESS: exit=0 elapsed=112.6s
[2026-03-22 17:05:33]   SKIP: already converted (<cached output>)
[2026-03-22 17:05:33]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25flash
[2026-03-22 17:05:50]   SUCCESS: exit=0 elapsed=16.7s
[2026-03-22 17:05:50]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25flash
[2026-03-22 17:06:07]   SUCCESS: exit=0 elapsed=98.3s
[2026-03-22 17:06:07]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini25flash
[2026-03-22 17:07:13]   SUCCESS: exit=0 elapsed=82.9s
[2026-03-22 17:07:13]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini25flash
[2026-03-22 17:08:53]   SUCCESS: exit=0 elapsed=100.1s
[2026-03-22 17:08:53]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini25flash
[2026-03-22 17:09:05]   SUCCESS: exit=0 elapsed=12.6s
[2026-03-22 17:09:05]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini25flash
[2026-03-22 17:09:11]   SUCCESS: exit=0 elapsed=310.1s
[2026-03-22 17:09:11]   SKIP: already converted (<cached output>)
[2026-03-22 17:09:11]   SKIP: already converted (<cached output>)
[2026-03-22 17:09:11]   SKIP: already converted (<cached output>)
[2026-03-22 17:09:11]   SKIP: already converted (<cached output>)
[2026-03-22 17:09:11]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini25flash
[2026-03-22 17:10:17]   SUCCESS: exit=0 elapsed=71.4s
[2026-03-22 17:10:17]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini25flash
[2026-03-22 17:10:26]   SUCCESS: exit=0 elapsed=75.1s
[2026-03-22 17:10:26]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini25flash
[2026-03-22 17:11:05]   SUCCESS: exit=0 elapsed=298.1s
[2026-03-22 17:11:05]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25flash
[2026-03-22 17:11:20]   SUCCESS: exit=0 elapsed=15.0s
[2026-03-22 17:11:20]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25flash
[2026-03-22 17:11:21]   SUCCESS: exit=0 elapsed=64.2s
[2026-03-22 17:11:21]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini25flash
[2026-03-22 17:11:37]   SUCCESS: exit=0 elapsed=16.0s
[2026-03-22 17:11:37]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-22 17:11:38]   SUCCESS: exit=0 elapsed=72.6s
[2026-03-22 17:11:38]   SKIP: already converted (<cached output>)
[2026-03-22 17:11:38]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-22 17:12:39]   ERROR: exit=1 elapsed=62.2s
[2026-03-22 17:12:39]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:12:39]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-22 17:12:40]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 17:12:40]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:12:40]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-22 17:12:43]   SUCCESS: exit=0 elapsed=83.2s
[2026-03-22 17:12:43]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini25flash
[2026-03-22 17:13:00]   ERROR: exit=1 elapsed=19.7s
[2026-03-22 17:13:00]   STDERR: iled: [Errno 2] No such file or directory: '<workspace>/validation/runs/google_gemini25flash/SRC_12/.slides_tmp/slide-027.png'

[2026-03-22 17:13:00]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini25flash
[2026-03-22 17:14:26]   SUCCESS: exit=0 elapsed=103.7s
[2026-03-22 17:14:26]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini25flash
[2026-03-22 17:14:39]   SUCCESS: exit=0 elapsed=12.4s
[2026-03-22 17:14:39]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini25flash
[2026-03-22 17:16:03]   SUCCESS: exit=0 elapsed=84.4s
[2026-03-22 17:16:03]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini25flash
[2026-03-22 17:16:16]   SUCCESS: exit=0 elapsed=196.0s
[2026-03-22 17:16:16]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini25flash
[2026-03-22 17:17:11]   SUCCESS: exit=0 elapsed=68.1s
[2026-03-22 17:17:11]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini25flash
[2026-03-22 17:17:27]   SUCCESS: exit=0 elapsed=15.6s
[2026-03-22 17:17:27]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-22 17:17:30]   ERROR: exit=1 elapsed=74.0s
[2026-03-22 17:17:30]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:17:30]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-22 17:18:29]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 17:18:29]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:18:29]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-22 17:18:57]   SUCCESS: exit=0 elapsed=378.0s
[2026-03-22 17:18:57]   SKIP: already converted (<cached output>)
[2026-03-22 17:18:57]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini25flash
[2026-03-22 17:20:03]   SUCCESS: exit=0 elapsed=153.3s
[2026-03-22 17:20:03]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-22 17:20:10]   ERROR: exit=1 elapsed=73.4s
[2026-03-22 17:20:10]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:20:10]   SKIP: already converted (<cached output>)
[2026-03-22 17:20:10]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-22 17:21:05]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 17:21:05]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 17:21:05]   SUMMARY: 6 success, 10 failed, 1400s total
[2026-03-22 17:21:05] 
============================================================
[2026-03-22 17:21:05] PROFILE: google_gemini20flash
[2026-03-22 17:21:05] ============================================================
[2026-03-22 17:21:05]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash
[2026-03-22 17:21:12]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 17:21:12]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 17:21:12]   SUMMARY: 10 success, 6 failed, 1412s total
[2026-03-22 17:21:12] 
============================================================
[2026-03-22 17:21:12] PROFILE: google_gemini20flash
[2026-03-22 17:21:12] ============================================================
[2026-03-22 17:21:12]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash
[2026-03-22 17:21:13]   ERROR: exit=1 elapsed=7.6s
[2026-03-22 17:21:13]   STDERR: .
✗ Error: [Errno 2] No such file or directory: '<workspace>/validation/runs/google_gemini20flash/SRC_01/slides/slide-001.png'

[2026-03-22 17:21:13]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini20flash
[2026-03-22 17:21:37]   SUCCESS: exit=0 elapsed=24.8s
[2026-03-22 17:21:37]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini20flash
[2026-03-22 17:21:39]   ERROR: exit=1 elapsed=26.2s
[2026-03-22 17:21:39]   STDERR: "
✗ Error: [Errno 2] No such file or directory: '<workspace>/validation/runs/google_gemini20flash/SRC_02/slides/slide-002.png'

[2026-03-22 17:21:39]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini20flash
[2026-03-22 17:22:43]   SUCCESS: exit=0 elapsed=66.2s
[2026-03-22 17:22:43]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini20flash
[2026-03-22 17:22:49]   ERROR: exit=1 elapsed=69.8s
[2026-03-22 17:22:49]   STDERR: .
✗ Error: [Errno 2] No such file or directory: '<workspace>/validation/runs/google_gemini20flash/SRC_03/slides/slide-001.png'

[2026-03-22 17:22:49]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash
[2026-03-22 17:22:59]   SUCCESS: exit=0 elapsed=10.3s
[2026-03-22 17:22:59]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash
[2026-03-22 17:23:07]   SUCCESS: exit=0 elapsed=8.1s
[2026-03-22 17:23:07]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini20flash
[2026-03-22 17:23:15]   SUCCESS: exit=0 elapsed=8.2s
[2026-03-22 17:23:15]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini20flash
[2026-03-22 17:23:24]   SUCCESS: exit=0 elapsed=8.3s
[2026-03-22 17:23:24]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini20flash
[2026-03-22 17:23:32]   SUCCESS: exit=0 elapsed=8.2s
[2026-03-22 17:23:32]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini20flash
[2026-03-22 17:23:39]   SUCCESS: exit=0 elapsed=7.6s
[2026-03-22 17:23:39]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini20flash
[2026-03-22 17:23:48]   SUCCESS: exit=0 elapsed=8.6s
[2026-03-22 17:23:48]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-22 17:24:40]   SUCCESS: exit=0 elapsed=370.8s
[2026-03-22 17:24:40]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini25flash
[2026-03-22 17:24:50]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 17:24:50]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:24:50]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash
[2026-03-22 17:25:37]   SUCCESS: exit=0 elapsed=173.8s
[2026-03-22 17:25:37]   SKIP: already converted (<cached output>)
[2026-03-22 17:25:37]   SKIP: already converted (<cached output>)
[2026-03-22 17:25:37]   SKIP: already converted (<cached output>)
[2026-03-22 17:25:37]   SKIP: already converted (<cached output>)
[2026-03-22 17:25:37]   SKIP: already converted (<cached output>)
[2026-03-22 17:25:37]   SKIP: already converted (<cached output>)
[2026-03-22 17:25:37]   SKIP: already converted (<cached output>)
[2026-03-22 17:25:37]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-22 17:26:39]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 17:26:39]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:26:39]   SKIP: already converted (<cached output>)
[2026-03-22 17:26:39]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini20flash
[2026-03-22 17:27:57]   SUCCESS: exit=0 elapsed=197.3s
[2026-03-22 17:27:57]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini25flash
[2026-03-22 17:28:07]   SUCCESS: exit=0 elapsed=87.5s
[2026-03-22 17:28:07]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini20flash
[2026-03-22 17:28:08]   SUCCESS: exit=0 elapsed=197.8s
[2026-03-22 17:28:08]   SKIP: already converted (<cached output>)
[2026-03-22 17:28:08]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini20flash
[2026-03-22 17:29:11]   ERROR: exit=1 elapsed=73.9s
[2026-03-22 17:29:11]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:29:11]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-22 17:29:20]   ERROR: exit=1 elapsed=73.7s
[2026-03-22 17:29:20]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:29:20]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash
[2026-03-22 17:29:21]   ERROR: exit=1 elapsed=73.7s
[2026-03-22 17:29:21]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:29:21]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash
[2026-03-22 17:29:26]   ERROR: exit=1 elapsed=4.5s
[2026-03-22 17:29:26]   STDERR: iled: [Errno 2] No such file or directory: '<workspace>/validation/runs/google_gemini20flash/SRC_15/.slides_tmp/slide-005.png'

[2026-03-22 17:29:26]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-22 17:30:28]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 17:30:28]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 17:30:28]   SUMMARY: 8 success, 8 failed, 563s total
[2026-03-22 17:30:28] 
============================================================
[2026-03-22 17:30:28] PROFILE: google_gemini20flash001
[2026-03-22 17:30:28] ============================================================
[2026-03-22 17:30:28]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:30:36]   SUCCESS: exit=0 elapsed=75.4s
[2026-03-22 17:30:36]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-22 17:30:56]   SUCCESS: exit=0 elapsed=28.3s
[2026-03-22 17:30:56]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:31:37]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 17:31:37]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 17:31:37]   SUMMARY: 5 success, 11 failed, 625s total
[2026-03-22 17:31:37] 
============================================================
[2026-03-22 17:31:37] PROFILE: google_gemini20flash001
[2026-03-22 17:31:37] ============================================================
[2026-03-22 17:31:37]   SKIP: already converted (<cached output>)
[2026-03-22 17:31:37]   SKIP: already converted (<cached output>)
[2026-03-22 17:31:37]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:31:43]   SUCCESS: exit=0 elapsed=152.2s
[2026-03-22 17:31:43]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-22 17:31:59]   SUCCESS: exit=0 elapsed=63.4s
[2026-03-22 17:31:59]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:32:45]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 17:32:45]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 17:32:45]   SUMMARY: 13 success, 3 failed, 2039s total
[2026-03-22 17:32:45] 
============================================================
[2026-03-22 17:32:45] PROFILE: google_gemini20flash
[2026-03-22 17:32:45] ============================================================
[2026-03-22 17:32:45]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash
[2026-03-22 17:33:10]   SUCCESS: exit=0 elapsed=25.7s
[2026-03-22 17:33:10]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini20flash
[2026-03-22 17:34:13]   SUCCESS: exit=0 elapsed=62.7s
[2026-03-22 17:34:13]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini20flash
[2026-03-22 17:34:32]   SUCCESS: exit=0 elapsed=174.5s
[2026-03-22 17:34:32]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:34:43]   SUCCESS: exit=0 elapsed=10.9s
[2026-03-22 17:34:43]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:34:50]   SUCCESS: exit=0 elapsed=170.2s
[2026-03-22 17:34:50]   SKIP: already converted (<cached output>)
[2026-03-22 17:34:50]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:34:52]   SUCCESS: exit=0 elapsed=9.1s
[2026-03-22 17:34:52]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:34:58]   SUCCESS: exit=0 elapsed=8.1s
[2026-03-22 17:34:58]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:35:00]   SUCCESS: exit=0 elapsed=8.0s
[2026-03-22 17:35:00]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:35:06]   SUCCESS: exit=0 elapsed=7.9s
[2026-03-22 17:35:06]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:35:08]   SUCCESS: exit=0 elapsed=8.1s
[2026-03-22 17:35:08]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:35:14]   SUCCESS: exit=0 elapsed=8.0s
[2026-03-22 17:35:14]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:35:16]   SUCCESS: exit=0 elapsed=8.2s
[2026-03-22 17:35:16]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:35:22]   SUCCESS: exit=0 elapsed=7.9s
[2026-03-22 17:35:22]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:35:24]   SUCCESS: exit=0 elapsed=7.6s
[2026-03-22 17:35:24]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:35:29]   SUCCESS: exit=0 elapsed=7.1s
[2026-03-22 17:35:29]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:35:32]   SUCCESS: exit=0 elapsed=8.4s
[2026-03-22 17:35:32]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-22 17:35:37]   SUCCESS: exit=0 elapsed=8.5s
[2026-03-22 17:35:37]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-22 17:36:34]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 17:36:34]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:36:34]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:36:39]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 17:36:39]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:36:39]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:36:55]   ERROR: exit=1 elapsed=16.2s
[2026-03-22 17:36:55]   STDERR: d: [Errno 2] No such file or directory: '<workspace>/validation/runs/google_gemini20flash001/SRC_12/.slides_tmp/slide-019.png'

[2026-03-22 17:36:55]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:37:18]   SUCCESS: exit=0 elapsed=43.8s
[2026-03-22 17:37:18]   SKIP: already converted (<cached output>)
[2026-03-22 17:37:18]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini20flash001
[2026-03-22 17:37:23]   SUCCESS: exit=0 elapsed=190.3s
[2026-03-22 17:37:23]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash
[2026-03-22 17:37:34]   SUCCESS: exit=0 elapsed=10.6s
[2026-03-22 17:37:34]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash
[2026-03-22 17:37:41]   SUCCESS: exit=0 elapsed=7.5s
[2026-03-22 17:37:41]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini20flash
[2026-03-22 17:37:49]   SUCCESS: exit=0 elapsed=7.9s
[2026-03-22 17:37:49]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini20flash
[2026-03-22 17:37:58]   SUCCESS: exit=0 elapsed=8.2s
[2026-03-22 17:37:58]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini20flash
[2026-03-22 17:38:06]   SUCCESS: exit=0 elapsed=8.1s
[2026-03-22 17:38:06]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini20flash
[2026-03-22 17:38:13]   SUCCESS: exit=0 elapsed=6.9s
[2026-03-22 17:38:13]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini20flash
[2026-03-22 17:38:21]   SUCCESS: exit=0 elapsed=8.5s
[2026-03-22 17:38:21]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-22 17:38:27]   SUCCESS: exit=0 elapsed=91.4s
[2026-03-22 17:38:27]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini20flash001
[2026-03-22 17:38:32]   ERROR: exit=1 elapsed=74.2s
[2026-03-22 17:38:32]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:38:32]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:39:23]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 17:39:23]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:39:23]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash
[2026-03-22 17:39:40]   ERROR: exit=1 elapsed=73.6s
[2026-03-22 17:39:40]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:39:40]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:39:44]   SUCCESS: exit=0 elapsed=72.4s
[2026-03-22 17:39:44]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-22 17:40:46]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 17:40:46]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 17:40:46]   SUMMARY: 10 success, 6 failed, 549s total
[2026-03-22 17:40:46] 
============================================================
[2026-03-22 17:40:46] PROFILE: google_gemini20lite
[2026-03-22 17:40:46] ============================================================
[2026-03-22 17:40:46]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20lite
[2026-03-22 17:40:54]   SUCCESS: exit=0 elapsed=74.2s
[2026-03-22 17:40:54]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-22 17:41:09]   SUCCESS: exit=0 elapsed=23.1s
[2026-03-22 17:41:09]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini20lite
[2026-03-22 17:41:56]   ERROR: exit=1 elapsed=61.4s
[2026-03-22 17:41:56]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 17:41:56]   SUMMARY: 11 success, 5 failed, 688s total
[2026-03-22 17:41:56] 
============================================================
[2026-03-22 17:41:56] PROFILE: google_gemini20lite
[2026-03-22 17:41:56] ============================================================
[2026-03-22 17:41:56]   SKIP: already converted (<cached output>)
[2026-03-22 17:41:56]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini20lite
[2026-03-22 17:42:12]   SUCCESS: exit=0 elapsed=62.8s
[2026-03-22 17:42:12]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini20lite
[2026-03-22 17:42:39]   SUCCESS: exit=0 elapsed=196.2s
[2026-03-22 17:42:39]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini20flash
[2026-03-22 17:43:00]   SUCCESS: exit=0 elapsed=64.8s
[2026-03-22 17:43:00]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini20lite
[2026-03-22 17:44:03]   SUCCESS: exit=0 elapsed=84.6s
[2026-03-22 17:44:03]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini20flash
[2026-03-22 17:45:01]   SUCCESS: exit=0 elapsed=168.8s
[2026-03-22 17:45:01]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20lite
[2026-03-22 17:45:11]   SUCCESS: exit=0 elapsed=10.1s
[2026-03-22 17:45:11]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20lite
[2026-03-22 17:45:17]   ERROR: exit=1 elapsed=73.9s
[2026-03-22 17:45:17]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:45:17]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash
[2026-03-22 17:45:19]   SUCCESS: exit=0 elapsed=7.8s
[2026-03-22 17:45:19]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini20lite
[2026-03-22 17:45:27]   SUCCESS: exit=0 elapsed=8.3s
[2026-03-22 17:45:27]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini20lite
[2026-03-22 17:45:36]   SUCCESS: exit=0 elapsed=9.1s
[2026-03-22 17:45:36]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini20lite
[2026-03-22 17:45:44]   SUCCESS: exit=0 elapsed=8.0s
[2026-03-22 17:45:44]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini20lite
[2026-03-22 17:45:52]   SUCCESS: exit=0 elapsed=171.2s
[2026-03-22 17:45:52]   SKIP: already converted (<cached output>)
[2026-03-22 17:45:52]   SKIP: already converted (<cached output>)
[2026-03-22 17:45:52]   SKIP: already converted (<cached output>)
[2026-03-22 17:45:52]   SKIP: already converted (<cached output>)
[2026-03-22 17:45:52]   SKIP: already converted (<cached output>)
[2026-03-22 17:45:52]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini20lite
[2026-03-22 17:45:52]   SUCCESS: exit=0 elapsed=7.8s
[2026-03-22 17:45:52]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini20lite
[2026-03-22 17:45:59]   SUCCESS: exit=0 elapsed=7.4s
[2026-03-22 17:45:59]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini20lite
[2026-03-22 17:46:00]   SUCCESS: exit=0 elapsed=8.2s
[2026-03-22 17:46:00]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-22 17:46:16]   SUCCESS: exit=0 elapsed=16.7s
[2026-03-22 17:46:16]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-22 17:46:29]   SUCCESS: exit=0 elapsed=71.5s
[2026-03-22 17:46:29]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-22 17:47:02]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 17:47:02]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:47:02]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-22 17:47:18]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 17:47:18]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:47:18]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-22 17:47:23]   ERROR: exit=1 elapsed=5.2s
[2026-03-22 17:47:23]   STDERR: ailed: [Errno 2] No such file or directory: '<workspace>/validation/runs/google_gemini20lite/SRC_12/.slides_tmp/slide-018.png'

[2026-03-22 17:47:23]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini20lite
[2026-03-22 17:47:26]   ERROR: exit=1 elapsed=23.7s
[2026-03-22 17:47:26]   STDERR: e.
✗ Error: [Errno 2] No such file or directory: '<workspace>/validation/runs/google_gemini20lite/SRC_12/slides/slide-001.png'

[2026-03-22 17:47:26]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini20lite
[2026-03-22 17:47:26]   ERROR: exit=1 elapsed=2.7s
[2026-03-22 17:47:26]   STDERR: ailed: [Errno 2] No such file or directory: '<workspace>/validation/runs/google_gemini20lite/SRC_13/.slides_tmp/slide-013.png'

[2026-03-22 17:47:26]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini20lite
[2026-03-22 17:47:31]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 17:47:31]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 17:47:31]   SUMMARY: 13 success, 3 failed, 886s total
[2026-03-22 17:47:31] 
============================================================
[2026-03-22 17:47:31] PROFILE: google_gemini20flash001
[2026-03-22 17:47:31] ============================================================
[2026-03-22 17:47:31]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:47:56]   SUCCESS: exit=0 elapsed=25.8s
[2026-03-22 17:47:56]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:48:39]   ERROR: exit=1 elapsed=73.6s
[2026-03-22 17:48:39]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:48:39]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20lite
[2026-03-22 17:49:00]   SUCCESS: exit=0 elapsed=63.1s
[2026-03-22 17:49:00]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:49:02]   SUCCESS: exit=0 elapsed=96.3s
[2026-03-22 17:49:02]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini20lite
[2026-03-22 17:49:55]   SUCCESS: exit=0 elapsed=76.0s
[2026-03-22 17:49:55]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-22 17:50:16]   ERROR: exit=1 elapsed=74.0s
[2026-03-22 17:50:16]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:50:16]   SKIP: already converted (<cached output>)
[2026-03-22 17:50:16]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-22 17:50:57]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 17:50:57]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 17:50:57]   SUMMARY: 5 success, 11 failed, 542s total
[2026-03-22 17:50:57] 
--- STABILITY ---
[2026-03-22 17:50:57] 
============================================================
[2026-03-22 17:50:57] STABILITY: anthropic_opus4
[2026-03-22 17:50:57] ============================================================
[2026-03-22 17:50:57]   --- Repetition 1/3 ---
[2026-03-22 17:50:57]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_opus4
[2026-03-22 17:51:18]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 17:51:18]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 17:51:18]   SUMMARY: 11 success, 5 failed, 632s total
[2026-03-22 17:51:18] 
--- STABILITY ---
[2026-03-22 17:51:18] 
============================================================
[2026-03-22 17:51:18] STABILITY: anthropic_opus4
[2026-03-22 17:51:18] ============================================================
[2026-03-22 17:51:18]   --- Repetition 1/3 ---
[2026-03-22 17:51:18]   SKIP: already converted (<cached output>)
[2026-03-22 17:51:18]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_opus4
[2026-03-22 17:51:45]   SUCCESS: exit=0 elapsed=165.0s
[2026-03-22 17:51:45]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:51:55]   SUCCESS: exit=0 elapsed=10.0s
[2026-03-22 17:51:55]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:52:02]   SUCCESS: exit=0 elapsed=7.9s
[2026-03-22 17:52:02]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:52:10]   SUCCESS: exit=0 elapsed=8.0s
[2026-03-22 17:52:10]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:52:18]   SUCCESS: exit=0 elapsed=8.0s
[2026-03-22 17:52:18]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:52:26]   SUCCESS: exit=0 elapsed=7.8s
[2026-03-22 17:52:26]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:52:33]   SUCCESS: exit=0 elapsed=7.3s
[2026-03-22 17:52:33]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:52:42]   SUCCESS: exit=0 elapsed=8.1s
[2026-03-22 17:52:42]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-22 17:53:43]   ERROR: exit=1 elapsed=61.4s
[2026-03-22 17:53:43]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 17:53:43]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:54:19]   SUCCESS: exit=0 elapsed=202.2s
[2026-03-22 17:54:19]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_opus4
[2026-03-22 17:56:56]   SUCCESS: exit=0 elapsed=192.9s
[2026-03-22 17:56:56]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:57:43]   SUCCESS: exit=0 elapsed=385.8s
[2026-03-22 17:57:43]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_opus4
[2026-03-22 17:58:27]   SUCCESS: exit=0 elapsed=91.1s
[2026-03-22 17:58:27]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini20flash001
[2026-03-22 17:59:41]   ERROR: exit=1 elapsed=74.1s
[2026-03-22 17:59:41]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 17:59:41]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash001
[2026-03-22 17:59:41]   SUCCESS: exit=0 elapsed=321.7s
[2026-03-22 17:59:41]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_opus4
[2026-03-22 18:00:13]   SUCCESS: exit=0 elapsed=149.9s
[2026-03-22 18:00:13]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_opus4
[2026-03-22 18:00:56]   SUCCESS: exit=0 elapsed=75.2s
[2026-03-22 18:00:56]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-22 18:01:15]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 18:01:15]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 18:01:15]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 18:01:58]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 18:01:58]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 18:01:58]   SUMMARY: 13 success, 3 failed, 867s total
[2026-03-22 18:01:58] 
============================================================
[2026-03-22 18:01:58] PROFILE: google_gemini20lite
[2026-03-22 18:01:58] ============================================================
[2026-03-22 18:01:58]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20lite
[2026-03-22 18:02:15]   SUCCESS: exit=0 elapsed=153.9s
[2026-03-22 18:02:15]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_opus4
[2026-03-22 18:02:23]   SUCCESS: exit=0 elapsed=24.9s
[2026-03-22 18:02:23]   CMD: folio convert SRC_02.pdf --llm-profile google_gemini20lite
[2026-03-22 18:03:17]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 18:03:17]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 18:03:17]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 18:03:27]   SUCCESS: exit=0 elapsed=64.5s
[2026-03-22 18:03:27]   CMD: folio convert SRC_03.pdf --llm-profile google_gemini20lite
[2026-03-22 18:06:20]   SUCCESS: exit=0 elapsed=173.3s
[2026-03-22 18:06:20]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20lite
[2026-03-22 18:06:30]   SUCCESS: exit=0 elapsed=9.6s
[2026-03-22 18:06:30]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20lite
[2026-03-22 18:23:23]   SUCCESS: exit=0 elapsed=1013.3s
[2026-03-22 18:23:23]   CMD: folio convert SRC_06.pdf --llm-profile google_gemini20lite
[2026-03-22 18:23:35]   SUCCESS: exit=0 elapsed=11.6s
[2026-03-22 18:23:35]   CMD: folio convert SRC_07.pdf --llm-profile google_gemini20lite
[2026-03-22 18:23:44]   SUCCESS: exit=0 elapsed=8.8s
[2026-03-22 18:23:44]   CMD: folio convert SRC_08.pdf --llm-profile google_gemini20lite
[2026-03-22 18:23:52]   SUCCESS: exit=0 elapsed=8.2s
[2026-03-22 18:23:52]   CMD: folio convert SRC_09.pdf --llm-profile google_gemini20lite
[2026-03-22 18:24:00]   SUCCESS: exit=0 elapsed=8.4s
[2026-03-22 18:24:00]   CMD: folio convert SRC_10.pdf --llm-profile google_gemini20lite
[2026-03-22 18:24:20]   SUCCESS: exit=0 elapsed=19.9s
[2026-03-22 18:24:20]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-22 18:25:22]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 18:25:22]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 18:25:22]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-22 18:28:56]   SUCCESS: exit=0 elapsed=214.5s
[2026-03-22 18:28:56]   CMD: folio convert SRC_13.pdf --llm-profile google_gemini20lite
[2026-03-22 18:30:36]   SUCCESS: exit=0 elapsed=99.9s
[2026-03-22 18:30:36]   CMD: folio convert SRC_14.pptx --llm-profile google_gemini20lite
[2026-03-22 18:31:50]   ERROR: exit=1 elapsed=73.9s
[2026-03-22 18:31:50]   STDERR: Converting: SRC_14.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_14.pptx within 73s

[2026-03-22 18:31:50]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20lite
[2026-03-22 18:33:05]   SUCCESS: exit=0 elapsed=74.6s
[2026-03-22 18:33:05]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-22 18:34:06]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 18:34:06]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 18:34:06]   SUMMARY: 13 success, 3 failed, 1929s total
[2026-03-22 18:34:06] 
--- STABILITY ---
[2026-03-22 18:34:06] 
============================================================
[2026-03-22 18:34:06] STABILITY: anthropic_opus4
[2026-03-22 18:34:06] ============================================================
[2026-03-22 18:34:06]   --- Repetition 1/3 ---
[2026-03-22 18:34:06]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_opus4
[2026-03-22 18:37:18]   SUCCESS: exit=0 elapsed=191.5s
[2026-03-22 18:37:18]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_opus4
[2026-03-22 18:37:47]   SUCCESS: exit=0 elapsed=2192.0s
[2026-03-22 18:37:47]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_opus4
[2026-03-22 18:38:12]   SUCCESS: exit=0 elapsed=2095.4s
[2026-03-22 18:38:12]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_opus4
[2026-03-22 18:40:35]   SUCCESS: exit=0 elapsed=167.6s
[2026-03-22 18:40:35]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_opus4
[2026-03-22 18:41:08]   SUCCESS: exit=0 elapsed=175.6s
[2026-03-22 18:41:08]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_opus4
[2026-03-22 18:41:37]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 18:41:37]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 18:41:37]   --- Repetition 2/3 ---
[2026-03-22 18:41:37]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_opus4
[2026-03-22 18:42:09]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 18:42:09]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 18:42:09]   --- Repetition 2/3 ---
[2026-03-22 18:42:09]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_opus4
[2026-03-22 18:43:43]   SUCCESS: exit=0 elapsed=385.1s
[2026-03-22 18:43:43]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_opus4
[2026-03-22 18:45:00]   SUCCESS: exit=0 elapsed=203.4s
[2026-03-22 18:45:00]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_opus4
[2026-03-22 18:45:30]   SUCCESS: exit=0 elapsed=200.6s
[2026-03-22 18:45:30]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_opus4
[2026-03-22 18:46:25]   SUCCESS: exit=0 elapsed=162.3s
[2026-03-22 18:46:25]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_opus4
[2026-03-22 18:47:27]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 18:47:27]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 18:47:27]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 18:51:26]   SUCCESS: exit=0 elapsed=386.3s
[2026-03-22 18:51:26]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_opus4
[2026-03-22 18:51:56]   SUCCESS: exit=0 elapsed=386.1s
[2026-03-22 18:51:56]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_opus4
[2026-03-22 18:54:01]   SUCCESS: exit=0 elapsed=155.1s
[2026-03-22 18:54:01]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_opus4
[2026-03-22 18:54:25]   SUCCESS: exit=0 elapsed=149.3s
[2026-03-22 18:54:25]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_opus4
[2026-03-22 18:55:03]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 18:55:03]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 18:55:03]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 18:55:27]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 18:55:27]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 18:55:27]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 18:55:34]   ERROR: exit=1 elapsed=6.7s
[2026-03-22 18:55:34]   STDERR: no 2] No such file or directory: '<workspace>/validation/runs/stability/rep2_anthropic_opus4/SRC_12/.slides_tmp/slide-002.png'

[2026-03-22 18:55:34]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_opus4
[2026-03-22 18:55:39]   ERROR: exit=1 elapsed=36.1s
[2026-03-22 18:55:39]   STDERR:  [Errno 2] No such file or directory: '<workspace>/validation/runs/stability/rep2_anthropic_opus4/SRC_12/slides/slide-001.png'

[2026-03-22 18:55:39]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_opus4
[2026-03-22 18:55:48]   ERROR: exit=1 elapsed=8.9s
[2026-03-22 18:55:48]   STDERR: no 2] No such file or directory: '<workspace>/validation/runs/stability/rep2_anthropic_opus4/SRC_15/.slides_tmp/slide-004.png'

[2026-03-22 18:55:48]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_opus4
[2026-03-22 18:56:50]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 18:56:50]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 18:56:50]   --- Repetition 3/3 ---
[2026-03-22 18:56:50]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_opus4
[2026-03-22 18:57:27]   TIMEOUT after 600.0s
[2026-03-22 18:57:27]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_opus4
[2026-03-22 18:58:21]   SUCCESS: exit=0 elapsed=167.2s
[2026-03-22 18:58:21]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_opus4
[2026-03-22 18:59:23]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 18:59:23]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 18:59:23]   --- Repetition 3/3 ---
[2026-03-22 18:59:23]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_opus4
[2026-03-22 19:00:06]   SUCCESS: exit=0 elapsed=195.5s
[2026-03-22 19:00:06]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_opus4
[2026-03-22 19:00:15]   SUCCESS: exit=0 elapsed=168.1s
[2026-03-22 19:00:15]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_opus4
[2026-03-22 19:01:16]   ERROR: exit=1 elapsed=61.4s
[2026-03-22 19:01:16]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 19:01:16]   --- Repetition 2/3 ---
[2026-03-22 19:01:16]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_opus4
[2026-03-22 19:02:41]   SUCCESS: exit=0 elapsed=198.8s
[2026-03-22 19:02:41]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_opus4
[2026-03-22 19:04:18]   SUCCESS: exit=0 elapsed=181.9s
[2026-03-22 19:04:18]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_opus4
[2026-03-22 19:06:33]   SUCCESS: exit=0 elapsed=387.2s
[2026-03-22 19:06:33]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_opus4
[2026-03-22 19:09:08]   SUCCESS: exit=0 elapsed=154.6s
[2026-03-22 19:09:08]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_opus4
[2026-03-22 19:10:09]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 19:10:09]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 19:10:09]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 19:10:47]   SUCCESS: exit=0 elapsed=388.8s
[2026-03-22 19:10:47]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_opus4
[2026-03-22 19:11:46]   SUCCESS: exit=0 elapsed=544.8s
[2026-03-22 19:11:46]   SKIP: already converted (<cached output>)
[2026-03-22 19:11:46]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_opus4
[2026-03-22 19:12:48]   ERROR: exit=1 elapsed=61.4s
[2026-03-22 19:12:48]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 19:12:48]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 19:13:17]   SUCCESS: exit=0 elapsed=149.7s
[2026-03-22 19:13:17]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_opus4
[2026-03-22 19:14:19]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 19:14:19]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 19:14:19]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 19:24:19]   TIMEOUT after 600.0s
[2026-03-22 19:24:19]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_opus4
[2026-03-22 19:27:01]   SUCCESS: exit=0 elapsed=162.6s
[2026-03-22 19:27:01]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_opus4
[2026-03-22 19:28:03]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 19:28:03]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 19:28:03]   --- Repetition 3/3 ---
[2026-03-22 19:28:03]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_opus4
[2026-03-22 19:28:36]   SUCCESS: exit=0 elapsed=1106.7s
[2026-03-22 19:28:36]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_opus4
[2026-03-22 19:31:18]   SUCCESS: exit=0 elapsed=162.1s
[2026-03-22 19:31:18]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_opus4
[2026-03-22 19:31:20]   SUCCESS: exit=0 elapsed=197.6s
[2026-03-22 19:31:20]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_opus4
[2026-03-22 19:32:20]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 19:32:20]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 19:32:20] 
============================================================
[2026-03-22 19:32:20] STABILITY: anthropic_sonnet4
[2026-03-22 19:32:20] ============================================================
[2026-03-22 19:32:20]   --- Repetition 1/3 ---
[2026-03-22 19:32:20]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:32:35]   SUCCESS: exit=0 elapsed=1187.8s
[2026-03-22 19:32:35]   SKIP: already converted (<cached output>)
[2026-03-22 19:32:35]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_opus4
[2026-03-22 19:33:37]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 19:33:37]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 19:33:37] 
============================================================
[2026-03-22 19:33:37] STABILITY: anthropic_sonnet4
[2026-03-22 19:33:37] ============================================================
[2026-03-22 19:33:37]   --- Repetition 1/3 ---
[2026-03-22 19:33:37]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:33:49]   SUCCESS: exit=0 elapsed=89.3s
[2026-03-22 19:33:49]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:35:11]   SUCCESS: exit=0 elapsed=94.3s
[2026-03-22 19:35:11]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:37:03]   SUCCESS: exit=0 elapsed=194.1s
[2026-03-22 19:37:03]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:37:45]   SUCCESS: exit=0 elapsed=384.6s
[2026-03-22 19:37:45]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_opus4
[2026-03-22 19:37:56]   SUCCESS: exit=0 elapsed=52.9s
[2026-03-22 19:37:56]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 19:38:20]   SUCCESS: exit=0 elapsed=189.0s
[2026-03-22 19:38:20]   SKIP: already converted (<cached output>)
[2026-03-22 19:38:20]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 19:38:58]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 19:38:58]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 19:38:58]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:39:22]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 19:39:22]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 19:39:22]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:39:44]   ERROR: exit=1 elapsed=22.0s
[2026-03-22 19:39:44]   STDERR:  2] No such file or directory: '<workspace>/validation/runs/stability/rep1_anthropic_sonnet4/SRC_12/.slides_tmp/slide-007.png'

[2026-03-22 19:39:44]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:40:19]   SUCCESS: exit=0 elapsed=153.9s
[2026-03-22 19:40:19]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_opus4
[2026-03-22 19:40:31]   ERROR: exit=1 elapsed=92.5s
[2026-03-22 19:40:31]   STDERR: Errno 2] No such file or directory: '<workspace>/validation/runs/stability/rep1_anthropic_sonnet4/SRC_12/slides/slide-007.png'

[2026-03-22 19:40:31]   SKIP: already converted (<cached output>)
[2026-03-22 19:40:31]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 19:41:20]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 19:41:20]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 19:41:20]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_opus4
[2026-03-22 19:41:33]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 19:41:33]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 19:41:33]   --- Repetition 2/3 ---
[2026-03-22 19:41:33]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:42:20]   SUCCESS: exit=0 elapsed=155.9s
[2026-03-22 19:42:20]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 19:43:00]   SUCCESS: exit=0 elapsed=87.2s
[2026-03-22 19:43:00]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:43:22]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 19:43:22]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 19:43:22]   --- Repetition 2/3 ---
[2026-03-22 19:43:22]   SKIP: already converted (<cached output>)
[2026-03-22 19:43:22]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:46:28]   SUCCESS: exit=0 elapsed=208.4s
[2026-03-22 19:46:28]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:46:35]   SUCCESS: exit=0 elapsed=193.2s
[2026-03-22 19:46:35]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:47:24]   SUCCESS: exit=0 elapsed=55.9s
[2026-03-22 19:47:24]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 19:47:41]   SUCCESS: exit=0 elapsed=65.8s
[2026-03-22 19:47:41]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 19:48:26]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 19:48:26]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 19:48:26]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:48:43]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 19:48:43]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 19:48:43]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:49:07]   ERROR: exit=1 elapsed=24.7s
[2026-03-22 19:49:07]   STDERR:  2] No such file or directory: '<workspace>/validation/runs/stability/rep2_anthropic_sonnet4/SRC_12/.slides_tmp/slide-014.png'

[2026-03-22 19:49:07]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:51:20]   TIMEOUT after 600.0s
[2026-03-22 19:51:20]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_opus4
[2026-03-22 19:51:38]   SUCCESS: exit=0 elapsed=150.5s
[2026-03-22 19:51:38]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 19:52:39]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 19:52:39]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 19:52:39]   --- Repetition 3/3 ---
[2026-03-22 19:52:39]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:54:03]   SUCCESS: exit=0 elapsed=162.1s
[2026-03-22 19:54:03]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_opus4
[2026-03-22 19:54:07]   SUCCESS: exit=0 elapsed=88.0s
[2026-03-22 19:54:07]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:55:04]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 19:55:04]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 19:55:04] 
============================================================
[2026-03-22 19:55:04] STABILITY: anthropic_sonnet4
[2026-03-22 19:55:04] ============================================================
[2026-03-22 19:55:04]   --- Repetition 1/3 ---
[2026-03-22 19:55:04]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:56:33]   SUCCESS: exit=0 elapsed=88.5s
[2026-03-22 19:56:33]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:57:32]   SUCCESS: exit=0 elapsed=204.3s
[2026-03-22 19:57:32]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:58:29]   SUCCESS: exit=0 elapsed=57.3s
[2026-03-22 19:58:29]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 19:59:31]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 19:59:31]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 19:59:31]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 19:59:54]   SUCCESS: exit=0 elapsed=201.3s
[2026-03-22 19:59:54]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:01:23]   SUCCESS: exit=0 elapsed=88.7s
[2026-03-22 20:01:23]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 20:01:53]   SUCCESS: exit=0 elapsed=806.9s
[2026-03-22 20:01:53]   SKIP: already converted (<cached output>)
[2026-03-22 20:01:53]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 20:02:24]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 20:02:24]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:02:24]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:02:55]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 20:02:55]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:02:55]   --- Repetition 3/3 ---
[2026-03-22 20:02:55]   SKIP: already converted (<cached output>)
[2026-03-22 20:02:55]   SKIP: already converted (<cached output>)
[2026-03-22 20:02:55]   SKIP: already converted (<cached output>)
[2026-03-22 20:02:55]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 20:03:57]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 20:03:57]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:03:57]   SKIP: already converted (<cached output>)
[2026-03-22 20:03:57]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:06:23]   SUCCESS: exit=0 elapsed=146.8s
[2026-03-22 20:06:23]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 20:07:25]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 20:07:25]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:07:25] 
============================================================
[2026-03-22 20:07:25] STABILITY: anthropic_haiku45
[2026-03-22 20:07:25] ============================================================
[2026-03-22 20:07:25]   --- Repetition 1/3 ---
[2026-03-22 20:07:25]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:08:19]   SUCCESS: exit=0 elapsed=53.6s
[2026-03-22 20:08:19]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:10:51]   SUCCESS: exit=0 elapsed=152.9s
[2026-03-22 20:10:51]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:11:46]   SUCCESS: exit=0 elapsed=54.1s
[2026-03-22 20:11:46]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:12:24]   TIMEOUT after 600.0s
[2026-03-22 20:12:24]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:12:47]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 20:12:47]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:12:47]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:13:35]   SUCCESS: exit=0 elapsed=844.4s
[2026-03-22 20:13:35]   SKIP: already converted (<cached output>)
[2026-03-22 20:13:35]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 20:14:38]   ERROR: exit=1 elapsed=62.2s
[2026-03-22 20:14:38]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:14:38] 
============================================================
[2026-03-22 20:14:38] STABILITY: anthropic_haiku45
[2026-03-22 20:14:38] ============================================================
[2026-03-22 20:14:38]   --- Repetition 1/3 ---
[2026-03-22 20:14:38]   SKIP: already converted (<cached output>)
[2026-03-22 20:14:38]   SKIP: already converted (<cached output>)
[2026-03-22 20:14:38]   SKIP: already converted (<cached output>)
[2026-03-22 20:14:38]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:15:12]   SUCCESS: exit=0 elapsed=168.1s
[2026-03-22 20:15:12]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 20:15:39]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 20:15:39]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:15:39]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:16:14]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 20:16:14]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:16:14]   --- Repetition 2/3 ---
[2026-03-22 20:16:14]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:17:50]   SUCCESS: exit=0 elapsed=96.1s
[2026-03-22 20:17:50]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:21:33]   SUCCESS: exit=0 elapsed=222.6s
[2026-03-22 20:21:33]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:22:32]   SUCCESS: exit=0 elapsed=59.2s
[2026-03-22 20:22:32]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 20:23:34]   ERROR: exit=1 elapsed=62.2s
[2026-03-22 20:23:34]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:23:34]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:25:08]   SUCCESS: exit=0 elapsed=741.2s
[2026-03-22 20:25:08]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:26:49]   SUCCESS: exit=0 elapsed=100.8s
[2026-03-22 20:26:49]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:27:37]   SUCCESS: exit=0 elapsed=717.8s
[2026-03-22 20:27:37]   SKIP: already converted (<cached output>)
[2026-03-22 20:27:37]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:27:51]   ERROR: exit=1 elapsed=62.2s
[2026-03-22 20:27:51]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:27:51]   --- Repetition 2/3 ---
[2026-03-22 20:27:51]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:28:39]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 20:28:39]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:28:39]   --- Repetition 2/3 ---
[2026-03-22 20:28:39]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:28:45]   SUCCESS: exit=0 elapsed=54.3s
[2026-03-22 20:28:45]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:29:30]   SUCCESS: exit=0 elapsed=52.0s
[2026-03-22 20:29:30]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:31:17]   SUCCESS: exit=0 elapsed=151.3s
[2026-03-22 20:31:17]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:31:46]   SUCCESS: exit=0 elapsed=135.6s
[2026-03-22 20:31:46]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:32:18]   SUCCESS: exit=0 elapsed=61.0s
[2026-03-22 20:32:18]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:32:39]   SUCCESS: exit=0 elapsed=53.1s
[2026-03-22 20:32:39]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:33:20]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 20:33:20]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:33:20]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:33:34]   TIMEOUT after 600.0s
[2026-03-22 20:33:34]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:33:41]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 20:33:41]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:33:41]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:34:04]   ERROR: exit=1 elapsed=23.6s
[2026-03-22 20:34:04]   STDERR:  2] No such file or directory: '<workspace>/validation/runs/stability/rep2_anthropic_haiku45/SRC_12/.slides_tmp/slide-007.png'

[2026-03-22 20:34:04]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:34:40]   ERROR: exit=1 elapsed=80.2s
[2026-03-22 20:34:40]   STDERR: Errno 2] No such file or directory: '<workspace>/validation/runs/stability/rep2_anthropic_haiku45/SRC_12/slides/slide-007.png'

[2026-03-22 20:34:40]   SKIP: already converted (<cached output>)
[2026-03-22 20:34:40]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:35:42]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 20:35:42]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:35:42]   --- Repetition 3/3 ---
[2026-03-22 20:35:42]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:35:44]   SUCCESS: exit=0 elapsed=99.7s
[2026-03-22 20:35:44]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:36:15]   SUCCESS: exit=0 elapsed=161.0s
[2026-03-22 20:36:15]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 20:36:37]   SUCCESS: exit=0 elapsed=55.8s
[2026-03-22 20:36:37]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:36:46]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 20:36:46]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:36:46]   --- Repetition 3/3 ---
[2026-03-22 20:36:46]   SKIP: already converted (<cached output>)
[2026-03-22 20:36:46]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:37:17]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 20:37:17]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:37:17]   --- Repetition 3/3 ---
[2026-03-22 20:37:17]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:38:48]   SUCCESS: exit=0 elapsed=90.5s
[2026-03-22 20:38:48]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:38:50]   SUCCESS: exit=0 elapsed=132.8s
[2026-03-22 20:38:50]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:38:57]   SUCCESS: exit=0 elapsed=131.4s
[2026-03-22 20:38:57]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:39:44]   SUCCESS: exit=0 elapsed=53.6s
[2026-03-22 20:39:44]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:39:51]   SUCCESS: exit=0 elapsed=54.1s
[2026-03-22 20:39:51]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:40:46]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 20:40:46]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:40:46]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:40:53]   ERROR: exit=1 elapsed=62.2s
[2026-03-22 20:40:53]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:40:53]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:41:28]   ERROR: exit=1 elapsed=35.0s
[2026-03-22 20:41:28]   STDERR:  2] No such file or directory: '<workspace>/validation/runs/stability/rep3_anthropic_haiku45/SRC_12/.slides_tmp/slide-025.png'

[2026-03-22 20:41:28]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:42:11]   SUCCESS: exit=0 elapsed=203.8s
[2026-03-22 20:42:11]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:43:06]   SUCCESS: exit=0 elapsed=54.1s
[2026-03-22 20:43:06]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_sonnet4
[2026-03-22 20:43:13]   SUCCESS: exit=0 elapsed=104.4s
[2026-03-22 20:43:13]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:44:08]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 20:44:08]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:44:08]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:44:14]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 20:44:14]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:44:14] 
============================================================
[2026-03-22 20:44:14] STABILITY: anthropic_haiku3
[2026-03-22 20:44:14] ============================================================
[2026-03-22 20:44:14]   --- Repetition 1/3 ---
[2026-03-22 20:44:14]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:44:39]   SUCCESS: exit=0 elapsed=24.2s
[2026-03-22 20:44:39]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:44:51]   SUCCESS: exit=0 elapsed=11.9s
[2026-03-22 20:44:51]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:44:57]   SUCCESS: exit=0 elapsed=6.5s
[2026-03-22 20:44:57]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 20:45:59]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 20:45:59]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:45:59]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:48:49]   SUCCESS: exit=0 elapsed=169.8s
[2026-03-22 20:48:49]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:49:54]   SUCCESS: exit=0 elapsed=64.9s
[2026-03-22 20:49:54]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 20:50:56]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 20:50:56]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:50:56]   --- Repetition 2/3 ---
[2026-03-22 20:50:56]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:51:18]   SUCCESS: exit=0 elapsed=22.1s
[2026-03-22 20:51:18]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:51:28]   SUCCESS: exit=0 elapsed=9.9s
[2026-03-22 20:51:28]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:51:34]   SUCCESS: exit=0 elapsed=5.9s
[2026-03-22 20:51:34]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 20:52:35]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 20:52:35]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:52:35]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:53:27]   SUCCESS: exit=0 elapsed=761.1s
[2026-03-22 20:53:27]   SKIP: already converted (<cached output>)
[2026-03-22 20:53:27]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 20:54:08]   TIMEOUT after 600.0s
[2026-03-22 20:54:08]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_sonnet4
[2026-03-22 20:54:29]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 20:54:29]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:54:29] 
============================================================
[2026-03-22 20:54:29] STABILITY: anthropic_haiku3
[2026-03-22 20:54:29] ============================================================
[2026-03-22 20:54:29]   --- Repetition 1/3 ---
[2026-03-22 20:54:29]   SKIP: already converted (<cached output>)
[2026-03-22 20:54:29]   SKIP: already converted (<cached output>)
[2026-03-22 20:54:29]   SKIP: already converted (<cached output>)
[2026-03-22 20:54:29]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 20:55:27]   SUCCESS: exit=0 elapsed=171.5s
[2026-03-22 20:55:27]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:55:31]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 20:55:31]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:55:31]   SKIP: already converted (<cached output>)
[2026-03-22 20:55:31]   SKIP: already converted (<cached output>)
[2026-03-22 20:55:31]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 20:56:26]   SUCCESS: exit=0 elapsed=59.5s
[2026-03-22 20:56:26]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 20:56:33]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 20:56:33]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:56:33]   --- Repetition 2/3 ---
[2026-03-22 20:56:33]   SKIP: already converted (<cached output>)
[2026-03-22 20:56:33]   SKIP: already converted (<cached output>)
[2026-03-22 20:56:33]   SKIP: already converted (<cached output>)
[2026-03-22 20:56:33]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 20:56:46]   SUCCESS: exit=0 elapsed=158.0s
[2026-03-22 20:56:46]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_sonnet4
[2026-03-22 20:57:28]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 20:57:28]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:57:28]   --- Repetition 3/3 ---
[2026-03-22 20:57:28]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:57:34]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 20:57:34]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:57:34]   SKIP: already converted (<cached output>)
[2026-03-22 20:57:34]   SKIP: already converted (<cached output>)
[2026-03-22 20:57:34]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 20:57:48]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 20:57:48]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:57:48] 
============================================================
[2026-03-22 20:57:48] STABILITY: anthropic_haiku45
[2026-03-22 20:57:48] ============================================================
[2026-03-22 20:57:48]   --- Repetition 1/3 ---
[2026-03-22 20:57:48]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:57:52]   SUCCESS: exit=0 elapsed=24.3s
[2026-03-22 20:57:52]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:58:03]   SUCCESS: exit=0 elapsed=10.9s
[2026-03-22 20:58:03]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:58:08]   SUCCESS: exit=0 elapsed=4.9s
[2026-03-22 20:58:08]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 20:58:36]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 20:58:36]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 20:58:36]   --- Repetition 3/3 ---
[2026-03-22 20:58:36]   SKIP: already converted (<cached output>)
[2026-03-22 20:58:36]   SKIP: already converted (<cached output>)
[2026-03-22 20:58:36]   SKIP: already converted (<cached output>)
[2026-03-22 20:58:36]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 20:58:42]   SUCCESS: exit=0 elapsed=53.9s
[2026-03-22 20:58:42]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku45
[2026-03-22 20:59:10]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 20:59:10]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:59:10]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:59:38]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 20:59:38]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 20:59:38]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku3
[2026-03-22 20:59:38]   ERROR: exit=1 elapsed=28.6s
[2026-03-22 20:59:38]   STDERR: o 2] No such file or directory: '<workspace>/validation/runs/stability/rep3_anthropic_haiku3/SRC_12/.slides_tmp/slide-025.png'

[2026-03-22 20:59:38]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku3
[2026-03-22 21:00:43]   SUCCESS: exit=0 elapsed=64.6s
[2026-03-22 21:00:43]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 21:00:53]   SUCCESS: exit=0 elapsed=131.0s
[2026-03-22 21:00:53]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:01:45]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 21:01:45]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:01:45] 
============================================================
[2026-03-22 21:01:45] STABILITY: openai_gpt53
[2026-03-22 21:01:45] ============================================================
[2026-03-22 21:01:45]   --- Repetition 1/3 ---
[2026-03-22 21:01:45]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 21:01:53]   SUCCESS: exit=0 elapsed=60.1s
[2026-03-22 21:01:53]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 21:02:35]   SUCCESS: exit=0 elapsed=177.4s
[2026-03-22 21:02:35]   SKIP: already converted (<cached output>)
[2026-03-22 21:02:35]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 21:02:51]   SUCCESS: exit=0 elapsed=66.2s
[2026-03-22 21:02:51]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt53
[2026-03-22 21:02:54]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 21:02:54]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:02:54]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:03:37]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 21:03:37]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:03:37] 
============================================================
[2026-03-22 21:03:37] STABILITY: openai_gpt53
[2026-03-22 21:03:37] ============================================================
[2026-03-22 21:03:37]   --- Repetition 1/3 ---
[2026-03-22 21:03:37]   SKIP: already converted (<cached output>)
[2026-03-22 21:03:37]   SKIP: already converted (<cached output>)
[2026-03-22 21:03:37]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt53
[2026-03-22 21:04:05]   SUCCESS: exit=0 elapsed=28.3s
[2026-03-22 21:04:05]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 21:05:07]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 21:05:07]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:05:07]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 21:05:28]   SUCCESS: exit=0 elapsed=157.2s
[2026-03-22 21:05:28]   SKIP: already converted (<cached output>)
[2026-03-22 21:05:28]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 21:06:30]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 21:06:30]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:06:30]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 21:12:54]   TIMEOUT after 600.0s
[2026-03-22 21:12:54]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:14:29]   SUCCESS: exit=0 elapsed=94.4s
[2026-03-22 21:14:29]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 21:15:30]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 21:15:30]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:15:30]   --- Repetition 2/3 ---
[2026-03-22 21:15:30]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:16:20]   SUCCESS: exit=0 elapsed=49.8s
[2026-03-22 21:16:20]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:18:29]   SUCCESS: exit=0 elapsed=128.7s
[2026-03-22 21:18:29]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:19:23]   SUCCESS: exit=0 elapsed=53.9s
[2026-03-22 21:19:23]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 21:20:25]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 21:20:25]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:20:25]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:20:43]   SUCCESS: exit=0 elapsed=936.0s
[2026-03-22 21:20:43]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt53
[2026-03-22 21:21:18]   SUCCESS: exit=0 elapsed=888.3s
[2026-03-22 21:21:18]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt53
[2026-03-22 21:22:59]   SUCCESS: exit=0 elapsed=135.4s
[2026-03-22 21:22:59]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 21:23:51]   SUCCESS: exit=0 elapsed=152.8s
[2026-03-22 21:23:51]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 21:24:01]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 21:24:01]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:24:01]   --- Repetition 2/3 ---
[2026-03-22 21:24:01]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 21:24:53]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 21:24:53]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:24:53]   --- Repetition 2/3 ---
[2026-03-22 21:24:53]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 21:25:04]   SUCCESS: exit=0 elapsed=63.0s
[2026-03-22 21:25:04]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt53
[2026-03-22 21:25:47]   SUCCESS: exit=0 elapsed=53.7s
[2026-03-22 21:25:47]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt53
[2026-03-22 21:27:38]   SUCCESS: exit=0 elapsed=111.7s
[2026-03-22 21:27:38]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt53
[2026-03-22 21:27:50]   SUCCESS: exit=0 elapsed=11.6s
[2026-03-22 21:27:50]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 21:28:14]   SUCCESS: exit=0 elapsed=190.2s
[2026-03-22 21:28:14]   SKIP: already converted (<cached output>)
[2026-03-22 21:28:14]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 21:28:52]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 21:28:52]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:28:52]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 21:29:16]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 21:29:16]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:29:16]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 21:29:36]   ERROR: exit=1 elapsed=20.0s
[2026-03-22 21:29:36]   STDERR: Errno 2] No such file or directory: '<workspace>/validation/runs/stability/rep2_openai_gpt53/SRC_12/.slides_tmp/slide-007.png'

[2026-03-22 21:29:36]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt53
[2026-03-22 21:30:23]   ERROR: exit=1 elapsed=91.6s
[2026-03-22 21:30:23]   STDERR: or: [Errno 2] No such file or directory: '<workspace>/validation/runs/stability/rep2_openai_gpt53/SRC_12/slides/slide-007.png'

[2026-03-22 21:30:23]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt53
[2026-03-22 21:30:25]   TIMEOUT after 600.0s
[2026-03-22 21:30:25]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:31:45]   SUCCESS: exit=0 elapsed=129.5s
[2026-03-22 21:31:45]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 21:32:18]   SUCCESS: exit=0 elapsed=113.5s
[2026-03-22 21:32:18]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 21:32:40]   SUCCESS: exit=0 elapsed=136.6s
[2026-03-22 21:32:40]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 21:32:47]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 21:32:47]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:32:47]   --- Repetition 3/3 ---
[2026-03-22 21:32:47]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 21:33:20]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 21:33:20]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:33:20]   --- Repetition 3/3 ---
[2026-03-22 21:33:20]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:33:42]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 21:33:42]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:33:42]   --- Repetition 3/3 ---
[2026-03-22 21:33:42]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 21:33:52]   SUCCESS: exit=0 elapsed=65.1s
[2026-03-22 21:33:52]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt53
[2026-03-22 21:34:12]   SUCCESS: exit=0 elapsed=52.2s
[2026-03-22 21:34:12]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:34:35]   SUCCESS: exit=0 elapsed=53.5s
[2026-03-22 21:34:35]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt53
[2026-03-22 21:35:17]   SUCCESS: exit=0 elapsed=64.9s
[2026-03-22 21:35:17]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:36:12]   SUCCESS: exit=0 elapsed=55.1s
[2026-03-22 21:36:12]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku45
[2026-03-22 21:36:23]   SUCCESS: exit=0 elapsed=107.5s
[2026-03-22 21:36:23]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt53
[2026-03-22 21:36:50]   SUCCESS: exit=0 elapsed=27.3s
[2026-03-22 21:36:50]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 21:36:54]   SUCCESS: exit=0 elapsed=181.3s
[2026-03-22 21:36:54]   SKIP: already converted (<cached output>)
[2026-03-22 21:36:54]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 21:37:14]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 21:37:14]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:37:14]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:37:52]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 21:37:52]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:37:52]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 21:37:56]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 21:37:56]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:37:56]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 21:38:37]   ERROR: exit=1 elapsed=41.3s
[2026-03-22 21:38:37]   STDERR: Errno 2] No such file or directory: '<workspace>/validation/runs/stability/rep3_openai_gpt53/SRC_12/.slides_tmp/slide-027.png'

[2026-03-22 21:38:37]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt53
[2026-03-22 21:40:56]   SUCCESS: exit=0 elapsed=139.4s
[2026-03-22 21:40:56]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 21:41:58]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 21:41:58]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:41:58] 
============================================================
[2026-03-22 21:41:58] STABILITY: openai_gpt41
[2026-03-22 21:41:58] ============================================================
[2026-03-22 21:41:58]   --- Repetition 1/3 ---
[2026-03-22 21:41:58]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41
[2026-03-22 21:43:32]   SUCCESS: exit=0 elapsed=93.8s
[2026-03-22 21:43:32]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41
[2026-03-22 21:45:53]   SUCCESS: exit=0 elapsed=141.4s
[2026-03-22 21:45:53]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41
[2026-03-22 21:46:16]   SUCCESS: exit=0 elapsed=23.0s
[2026-03-22 21:46:16]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 21:47:14]   TIMEOUT after 600.0s
[2026-03-22 21:47:14]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku45
[2026-03-22 21:47:18]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 21:47:18]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:47:18]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 21:48:56]   SUCCESS: exit=0 elapsed=101.9s
[2026-03-22 21:48:56]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku45
[2026-03-22 21:49:57]   ERROR: exit=1 elapsed=61.4s
[2026-03-22 21:49:57]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:49:57] 
============================================================
[2026-03-22 21:49:57] STABILITY: anthropic_haiku3
[2026-03-22 21:49:57] ============================================================
[2026-03-22 21:49:57]   --- Repetition 1/3 ---
[2026-03-22 21:49:57]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku3
[2026-03-22 21:50:18]   SUCCESS: exit=0 elapsed=21.0s
[2026-03-22 21:50:18]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku3
[2026-03-22 21:50:28]   SUCCESS: exit=0 elapsed=9.7s
[2026-03-22 21:50:28]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku3
[2026-03-22 21:50:33]   SUCCESS: exit=0 elapsed=4.8s
[2026-03-22 21:50:33]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 21:51:35]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 21:51:35]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:51:35]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku3
[2026-03-22 21:52:29]   SUCCESS: exit=0 elapsed=876.9s
[2026-03-22 21:52:29]   SKIP: already converted (<cached output>)
[2026-03-22 21:52:29]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 21:53:31]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 21:53:31]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:53:31] 
============================================================
[2026-03-22 21:53:31] STABILITY: openai_gpt41
[2026-03-22 21:53:31] ============================================================
[2026-03-22 21:53:31]   --- Repetition 1/3 ---
[2026-03-22 21:53:31]   SKIP: already converted (<cached output>)
[2026-03-22 21:53:31]   SKIP: already converted (<cached output>)
[2026-03-22 21:53:31]   SKIP: already converted (<cached output>)
[2026-03-22 21:53:31]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 21:54:23]   SUCCESS: exit=0 elapsed=168.1s
[2026-03-22 21:54:23]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku3
[2026-03-22 21:54:33]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 21:54:33]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:54:33]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 21:55:35]   SUCCESS: exit=0 elapsed=72.2s
[2026-03-22 21:55:35]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 21:56:37]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 21:56:37]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 21:56:37]   --- Repetition 2/3 ---
[2026-03-22 21:56:37]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku3
[2026-03-22 21:57:00]   SUCCESS: exit=0 elapsed=23.7s
[2026-03-22 21:57:00]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku3
[2026-03-22 21:57:11]   SUCCESS: exit=0 elapsed=10.3s
[2026-03-22 21:57:11]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku3
[2026-03-22 21:57:16]   SUCCESS: exit=0 elapsed=5.4s
[2026-03-22 21:57:16]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 21:58:18]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 21:58:18]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 21:58:18]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku3
[2026-03-22 21:59:02]   SUCCESS: exit=0 elapsed=704.2s
[2026-03-22 21:59:02]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41
[2026-03-22 22:00:17]   SUCCESS: exit=0 elapsed=75.6s
[2026-03-22 22:00:17]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 22:01:05]   SUCCESS: exit=0 elapsed=167.5s
[2026-03-22 22:01:05]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku3
[2026-03-22 22:01:19]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 22:01:19]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:01:19]   --- Repetition 2/3 ---
[2026-03-22 22:01:19]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41
[2026-03-22 22:02:12]   SUCCESS: exit=0 elapsed=67.0s
[2026-03-22 22:02:12]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 22:03:00]   SUCCESS: exit=0 elapsed=101.3s
[2026-03-22 22:03:00]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41
[2026-03-22 22:03:14]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 22:03:14]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:03:14]   --- Repetition 3/3 ---
[2026-03-22 22:03:14]   CMD: folio convert SRC_01.pdf --llm-profile anthropic_haiku3
[2026-03-22 22:03:35]   SUCCESS: exit=0 elapsed=21.2s
[2026-03-22 22:03:35]   CMD: folio convert SRC_04.pdf --llm-profile anthropic_haiku3
[2026-03-22 22:03:44]   SUCCESS: exit=0 elapsed=9.3s
[2026-03-22 22:03:44]   CMD: folio convert SRC_05.pdf --llm-profile anthropic_haiku3
[2026-03-22 22:03:50]   SUCCESS: exit=0 elapsed=5.6s
[2026-03-22 22:03:50]   CMD: folio convert SRC_11.pptx --llm-profile anthropic_haiku3
[2026-03-22 22:04:52]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 22:04:52]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:04:52]   CMD: folio convert SRC_12.pdf --llm-profile anthropic_haiku3
[2026-03-22 22:05:03]   SUCCESS: exit=0 elapsed=122.3s
[2026-03-22 22:05:03]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41
[2026-03-22 22:05:27]   SUCCESS: exit=0 elapsed=24.2s
[2026-03-22 22:05:27]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 22:05:41]   SUCCESS: exit=0 elapsed=668.1s
[2026-03-22 22:05:41]   SKIP: already converted (<cached output>)
[2026-03-22 22:05:41]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 22:06:28]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 22:06:28]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:06:28]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 22:06:43]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 22:06:43]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:06:43]   --- Repetition 2/3 ---
[2026-03-22 22:06:43]   SKIP: already converted (<cached output>)
[2026-03-22 22:06:43]   SKIP: already converted (<cached output>)
[2026-03-22 22:06:43]   SKIP: already converted (<cached output>)
[2026-03-22 22:06:43]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 22:07:43]   SUCCESS: exit=0 elapsed=171.0s
[2026-03-22 22:07:43]   CMD: folio convert SRC_15.pdf --llm-profile anthropic_haiku3
[2026-03-22 22:07:45]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 22:07:45]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:07:45]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 22:08:47]   SUCCESS: exit=0 elapsed=63.8s
[2026-03-22 22:08:47]   CMD: folio convert SRC_16.pptx --llm-profile anthropic_haiku3
[2026-03-22 22:09:48]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 22:09:48]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:09:48] 
============================================================
[2026-03-22 22:09:48] STABILITY: openai_gpt53
[2026-03-22 22:09:48] ============================================================
[2026-03-22 22:09:48]   --- Repetition 1/3 ---
[2026-03-22 22:09:48]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 22:11:05]   SUCCESS: exit=0 elapsed=76.7s
[2026-03-22 22:11:05]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt53
[2026-03-22 22:14:33]   SUCCESS: exit=0 elapsed=208.4s
[2026-03-22 22:14:33]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt53
[2026-03-22 22:14:53]   SUCCESS: exit=0 elapsed=19.4s
[2026-03-22 22:14:53]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 22:15:54]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 22:15:54]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:15:54]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 22:18:11]   SUCCESS: exit=0 elapsed=702.1s
[2026-03-22 22:18:11]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41
[2026-03-22 22:19:39]   SUCCESS: exit=0 elapsed=88.1s
[2026-03-22 22:19:39]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 22:20:13]   SUCCESS: exit=0 elapsed=748.8s
[2026-03-22 22:20:13]   SKIP: already converted (<cached output>)
[2026-03-22 22:20:13]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 22:20:40]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 22:20:40]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:20:40]   --- Repetition 3/3 ---
[2026-03-22 22:20:40]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41
[2026-03-22 22:21:15]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 22:21:15]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:21:15]   --- Repetition 3/3 ---
[2026-03-22 22:21:15]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41
[2026-03-22 22:22:28]   SUCCESS: exit=0 elapsed=107.5s
[2026-03-22 22:22:28]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41
[2026-03-22 22:22:44]   SUCCESS: exit=0 elapsed=89.1s
[2026-03-22 22:22:44]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41
[2026-03-22 22:25:11]   SUCCESS: exit=0 elapsed=146.7s
[2026-03-22 22:25:11]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41
[2026-03-22 22:25:36]   SUCCESS: exit=0 elapsed=24.6s
[2026-03-22 22:25:36]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 22:25:46]   SUCCESS: exit=0 elapsed=198.3s
[2026-03-22 22:25:46]   SKIP: already converted (<cached output>)
[2026-03-22 22:25:46]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 22:25:55]   TIMEOUT after 600.7s
[2026-03-22 22:25:55]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt53
[2026-03-22 22:26:37]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 22:26:37]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:26:37]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 22:26:47]   ERROR: exit=1 elapsed=61.3s
[2026-03-22 22:26:47]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:26:47]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 22:26:48]   ERROR: exit=1 elapsed=10.7s
[2026-03-22 22:26:48]   STDERR: Errno 2] No such file or directory: '<workspace>/validation/runs/stability/rep3_openai_gpt41/SRC_12/.slides_tmp/slide-007.png'

[2026-03-22 22:26:48]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41
[2026-03-22 22:28:13]   SUCCESS: exit=0 elapsed=84.8s
[2026-03-22 22:28:13]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 22:29:14]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 22:29:14]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:29:14] 
============================================================
[2026-03-22 22:29:14] STABILITY: openai_gpt41mini
[2026-03-22 22:29:14] ============================================================
[2026-03-22 22:29:14]   --- Repetition 1/3 ---
[2026-03-22 22:29:14]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41mini
[2026-03-22 22:30:02]   SUCCESS: exit=0 elapsed=247.1s
[2026-03-22 22:30:02]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 22:31:04]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 22:31:04]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:31:04]   --- Repetition 2/3 ---
[2026-03-22 22:31:04]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 22:32:29]   SUCCESS: exit=0 elapsed=84.7s
[2026-03-22 22:32:29]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt53
[2026-03-22 22:32:55]   SUCCESS: exit=0 elapsed=220.6s
[2026-03-22 22:32:55]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41mini
[2026-03-22 22:35:46]   SUCCESS: exit=0 elapsed=197.1s
[2026-03-22 22:35:46]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt53
[2026-03-22 22:36:31]   SUCCESS: exit=0 elapsed=45.0s
[2026-03-22 22:36:31]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 22:37:32]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 22:37:32]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:37:32]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 22:39:16]   SUCCESS: exit=0 elapsed=381.0s
[2026-03-22 22:39:16]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41mini
[2026-03-22 22:39:34]   SUCCESS: exit=0 elapsed=18.3s
[2026-03-22 22:39:34]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-22 22:40:36]   ERROR: exit=1 elapsed=62.0s
[2026-03-22 22:40:36]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:40:36]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-22 22:43:01]   SUCCESS: exit=0 elapsed=974.0s
[2026-03-22 22:43:01]   SKIP: already converted (<cached output>)
[2026-03-22 22:43:01]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 22:44:03]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 22:44:03]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:44:03] 
============================================================
[2026-03-22 22:44:03] STABILITY: openai_gpt41mini
[2026-03-22 22:44:03] ============================================================
[2026-03-22 22:44:03]   --- Repetition 1/3 ---
[2026-03-22 22:44:03]   SKIP: already converted (<cached output>)
[2026-03-22 22:44:03]   SKIP: already converted (<cached output>)
[2026-03-22 22:44:03]   SKIP: already converted (<cached output>)
[2026-03-22 22:44:03]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-22 22:45:05]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 22:45:05]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:45:05]   SKIP: already converted (<cached output>)
[2026-03-22 22:45:05]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41mini
[2026-03-22 22:47:05]   SUCCESS: exit=0 elapsed=120.2s
[2026-03-22 22:47:05]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-22 22:47:32]   TIMEOUT after 600.0s
[2026-03-22 22:47:32]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt53
[2026-03-22 22:48:07]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 22:48:07]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:48:07]   --- Repetition 2/3 ---
[2026-03-22 22:48:07]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41mini
[2026-03-22 22:49:38]   SUCCESS: exit=0 elapsed=91.6s
[2026-03-22 22:49:38]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41mini
[2026-03-22 22:49:43]   SUCCESS: exit=0 elapsed=130.4s
[2026-03-22 22:49:43]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 22:50:44]   ERROR: exit=1 elapsed=61.5s
[2026-03-22 22:50:44]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:50:44]   --- Repetition 3/3 ---
[2026-03-22 22:50:44]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt53
[2026-03-22 22:51:42]   SUCCESS: exit=0 elapsed=57.5s
[2026-03-22 22:51:42]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt53
[2026-03-22 22:53:14]   SUCCESS: exit=0 elapsed=92.7s
[2026-03-22 22:53:14]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt53
[2026-03-22 22:53:40]   SUCCESS: exit=0 elapsed=241.5s
[2026-03-22 22:53:40]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41mini
[2026-03-22 22:53:41]   SUCCESS: exit=0 elapsed=26.0s
[2026-03-22 22:53:41]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt53
[2026-03-22 22:54:01]   SUCCESS: exit=0 elapsed=21.6s
[2026-03-22 22:54:01]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-22 22:54:42]   ERROR: exit=1 elapsed=61.4s
[2026-03-22 22:54:42]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:54:42]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt53
[2026-03-22 22:55:03]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 22:55:03]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:55:03]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-22 22:56:00]   SUCCESS: exit=0 elapsed=923.7s
[2026-03-22 22:56:00]   SKIP: already converted (<cached output>)
[2026-03-22 22:56:00]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-22 22:57:02]   ERROR: exit=1 elapsed=62.1s
[2026-03-22 22:57:02]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 22:57:02]   --- Repetition 2/3 ---
[2026-03-22 22:57:02]   SKIP: already converted (<cached output>)
[2026-03-22 22:57:02]   SKIP: already converted (<cached output>)
[2026-03-22 22:57:02]   SKIP: already converted (<cached output>)
[2026-03-22 22:57:02]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-22 22:58:04]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 22:58:04]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 22:58:04]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:04:42]   TIMEOUT after 600.0s
[2026-03-22 23:04:42]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt53
[2026-03-22 23:06:55]   SUCCESS: exit=0 elapsed=132.7s
[2026-03-22 23:06:55]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt53
[2026-03-22 23:07:57]   ERROR: exit=1 elapsed=62.3s
[2026-03-22 23:07:57]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 23:07:57] 
============================================================
[2026-03-22 23:07:57] STABILITY: openai_gpt41
[2026-03-22 23:07:57] ============================================================
[2026-03-22 23:07:57]   --- Repetition 1/3 ---
[2026-03-22 23:07:57]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41
[2026-03-22 23:09:37]   SUCCESS: exit=0 elapsed=100.3s
[2026-03-22 23:09:37]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41
[2026-03-22 23:11:35]   SUCCESS: exit=0 elapsed=117.7s
[2026-03-22 23:11:35]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41
[2026-03-22 23:11:47]   SUCCESS: exit=0 elapsed=1003.7s
[2026-03-22 23:11:47]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:11:53]   SUCCESS: exit=0 elapsed=18.3s
[2026-03-22 23:11:53]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 23:12:55]   ERROR: exit=1 elapsed=62.2s
[2026-03-22 23:12:55]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 23:12:55]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 23:13:41]   SUCCESS: exit=0 elapsed=113.9s
[2026-03-22 23:13:41]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-22 23:14:42]   ERROR: exit=1 elapsed=61.7s
[2026-03-22 23:14:42]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 23:14:42]   --- Repetition 3/3 ---
[2026-03-22 23:14:42]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:15:05]   SUCCESS: exit=0 elapsed=1020.9s
[2026-03-22 23:15:05]   SKIP: already converted (<cached output>)
[2026-03-22 23:15:05]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-22 23:16:06]   ERROR: exit=1 elapsed=61.8s
[2026-03-22 23:16:06]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 23:16:06]   --- Repetition 3/3 ---
[2026-03-22 23:16:06]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:16:14]   SUCCESS: exit=0 elapsed=92.1s
[2026-03-22 23:16:14]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:18:17]   SUCCESS: exit=0 elapsed=130.2s
[2026-03-22 23:18:17]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:20:30]   SUCCESS: exit=0 elapsed=255.5s
[2026-03-22 23:20:30]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:20:54]   SUCCESS: exit=0 elapsed=23.6s
[2026-03-22 23:20:54]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-22 23:22:00]   SUCCESS: exit=0 elapsed=223.3s
[2026-03-22 23:22:00]   SKIP: already converted (<cached output>)
[2026-03-22 23:22:00]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-22 23:22:16]   SUCCESS: exit=0 elapsed=82.5s
[2026-03-22 23:22:16]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:22:55]   TIMEOUT after 600.0s
[2026-03-22 23:22:55]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41
[2026-03-22 23:23:13]   SUCCESS: exit=0 elapsed=72.9s
[2026-03-22 23:23:13]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:24:18]   SUCCESS: exit=0 elapsed=82.2s
[2026-03-22 23:24:18]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 23:26:59]   SUCCESS: exit=0 elapsed=161.8s
[2026-03-22 23:26:59]   --- Repetition 2/3 ---
[2026-03-22 23:26:59]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41
[2026-03-22 23:28:35]   SUCCESS: exit=0 elapsed=95.3s
[2026-03-22 23:28:35]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41
[2026-03-22 23:30:23]   SUCCESS: exit=0 elapsed=108.2s
[2026-03-22 23:30:23]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41
[2026-03-22 23:30:44]   SUCCESS: exit=0 elapsed=20.9s
[2026-03-22 23:30:44]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 23:31:15]   SUCCESS: exit=0 elapsed=31.3s
[2026-03-22 23:31:15]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 23:38:42]   SUCCESS: exit=0 elapsed=986.5s
[2026-03-22 23:38:42]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:39:03]   SUCCESS: exit=0 elapsed=949.7s
[2026-03-22 23:39:03]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41mini
[2026-03-22 23:41:07]   SUCCESS: exit=0 elapsed=144.3s
[2026-03-22 23:41:07]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-22 23:41:15]   TIMEOUT after 600.0s
[2026-03-22 23:41:15]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41
[2026-03-22 23:41:17]   SUCCESS: exit=0 elapsed=134.7s
[2026-03-22 23:41:17]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-22 23:41:20]   ERROR: exit=1 elapsed=3.0s
[2026-03-22 23:41:20]   STDERR: b.pptx
  Normalizing to PDF...
✗ Conversion failed: Conversion completed but PDF not found at <powerpoint-staging>/SRC_16.pdf

[2026-03-22 23:41:20] 
============================================================
[2026-03-22 23:41:20] STABILITY: openai_gpt4o
[2026-03-22 23:41:20] ============================================================
[2026-03-22 23:41:20]   --- Repetition 1/3 ---
[2026-03-22 23:41:20]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4o
[2026-03-22 23:42:14]   SUCCESS: exit=0 elapsed=54.1s
[2026-03-22 23:42:14]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4o
[2026-03-22 23:42:29]   SUCCESS: exit=0 elapsed=73.8s
[2026-03-22 23:42:29]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-22 23:43:31]   ERROR: exit=1 elapsed=61.6s
[2026-03-22 23:43:31]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-22 23:43:31]   --- Repetition 3/3 ---
[2026-03-22 23:43:31]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41
[2026-03-22 23:44:24]   SUCCESS: exit=0 elapsed=129.2s
[2026-03-22 23:44:24]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4o
[2026-03-22 23:44:35]   SUCCESS: exit=0 elapsed=11.4s
[2026-03-22 23:44:35]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-22 23:45:24]   SUCCESS: exit=0 elapsed=113.1s
[2026-03-22 23:45:24]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41
[2026-03-22 23:45:37]   ERROR: exit=1 elapsed=61.9s
[2026-03-22 23:45:37]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-22 23:45:37]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-22 23:48:20]   SUCCESS: exit=0 elapsed=176.2s
[2026-03-22 23:48:20]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41
[2026-03-22 23:48:51]   SUCCESS: exit=0 elapsed=31.2s
[2026-03-22 23:48:51]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41
[2026-03-22 23:49:33]   SUCCESS: exit=0 elapsed=42.2s
[2026-03-22 23:49:33]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41
[2026-03-22 23:49:39]   SUCCESS: exit=0 elapsed=512.5s
[2026-03-22 23:49:39] 
============================================================
[2026-03-22 23:49:39] STABILITY: openai_gpt4o
[2026-03-22 23:49:39] ============================================================
[2026-03-22 23:49:39]   --- Repetition 1/3 ---
[2026-03-22 23:49:39]   SKIP: already converted (<cached output>)
[2026-03-22 23:49:39]   SKIP: already converted (<cached output>)
[2026-03-22 23:49:39]   SKIP: already converted (<cached output>)
[2026-03-22 23:49:39]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-22 23:50:10]   SUCCESS: exit=0 elapsed=30.7s
[2026-03-22 23:50:10]   SKIP: already converted (<cached output>)
[2026-03-22 23:50:10]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4o
[2026-03-22 23:51:05]   SUCCESS: exit=0 elapsed=54.8s
[2026-03-22 23:51:05]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4o
[2026-03-22 23:52:24]   SUCCESS: exit=0 elapsed=78.8s
[2026-03-22 23:52:24]   --- Repetition 2/3 ---
[2026-03-22 23:52:24]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4o
[2026-03-22 23:53:15]   SUCCESS: exit=0 elapsed=51.0s
[2026-03-22 23:53:15]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4o
[2026-03-22 23:53:34]   SUCCESS: exit=0 elapsed=477.0s
[2026-03-22 23:53:34]   SKIP: already converted (<cached output>)
[2026-03-22 23:53:34]   SKIP: already converted (<cached output>)
[2026-03-22 23:53:34]   --- Repetition 2/3 ---
[2026-03-22 23:53:34]   SKIP: already converted (<cached output>)
[2026-03-22 23:53:34]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4o
[2026-03-22 23:55:02]   SUCCESS: exit=0 elapsed=107.4s
[2026-03-22 23:55:02]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4o
[2026-03-22 23:55:10]   SUCCESS: exit=0 elapsed=96.5s
[2026-03-22 23:55:10]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4o
[2026-03-22 23:55:14]   SUCCESS: exit=0 elapsed=11.9s
[2026-03-22 23:55:14]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-22 23:55:22]   SUCCESS: exit=0 elapsed=11.3s
[2026-03-22 23:55:22]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-22 23:55:46]   SUCCESS: exit=0 elapsed=32.3s
[2026-03-22 23:55:46]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-22 23:55:55]   SUCCESS: exit=0 elapsed=33.7s
[2026-03-22 23:55:55]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-22 23:56:09]   ERROR: exit=1 elapsed=13.3s
[2026-03-22 23:56:09]   STDERR: Errno 2] No such file or directory: '<workspace>/validation/runs/stability/rep2_openai_gpt4o/SRC_12/.slides_tmp/slide-017.png'

[2026-03-22 23:56:09]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4o
[2026-03-22 23:57:00]   SUCCESS: exit=0 elapsed=51.5s
[2026-03-22 23:57:00]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4o
[2026-03-22 23:59:20]   SUCCESS: exit=0 elapsed=140.1s
[2026-03-22 23:59:20]   --- Repetition 3/3 ---
[2026-03-22 23:59:20]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4o
[2026-03-22 23:59:33]   TIMEOUT after 600.0s
[2026-03-22 23:59:33]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41
[2026-03-23 00:00:18]   SUCCESS: exit=0 elapsed=57.5s
[2026-03-23 00:00:18]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4o
[2026-03-23 00:00:56]   SUCCESS: exit=0 elapsed=82.4s
[2026-03-23 00:00:56]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41
[2026-03-23 00:02:33]   SUCCESS: exit=0 elapsed=134.7s
[2026-03-23 00:02:33]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4o
[2026-03-23 00:02:36]   SUCCESS: exit=0 elapsed=409.4s
[2026-03-23 00:02:36]   SKIP: already converted (<cached output>)
[2026-03-23 00:02:36]   SKIP: already converted (<cached output>)
[2026-03-23 00:02:36]   --- Repetition 3/3 ---
[2026-03-23 00:02:36]   SKIP: already converted (<cached output>)
[2026-03-23 00:02:36]   SKIP: already converted (<cached output>)
[2026-03-23 00:02:36]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4o
[2026-03-23 00:02:36]   ERROR: exit=1 elapsed=3.3s
[2026-03-23 00:02:36]   STDERR: or: [Errno 2] No such file or directory: '<workspace>/validation/runs/stability/rep3_openai_gpt4o/SRC_05/slides/slide-001.png'

[2026-03-23 00:02:36]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-23 00:02:49]   SUCCESS: exit=0 elapsed=13.0s
[2026-03-23 00:02:49]   SKIP: already converted (<cached output>)
[2026-03-23 00:02:49]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-23 00:03:13]   SUCCESS: exit=0 elapsed=36.7s
[2026-03-23 00:03:13]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-23 00:04:58]   SUCCESS: exit=0 elapsed=242.3s
[2026-03-23 00:04:58] 
============================================================
[2026-03-23 00:04:58] STABILITY: openai_gpt41mini
[2026-03-23 00:04:58] ============================================================
[2026-03-23 00:04:58]   --- Repetition 1/3 ---
[2026-03-23 00:04:58]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:06:48]   SUCCESS: exit=0 elapsed=110.2s
[2026-03-23 00:06:48]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:09:17]   SUCCESS: exit=0 elapsed=388.2s
[2026-03-23 00:09:17]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4o
[2026-03-23 00:10:21]   SUCCESS: exit=0 elapsed=64.1s
[2026-03-23 00:10:21]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4o
[2026-03-23 00:10:30]   SUCCESS: exit=0 elapsed=437.8s
[2026-03-23 00:10:30]   SKIP: already converted (<cached output>)
[2026-03-23 00:10:30]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4o
[2026-03-23 00:12:45]   SUCCESS: exit=0 elapsed=356.5s
[2026-03-23 00:12:45]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:12:53]   SUCCESS: exit=0 elapsed=152.1s
[2026-03-23 00:12:53] 
============================================================
[2026-03-23 00:12:53] STABILITY: openai_gpt4omini
[2026-03-23 00:12:53] ============================================================
[2026-03-23 00:12:53]   --- Repetition 1/3 ---
[2026-03-23 00:12:53]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:13:09]   SUCCESS: exit=0 elapsed=24.6s
[2026-03-23 00:13:09]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-23 00:13:10]   SUCCESS: exit=0 elapsed=159.4s
[2026-03-23 00:13:10] 
============================================================
[2026-03-23 00:13:10] STABILITY: openai_gpt4omini
[2026-03-23 00:13:10] ============================================================
[2026-03-23 00:13:10]   --- Repetition 1/3 ---
[2026-03-23 00:13:10]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:14:04]   SUCCESS: exit=0 elapsed=53.9s
[2026-03-23 00:14:04]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:14:21]   SUCCESS: exit=0 elapsed=72.1s
[2026-03-23 00:14:21]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:15:10]   SUCCESS: exit=0 elapsed=137.1s
[2026-03-23 00:15:10]   SKIP: already converted (<cached output>)
[2026-03-23 00:15:10]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:15:19]   SUCCESS: exit=0 elapsed=9.2s
[2026-03-23 00:15:19]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4omini
[2026-03-23 00:16:16]   SUCCESS: exit=0 elapsed=132.1s
[2026-03-23 00:16:16]   SKIP: already converted (<cached output>)
[2026-03-23 00:16:16]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4omini
[2026-03-23 00:17:34]   SUCCESS: exit=0 elapsed=134.6s
[2026-03-23 00:17:34]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:18:10]   SUCCESS: exit=0 elapsed=114.2s
[2026-03-23 00:18:10]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:24:21]   TIMEOUT after 600.0s
[2026-03-23 00:24:21]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:26:43]   SUCCESS: exit=0 elapsed=141.6s
[2026-03-23 00:26:43]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-23 00:30:39]   SUCCESS: exit=0 elapsed=235.7s
[2026-03-23 00:30:39]   --- Repetition 2/3 ---
[2026-03-23 00:30:39]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:32:03]   SUCCESS: exit=0 elapsed=84.5s
[2026-03-23 00:32:03]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:38:46]   SUCCESS: exit=0 elapsed=402.4s
[2026-03-23 00:38:46]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:39:24]   SUCCESS: exit=0 elapsed=38.2s
[2026-03-23 00:39:24]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-23 00:40:30]   SUCCESS: exit=0 elapsed=66.6s
[2026-03-23 00:40:30]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:47:34]   TIMEOUT after 1800.0s
[2026-03-23 00:47:34]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:48:10]   TIMEOUT after 1800.0s
[2026-03-23 00:48:10]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:48:43]   SUCCESS: exit=0 elapsed=68.6s
[2026-03-23 00:48:43]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-23 00:49:23]   SUCCESS: exit=0 elapsed=73.1s
[2026-03-23 00:49:23]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-23 00:50:30]   TIMEOUT after 600.0s
[2026-03-23 00:50:30]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:52:47]   SUCCESS: exit=0 elapsed=137.0s
[2026-03-23 00:52:47]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-23 00:56:28]   SUCCESS: exit=0 elapsed=465.5s
[2026-03-23 00:56:28]   --- Repetition 2/3 ---
[2026-03-23 00:56:28]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:56:56]   SUCCESS: exit=0 elapsed=27.5s
[2026-03-23 00:56:56]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:57:16]   SUCCESS: exit=0 elapsed=472.5s
[2026-03-23 00:57:16]   --- Repetition 2/3 ---
[2026-03-23 00:57:16]   SKIP: already converted (<cached output>)
[2026-03-23 00:57:16]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:58:13]   SUCCESS: exit=0 elapsed=56.8s
[2026-03-23 00:58:13]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:58:21]   SUCCESS: exit=0 elapsed=8.0s
[2026-03-23 00:58:21]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4omini
[2026-03-23 00:58:41]   SUCCESS: exit=0 elapsed=353.4s
[2026-03-23 00:58:41]   --- Repetition 3/3 ---
[2026-03-23 00:58:41]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt41mini
[2026-03-23 00:58:41]   SUCCESS: exit=0 elapsed=105.7s
[2026-03-23 00:58:41]   SKIP: already converted (<cached output>)
[2026-03-23 00:58:41]   SKIP: already converted (<cached output>)
[2026-03-23 00:58:41]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-23 00:59:08]   SUCCESS: exit=0 elapsed=47.3s
[2026-03-23 00:59:08]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-23 01:00:23]   SUCCESS: exit=0 elapsed=102.2s
[2026-03-23 01:00:23]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt41mini
[2026-03-23 01:04:10]   SUCCESS: exit=0 elapsed=227.0s
[2026-03-23 01:04:10]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt41mini
[2026-03-23 01:06:27]   SUCCESS: exit=0 elapsed=136.6s
[2026-03-23 01:06:27]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt41mini
[2026-03-23 01:07:32]   SUCCESS: exit=0 elapsed=65.3s
[2026-03-23 01:07:32]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt41mini
[2026-03-23 01:17:32]   TIMEOUT after 600.0s
[2026-03-23 01:17:32]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt41mini
[2026-03-23 01:20:07]   SUCCESS: exit=0 elapsed=155.0s
[2026-03-23 01:20:07]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt41mini
[2026-03-23 01:28:08]   SUCCESS: exit=0 elapsed=480.8s
[2026-03-23 01:28:08] 
============================================================
[2026-03-23 01:28:08] STABILITY: openai_gpt4o
[2026-03-23 01:28:08] ============================================================
[2026-03-23 01:28:08]   --- Repetition 1/3 ---
[2026-03-23 01:28:08]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4o
[2026-03-23 01:28:41]   TIMEOUT after 1800.0s
[2026-03-23 01:28:41]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4omini
[2026-03-23 01:29:03]   SUCCESS: exit=0 elapsed=54.9s
[2026-03-23 01:29:03]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4o
[2026-03-23 01:29:08]   TIMEOUT after 1800.0s
[2026-03-23 01:29:08]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4omini
[2026-03-23 01:29:47]   SUCCESS: exit=0 elapsed=66.1s
[2026-03-23 01:29:47]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-23 01:30:09]   SUCCESS: exit=0 elapsed=60.7s
[2026-03-23 01:30:09]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-23 01:30:55]   SUCCESS: exit=0 elapsed=112.2s
[2026-03-23 01:30:55]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4o
[2026-03-23 01:31:06]   SUCCESS: exit=0 elapsed=10.8s
[2026-03-23 01:31:06]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-23 01:31:39]   SUCCESS: exit=0 elapsed=33.3s
[2026-03-23 01:31:39]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-23 01:37:46]   SUCCESS: exit=0 elapsed=478.2s
[2026-03-23 01:37:46]   --- Repetition 3/3 ---
[2026-03-23 01:37:46]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4omini
[2026-03-23 01:37:46]   SUCCESS: exit=0 elapsed=457.9s
[2026-03-23 01:37:46]   --- Repetition 3/3 ---
[2026-03-23 01:37:46]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4omini
[2026-03-23 01:37:49]   ERROR: exit=1 elapsed=2.6s
[2026-03-23 01:37:49]   STDERR: age rendering failed: [Errno 17] File exists: '<workspace>/validation/runs/stability/rep3_openai_gpt4omini/SRC_01/.slides_tmp'

[2026-03-23 01:37:49]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4omini
[2026-03-23 01:37:50]   ERROR: exit=1 elapsed=4.7s
[2026-03-23 01:37:50]   STDERR: o 2] No such file or directory: '<workspace>/validation/runs/stability/rep3_openai_gpt4omini/SRC_01/.slides_tmp/slide-005.png'

[2026-03-23 01:37:50]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4omini
[2026-03-23 01:37:50]   ERROR: exit=1 elapsed=1.5s
[2026-03-23 01:37:50]   STDERR: o 2] No such file or directory: '<workspace>/validation/runs/stability/rep3_openai_gpt4omini/SRC_04/.slides_tmp/slide-001.png'

[2026-03-23 01:37:50]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4omini
[2026-03-23 01:37:59]   SUCCESS: exit=0 elapsed=8.8s
[2026-03-23 01:37:59]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4omini
[2026-03-23 01:38:35]   SUCCESS: exit=0 elapsed=415.5s
[2026-03-23 01:38:35]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4o
[2026-03-23 01:39:18]   SUCCESS: exit=0 elapsed=87.1s
[2026-03-23 01:39:18]   SKIP: already converted (<cached output>)
[2026-03-23 01:39:18]   SKIP: already converted (<cached output>)
[2026-03-23 01:39:18]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-23 01:39:37]   SUCCESS: exit=0 elapsed=62.3s
[2026-03-23 01:39:37]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4o
[2026-03-23 01:39:53]   SUCCESS: exit=0 elapsed=113.7s
[2026-03-23 01:39:53]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-23 01:42:17]   SUCCESS: exit=0 elapsed=160.6s
[2026-03-23 01:42:17]   --- Repetition 2/3 ---
[2026-03-23 01:42:17]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4o
[2026-03-23 01:43:08]   SUCCESS: exit=0 elapsed=50.8s
[2026-03-23 01:43:08]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4o
[2026-03-23 01:45:05]   SUCCESS: exit=0 elapsed=116.5s
[2026-03-23 01:45:05]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4o
[2026-03-23 01:45:16]   SUCCESS: exit=0 elapsed=11.1s
[2026-03-23 01:45:16]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-23 01:45:53]   SUCCESS: exit=0 elapsed=37.6s
[2026-03-23 01:45:53]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-23 01:51:25]   SUCCESS: exit=0 elapsed=331.1s
[2026-03-23 01:51:25]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4o
[2026-03-23 01:52:23]   SUCCESS: exit=0 elapsed=58.3s
[2026-03-23 01:52:23]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4o
[2026-03-23 01:54:56]   SUCCESS: exit=0 elapsed=153.2s
[2026-03-23 01:54:56]   --- Repetition 3/3 ---
[2026-03-23 01:54:56]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4o
[2026-03-23 01:55:49]   SUCCESS: exit=0 elapsed=53.0s
[2026-03-23 01:55:49]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4o
[2026-03-23 01:58:24]   SUCCESS: exit=0 elapsed=155.3s
[2026-03-23 01:58:24]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4o
[2026-03-23 01:58:35]   SUCCESS: exit=0 elapsed=11.1s
[2026-03-23 01:58:35]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4o
[2026-03-23 01:59:09]   SUCCESS: exit=0 elapsed=33.4s
[2026-03-23 01:59:09]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4o
[2026-03-23 02:05:53]   SUCCESS: exit=0 elapsed=404.7s
[2026-03-23 02:05:53]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4o
[2026-03-23 02:07:07]   SUCCESS: exit=0 elapsed=73.4s
[2026-03-23 02:07:07]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4o
[2026-03-23 02:09:18]   TIMEOUT after 1800.0s
[2026-03-23 02:09:18]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:09:52]   SUCCESS: exit=0 elapsed=164.9s
[2026-03-23 02:09:52] 
============================================================
[2026-03-23 02:09:52] STABILITY: openai_gpt4omini
[2026-03-23 02:09:52] ============================================================
[2026-03-23 02:09:52]   --- Repetition 1/3 ---
[2026-03-23 02:09:52]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:09:53]   TIMEOUT after 1800.0s
[2026-03-23 02:09:53]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:10:31]   SUCCESS: exit=0 elapsed=39.1s
[2026-03-23 02:10:31]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:10:40]   SUCCESS: exit=0 elapsed=82.8s
[2026-03-23 02:10:40]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-23 02:11:28]   SUCCESS: exit=0 elapsed=94.5s
[2026-03-23 02:11:28]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-23 02:14:10]   SUCCESS: exit=0 elapsed=218.7s
[2026-03-23 02:14:10]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:14:18]   SUCCESS: exit=0 elapsed=7.9s
[2026-03-23 02:14:18]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4omini
[2026-03-23 02:17:41]   SUCCESS: exit=0 elapsed=203.5s
[2026-03-23 02:17:41]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:19:20]   SUCCESS: exit=0 elapsed=519.4s
[2026-03-23 02:19:20] 
============================================================
[2026-03-23 02:19:20] STABILITY: openai_gpt4turbo
[2026-03-23 02:19:20] ============================================================
[2026-03-23 02:19:20]   --- Repetition 1/3 ---
[2026-03-23 02:19:20]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:19:36]   SUCCESS: exit=0 elapsed=15.9s
[2026-03-23 02:19:36]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:19:43]   SUCCESS: exit=0 elapsed=7.6s
[2026-03-23 02:19:43]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:19:48]   SUCCESS: exit=0 elapsed=5.2s
[2026-03-23 02:19:48]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4turbo
[2026-03-23 02:20:01]   SUCCESS: exit=0 elapsed=12.2s
[2026-03-23 02:20:01]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:20:51]   SUCCESS: exit=0 elapsed=563.4s
[2026-03-23 02:20:51] 
============================================================
[2026-03-23 02:20:51] STABILITY: openai_gpt4turbo
[2026-03-23 02:20:51] ============================================================
[2026-03-23 02:20:51]   --- Repetition 1/3 ---
[2026-03-23 02:20:51]   SKIP: already converted (<cached output>)
[2026-03-23 02:20:51]   SKIP: already converted (<cached output>)
[2026-03-23 02:20:51]   SKIP: already converted (<cached output>)
[2026-03-23 02:20:51]   SKIP: already converted (<cached output>)
[2026-03-23 02:20:51]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:20:57]   SUCCESS: exit=0 elapsed=56.3s
[2026-03-23 02:20:57]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:21:16]   SUCCESS: exit=0 elapsed=18.9s
[2026-03-23 02:21:16]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4turbo
[2026-03-23 02:21:40]   SUCCESS: exit=0 elapsed=24.1s
[2026-03-23 02:21:40]   --- Repetition 2/3 ---
[2026-03-23 02:21:40]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:21:48]   SUCCESS: exit=0 elapsed=57.4s
[2026-03-23 02:21:48]   SKIP: already converted (<cached output>)
[2026-03-23 02:21:48]   SKIP: already converted (<cached output>)
[2026-03-23 02:21:48]   --- Repetition 2/3 ---
[2026-03-23 02:21:48]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:21:52]   SUCCESS: exit=0 elapsed=12.1s
[2026-03-23 02:21:52]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:21:59]   SUCCESS: exit=0 elapsed=7.5s
[2026-03-23 02:21:59]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:22:01]   SUCCESS: exit=0 elapsed=12.3s
[2026-03-23 02:22:01]   SKIP: already converted (<cached output>)
[2026-03-23 02:22:01]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:22:04]   SUCCESS: exit=0 elapsed=4.6s
[2026-03-23 02:22:04]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4turbo
[2026-03-23 02:22:06]   SUCCESS: exit=0 elapsed=5.2s
[2026-03-23 02:22:06]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4turbo
[2026-03-23 02:22:07]   ERROR: exit=1 elapsed=2.7s
[2026-03-23 02:22:07]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Error: [Errno 2] No such file or directory: '<powerpoint-staging>/SRC_11.pdf'

[2026-03-23 02:22:07]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:22:14]   SUCCESS: exit=0 elapsed=8.4s
[2026-03-23 02:22:14]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:22:31]   ERROR: exit=1 elapsed=16.7s
[2026-03-23 02:22:31]   STDERR: o 2] No such file or directory: '<workspace>/validation/runs/stability/rep2_openai_gpt4turbo/SRC_12/.slides_tmp/slide-019.png'

[2026-03-23 02:22:31]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:22:49]   SUCCESS: exit=0 elapsed=18.3s
[2026-03-23 02:22:49]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4turbo
[2026-03-23 02:23:02]   SUCCESS: exit=0 elapsed=55.0s
[2026-03-23 02:23:02]   SKIP: already converted (<cached output>)
[2026-03-23 02:23:02]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4turbo
[2026-03-23 02:23:04]   ERROR: exit=1 elapsed=15.0s
[2026-03-23 02:23:04]   STDERR: b.pptx
  Normalizing to PDF...
✗ Conversion failed: Conversion completed but PDF not found at <powerpoint-staging>/SRC_16.pdf

[2026-03-23 02:23:04]   --- Repetition 3/3 ---
[2026-03-23 02:23:04]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:23:16]   SUCCESS: exit=0 elapsed=11.9s
[2026-03-23 02:23:16]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:23:23]   SUCCESS: exit=0 elapsed=21.6s
[2026-03-23 02:23:23]   --- Repetition 3/3 ---
[2026-03-23 02:23:23]   SKIP: already converted (<cached output>)
[2026-03-23 02:23:23]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:23:24]   ERROR: exit=1 elapsed=7.9s
[2026-03-23 02:23:24]   STDERR: [Errno 2] No such file or directory: '<workspace>/validation/runs/stability/rep3_openai_gpt4turbo/SRC_04/slides/slide-001.png'

[2026-03-23 02:23:24]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:23:29]   SUCCESS: exit=0 elapsed=4.6s
[2026-03-23 02:23:29]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4turbo
[2026-03-23 02:23:31]   SUCCESS: exit=0 elapsed=7.5s
[2026-03-23 02:23:31]   SKIP: already converted (<cached output>)
[2026-03-23 02:23:31]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4turbo
[2026-03-23 02:23:32]   ERROR: exit=1 elapsed=1.3s
[2026-03-23 02:23:32]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Error: [Errno 2] No such file or directory: '<powerpoint-staging>/SRC_11.pdf'

[2026-03-23 02:23:32]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:23:41]   SUCCESS: exit=0 elapsed=11.8s
[2026-03-23 02:23:41]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:23:54]   ERROR: exit=1 elapsed=13.6s
[2026-03-23 02:23:54]   STDERR: o 2] No such file or directory: '<workspace>/validation/runs/stability/rep3_openai_gpt4turbo/SRC_12/.slides_tmp/slide-017.png'

[2026-03-23 02:23:54]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4turbo
[2026-03-23 02:24:13]   SUCCESS: exit=0 elapsed=19.3s
[2026-03-23 02:24:13]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4turbo
[2026-03-23 02:24:30]   SUCCESS: exit=0 elapsed=57.5s
[2026-03-23 02:24:30]   SKIP: already converted (<cached output>)
[2026-03-23 02:24:30]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4turbo
[2026-03-23 02:24:30]   ERROR: exit=1 elapsed=16.6s
[2026-03-23 02:24:30]   STDERR: o 2] No such file or directory: '<workspace>/validation/runs/stability/rep3_openai_gpt4turbo/SRC_16/.slides_tmp/slide-001.png'

[2026-03-23 02:24:30] 
============================================================
[2026-03-23 02:24:30] STABILITY: google_gemini25pro
[2026-03-23 02:24:30] ============================================================
[2026-03-23 02:24:30]   --- Repetition 1/3 ---
[2026-03-23 02:24:30]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25pro
[2026-03-23 02:24:52]   SUCCESS: exit=0 elapsed=22.5s
[2026-03-23 02:24:52] 
============================================================
[2026-03-23 02:24:52] STABILITY: google_gemini25pro
[2026-03-23 02:24:52] ============================================================
[2026-03-23 02:24:52]   --- Repetition 1/3 ---
[2026-03-23 02:24:52]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25pro
[2026-03-23 02:27:41]   TIMEOUT after 600.0s
[2026-03-23 02:27:41]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:28:47]   SUCCESS: exit=0 elapsed=66.3s
[2026-03-23 02:28:47]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-23 02:32:37]   SUCCESS: exit=0 elapsed=465.1s
[2026-03-23 02:32:37]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25pro
[2026-03-23 02:32:39]   SUCCESS: exit=0 elapsed=488.5s
[2026-03-23 02:32:39]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25pro
[2026-03-23 02:33:03]   SUCCESS: exit=0 elapsed=26.0s
[2026-03-23 02:33:03]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-23 02:33:05]   SUCCESS: exit=0 elapsed=26.2s
[2026-03-23 02:33:05]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-23 02:33:06]   ERROR: exit=1 elapsed=1.7s
[2026-03-23 02:33:06]   STDERR: e rendering failed: [Errno 17] File exists: '<workspace>/validation/runs/stability/rep1_google_gemini25pro/SRC_05/.slides_tmp'

[2026-03-23 02:33:06]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25pro
[2026-03-23 02:33:08]   ERROR: exit=1 elapsed=4.5s
[2026-03-23 02:33:08]   STDERR: 2] No such file or directory: '<workspace>/validation/runs/stability/rep1_google_gemini25pro/SRC_05/.slides_tmp/slide-001.png'

[2026-03-23 02:33:08]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25pro
[2026-03-23 02:33:09]   ERROR: exit=1 elapsed=3.0s
[2026-03-23 02:33:09]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Error: [Errno 2] No such file or directory: '<powerpoint-staging>/SRC_11.pdf'

[2026-03-23 02:33:09]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-23 02:33:33]   SUCCESS: exit=0 elapsed=25.6s
[2026-03-23 02:33:33]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-23 02:33:35]   ERROR: exit=1 elapsed=25.7s
[2026-03-23 02:33:35]   STDERR: rrno 2] No such file or directory: '<workspace>/validation/runs/stability/rep1_google_gemini25pro/SRC_12/slides/slide-001.png'

[2026-03-23 02:33:35]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-23 02:36:24]   SUCCESS: exit=0 elapsed=456.9s
[2026-03-23 02:36:24]   --- Repetition 2/3 ---
[2026-03-23 02:36:24]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:37:53]   SUCCESS: exit=0 elapsed=88.5s
[2026-03-23 02:37:53]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:38:23]   SUCCESS: exit=0 elapsed=288.3s
[2026-03-23 02:38:23]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-23 02:39:03]   SUCCESS: exit=0 elapsed=70.3s
[2026-03-23 02:39:03]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:39:11]   SUCCESS: exit=0 elapsed=8.3s
[2026-03-23 02:39:11]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4omini
[2026-03-23 02:40:27]   SUCCESS: exit=0 elapsed=123.3s
[2026-03-23 02:40:27]   --- Repetition 2/3 ---
[2026-03-23 02:40:27]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25pro
[2026-03-23 02:41:29]   SUCCESS: exit=0 elapsed=137.6s
[2026-03-23 02:41:29]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:45:14]   SUCCESS: exit=0 elapsed=701.2s
[2026-03-23 02:45:14]   SKIP: already converted (<cached output>)
[2026-03-23 02:45:15]   SKIP: already converted (<cached output>)
[2026-03-23 02:45:15]   --- Repetition 2/3 ---
[2026-03-23 02:45:15]   SKIP: already converted (<cached output>)
[2026-03-23 02:45:15]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25pro
[2026-03-23 02:45:41]   SUCCESS: exit=0 elapsed=26.5s
[2026-03-23 02:45:41]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-23 02:48:00]   SUCCESS: exit=0 elapsed=453.6s
[2026-03-23 02:48:00]   SKIP: already converted (<cached output>)
[2026-03-23 02:48:00]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-23 02:48:01]   SUCCESS: exit=0 elapsed=140.3s
[2026-03-23 02:48:01]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25pro
[2026-03-23 02:48:23]   SUCCESS: exit=0 elapsed=22.0s
[2026-03-23 02:48:23]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-23 02:50:24]   SUCCESS: exit=0 elapsed=143.6s
[2026-03-23 02:50:24]   SKIP: already converted (<cached output>)
[2026-03-23 02:50:24]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-23 02:51:29]   TIMEOUT after 600.0s
[2026-03-23 02:51:29]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4omini
[2026-03-23 02:52:39]   SUCCESS: exit=0 elapsed=70.2s
[2026-03-23 02:52:39]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-23 03:00:08]   SUCCESS: exit=0 elapsed=704.9s
[2026-03-23 03:00:08]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-23 03:01:26]   SUCCESS: exit=0 elapsed=527.2s
[2026-03-23 03:01:26]   --- Repetition 3/3 ---
[2026-03-23 03:01:26]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4omini
[2026-03-23 03:02:00]   SUCCESS: exit=0 elapsed=696.6s
[2026-03-23 03:02:00]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-23 03:02:17]   SUCCESS: exit=0 elapsed=50.5s
[2026-03-23 03:02:17]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4omini
[2026-03-23 03:05:30]   SUCCESS: exit=0 elapsed=322.1s
[2026-03-23 03:05:30]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-23 03:07:00]   SUCCESS: exit=0 elapsed=299.5s
[2026-03-23 03:07:00]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-23 03:07:26]   SUCCESS: exit=0 elapsed=115.3s
[2026-03-23 03:07:26]   --- Repetition 3/3 ---
[2026-03-23 03:07:26]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25pro
[2026-03-23 03:07:49]   SUCCESS: exit=0 elapsed=331.9s
[2026-03-23 03:07:49]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4omini
[2026-03-23 03:07:58]   SUCCESS: exit=0 elapsed=8.9s
[2026-03-23 03:07:58]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4omini
[2026-03-23 03:08:56]   SUCCESS: exit=0 elapsed=116.5s
[2026-03-23 03:08:56]   --- Repetition 3/3 ---
[2026-03-23 03:08:56]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25pro
[2026-03-23 03:10:05]   SUCCESS: exit=0 elapsed=127.8s
[2026-03-23 03:10:05]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4omini
[2026-03-23 03:15:35]   SUCCESS: exit=0 elapsed=489.1s
[2026-03-23 03:15:35]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25pro
[2026-03-23 03:16:02]   SUCCESS: exit=0 elapsed=27.0s
[2026-03-23 03:16:02]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-23 03:17:14]   SUCCESS: exit=0 elapsed=497.1s
[2026-03-23 03:17:14]   SKIP: already converted (<cached output>)
[2026-03-23 03:17:14]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-23 03:18:22]   SUCCESS: exit=0 elapsed=140.6s
[2026-03-23 03:18:22]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25pro
[2026-03-23 03:18:58]   SUCCESS: exit=0 elapsed=35.4s
[2026-03-23 03:18:58]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-23 03:19:39]   SUCCESS: exit=0 elapsed=145.3s
[2026-03-23 03:19:39]   SKIP: already converted (<cached output>)
[2026-03-23 03:19:39]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-23 03:20:05]   TIMEOUT after 600.0s
[2026-03-23 03:20:05]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4omini
[2026-03-23 03:21:31]   SUCCESS: exit=0 elapsed=85.4s
[2026-03-23 03:21:31]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4omini
[2026-03-23 03:29:43]   SUCCESS: exit=0 elapsed=492.2s
[2026-03-23 03:29:43] 
============================================================
[2026-03-23 03:29:43] STABILITY: openai_gpt4turbo
[2026-03-23 03:29:43] ============================================================
[2026-03-23 03:29:43]   --- Repetition 1/3 ---
[2026-03-23 03:29:43]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:29:58]   SUCCESS: exit=0 elapsed=14.5s
[2026-03-23 03:29:58]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:30:01]   SUCCESS: exit=0 elapsed=663.7s
[2026-03-23 03:30:01]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-23 03:30:05]   SUCCESS: exit=0 elapsed=7.7s
[2026-03-23 03:30:05]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:30:10]   SUCCESS: exit=0 elapsed=4.4s
[2026-03-23 03:30:10]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4turbo
[2026-03-23 03:30:24]   SUCCESS: exit=0 elapsed=14.5s
[2026-03-23 03:30:24]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:30:47]   SUCCESS: exit=0 elapsed=668.0s
[2026-03-23 03:30:47]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-23 03:31:18]   SUCCESS: exit=0 elapsed=53.9s
[2026-03-23 03:31:18]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:31:36]   SUCCESS: exit=0 elapsed=17.8s
[2026-03-23 03:31:36]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4turbo
[2026-03-23 03:32:06]   SUCCESS: exit=0 elapsed=30.0s
[2026-03-23 03:32:06]   --- Repetition 2/3 ---
[2026-03-23 03:32:06]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:32:19]   SUCCESS: exit=0 elapsed=12.8s
[2026-03-23 03:32:19]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:32:25]   SUCCESS: exit=0 elapsed=6.6s
[2026-03-23 03:32:25]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:32:29]   SUCCESS: exit=0 elapsed=4.3s
[2026-03-23 03:32:29]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4turbo
[2026-03-23 03:32:39]   SUCCESS: exit=0 elapsed=9.1s
[2026-03-23 03:32:39]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:33:34]   SUCCESS: exit=0 elapsed=55.1s
[2026-03-23 03:33:34]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:33:54]   SUCCESS: exit=0 elapsed=19.8s
[2026-03-23 03:33:54]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4turbo
[2026-03-23 03:34:17]   SUCCESS: exit=0 elapsed=23.6s
[2026-03-23 03:34:17]   --- Repetition 3/3 ---
[2026-03-23 03:34:17]   CMD: folio convert SRC_01.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:34:28]   SUCCESS: exit=0 elapsed=11.3s
[2026-03-23 03:34:28]   CMD: folio convert SRC_04.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:34:31]   SUCCESS: exit=0 elapsed=270.1s
[2026-03-23 03:34:31]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-23 03:34:32]   ERROR: exit=1 elapsed=0.8s
[2026-03-23 03:34:32]   STDERR: t an error: The object you are trying to access does not exist (-1728)

If this file consistently fails, export it to PDF manually (File → Export → PDF, slides only) and run: folio convert <deck>.pdf

[2026-03-23 03:34:32] 
============================================================
[2026-03-23 03:34:32] STABILITY: google_gemini25flash
[2026-03-23 03:34:32] ============================================================
[2026-03-23 03:34:32]   --- Repetition 1/3 ---
[2026-03-23 03:34:32]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-23 03:34:35]   SUCCESS: exit=0 elapsed=6.4s
[2026-03-23 03:34:35]   CMD: folio convert SRC_05.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:34:39]   SUCCESS: exit=0 elapsed=4.4s
[2026-03-23 03:34:39]   CMD: folio convert SRC_11.pptx --llm-profile openai_gpt4turbo
[2026-03-23 03:35:41]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 03:35:41]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 03:35:41]   CMD: folio convert SRC_12.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:35:52]   SUCCESS: exit=0 elapsed=305.1s
[2026-03-23 03:35:52]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-23 03:36:37]   SUCCESS: exit=0 elapsed=56.2s
[2026-03-23 03:36:37]   CMD: folio convert SRC_15.pdf --llm-profile openai_gpt4turbo
[2026-03-23 03:36:54]   ERROR: exit=1 elapsed=61.9s
[2026-03-23 03:36:54]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 03:36:54] 
============================================================
[2026-03-23 03:36:54] STABILITY: google_gemini25flash
[2026-03-23 03:36:54] ============================================================
[2026-03-23 03:36:54]   --- Repetition 1/3 ---
[2026-03-23 03:36:54]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-23 03:36:54]   SUCCESS: exit=0 elapsed=17.4s
[2026-03-23 03:36:54]   CMD: folio convert SRC_16.pptx --llm-profile openai_gpt4turbo
[2026-03-23 03:37:56]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 03:37:56]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 03:37:56] 
============================================================
[2026-03-23 03:37:56] STABILITY: google_gemini25pro
[2026-03-23 03:37:56] ============================================================
[2026-03-23 03:37:56]   --- Repetition 1/3 ---
[2026-03-23 03:37:56]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25pro
[2026-03-23 03:40:33]   SUCCESS: exit=0 elapsed=361.1s
[2026-03-23 03:40:33]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25flash
[2026-03-23 03:40:50]   SUCCESS: exit=0 elapsed=17.0s
[2026-03-23 03:40:50]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25flash
[2026-03-23 03:42:10]   SUCCESS: exit=0 elapsed=79.3s
[2026-03-23 03:42:10]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-23 03:42:25]   SUCCESS: exit=0 elapsed=331.0s
[2026-03-23 03:42:25]   SKIP: already converted (<cached output>)
[2026-03-23 03:42:25]   SKIP: already converted (<cached output>)
[2026-03-23 03:42:25]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-23 03:43:11]   ERROR: exit=1 elapsed=61.7s
[2026-03-23 03:43:11]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 03:43:11]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-23 03:43:26]   ERROR: exit=1 elapsed=61.4s
[2026-03-23 03:43:26]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 03:43:26]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-23 03:43:28]   ERROR: exit=1 elapsed=16.8s
[2026-03-23 03:43:28]   STDERR:  No such file or directory: '<workspace>/validation/runs/stability/rep1_google_gemini25flash/SRC_12/.slides_tmp/slide-025.png'

[2026-03-23 03:43:28]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-23 03:43:30]   ERROR: exit=1 elapsed=3.5s
[2026-03-23 03:43:30]   STDERR:  No such file or directory: '<workspace>/validation/runs/stability/rep1_google_gemini25flash/SRC_12/.slides_tmp/slide-002.png'

[2026-03-23 03:43:30]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-23 03:43:34]   ERROR: exit=1 elapsed=4.3s
[2026-03-23 03:43:34]   STDERR:  No such file or directory: '<workspace>/validation/runs/stability/rep1_google_gemini25flash/SRC_15/.slides_tmp/slide-004.png'

[2026-03-23 03:43:34]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-23 03:44:35]   ERROR: exit=1 elapsed=61.4s
[2026-03-23 03:44:35]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 03:44:35]   --- Repetition 2/3 ---
[2026-03-23 03:44:35]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-23 03:46:11]   SUCCESS: exit=0 elapsed=163.0s
[2026-03-23 03:46:11]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-23 03:46:16]   SUCCESS: exit=0 elapsed=499.8s
[2026-03-23 03:46:16]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25pro
[2026-03-23 03:46:37]   SUCCESS: exit=0 elapsed=21.0s
[2026-03-23 03:46:37]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-23 03:47:13]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 03:47:13]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 03:47:13]   --- Repetition 2/3 ---
[2026-03-23 03:47:13]   SKIP: already converted (<cached output>)
[2026-03-23 03:47:13]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25flash
[2026-03-23 03:47:30]   SUCCESS: exit=0 elapsed=17.2s
[2026-03-23 03:47:30]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25flash
[2026-03-23 03:48:54]   SUCCESS: exit=0 elapsed=83.7s
[2026-03-23 03:48:54]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-23 03:49:02]   SUCCESS: exit=0 elapsed=144.7s
[2026-03-23 03:49:02]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25pro
[2026-03-23 03:49:56]   ERROR: exit=1 elapsed=62.0s
[2026-03-23 03:49:56]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 03:49:56]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-23 03:50:03]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 03:50:03]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 03:50:03]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-23 03:50:27]   SUCCESS: exit=0 elapsed=351.6s
[2026-03-23 03:50:27]   SKIP: already converted (<cached output>)
[2026-03-23 03:50:27]   SKIP: already converted (<cached output>)
[2026-03-23 03:50:27]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-23 03:51:29]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 03:51:29]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 03:51:29]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-23 03:56:28]   SUCCESS: exit=0 elapsed=392.1s
[2026-03-23 03:56:28]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-23 03:57:49]   SUCCESS: exit=0 elapsed=380.2s
[2026-03-23 03:57:49]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-23 03:59:04]   SUCCESS: exit=0 elapsed=156.2s
[2026-03-23 03:59:04]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-23 04:00:03]   TIMEOUT after 600.0s
[2026-03-23 04:00:03]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-23 04:00:06]   ERROR: exit=1 elapsed=61.7s
[2026-03-23 04:00:06]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:00:06]   --- Repetition 3/3 ---
[2026-03-23 04:00:06]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-23 04:00:22]   SUCCESS: exit=0 elapsed=153.1s
[2026-03-23 04:00:22]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-23 04:01:24]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 04:01:24]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:01:24]   --- Repetition 3/3 ---
[2026-03-23 04:01:24]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-23 04:04:24]   SUCCESS: exit=0 elapsed=260.4s
[2026-03-23 04:04:24]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-23 04:05:26]   ERROR: exit=1 elapsed=62.2s
[2026-03-23 04:05:26]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:05:26]   --- Repetition 2/3 ---
[2026-03-23 04:05:26]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25pro
[2026-03-23 04:06:02]   SUCCESS: exit=0 elapsed=356.1s
[2026-03-23 04:06:02]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25flash
[2026-03-23 04:06:20]   SUCCESS: exit=0 elapsed=18.2s
[2026-03-23 04:06:20]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25flash
[2026-03-23 04:07:26]   SUCCESS: exit=0 elapsed=362.1s
[2026-03-23 04:07:26]   SKIP: already converted (<cached output>)
[2026-03-23 04:07:26]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25flash
[2026-03-23 04:07:45]   SUCCESS: exit=0 elapsed=84.8s
[2026-03-23 04:07:45]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-23 04:08:46]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 04:08:46]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:08:46]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-23 04:08:48]   SUCCESS: exit=0 elapsed=82.3s
[2026-03-23 04:08:48]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-23 04:09:50]   ERROR: exit=1 elapsed=61.6s
[2026-03-23 04:09:50]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:09:50]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-23 04:13:27]   SUCCESS: exit=0 elapsed=481.4s
[2026-03-23 04:13:27]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25pro
[2026-03-23 04:13:56]   SUCCESS: exit=0 elapsed=29.1s
[2026-03-23 04:13:56]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-23 04:15:26]   SUCCESS: exit=0 elapsed=399.7s
[2026-03-23 04:15:26]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-23 04:16:18]   SUCCESS: exit=0 elapsed=141.4s
[2026-03-23 04:16:18]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25pro
[2026-03-23 04:16:32]   SUCCESS: exit=0 elapsed=401.8s
[2026-03-23 04:16:32]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-23 04:17:19]   ERROR: exit=1 elapsed=61.6s
[2026-03-23 04:17:19]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:17:19]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-23 04:18:06]   SUCCESS: exit=0 elapsed=160.1s
[2026-03-23 04:18:06]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-23 04:19:09]   ERROR: exit=1 elapsed=62.8s
[2026-03-23 04:19:09]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:19:09] 
============================================================
[2026-03-23 04:19:09] STABILITY: google_gemini20flash
[2026-03-23 04:19:09] ============================================================
[2026-03-23 04:19:09]   --- Repetition 1/3 ---
[2026-03-23 04:19:09]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash
[2026-03-23 04:19:10]   SUCCESS: exit=0 elapsed=158.1s
[2026-03-23 04:19:10]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-23 04:19:43]   SUCCESS: exit=0 elapsed=34.4s
[2026-03-23 04:19:43]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash
[2026-03-23 04:19:55]   SUCCESS: exit=0 elapsed=11.2s
[2026-03-23 04:19:55]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash
[2026-03-23 04:20:03]   SUCCESS: exit=0 elapsed=8.6s
[2026-03-23 04:20:03]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-23 04:20:11]   ERROR: exit=1 elapsed=61.4s
[2026-03-23 04:20:11]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:20:11] 
============================================================
[2026-03-23 04:20:11] STABILITY: google_gemini20flash
[2026-03-23 04:20:11] ============================================================
[2026-03-23 04:20:11]   --- Repetition 1/3 ---
[2026-03-23 04:20:11]   SKIP: already converted (<cached output>)
[2026-03-23 04:20:11]   SKIP: already converted (<cached output>)
[2026-03-23 04:20:11]   SKIP: already converted (<cached output>)
[2026-03-23 04:20:11]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-23 04:21:05]   ERROR: exit=1 elapsed=62.1s
[2026-03-23 04:21:05]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:21:05]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash
[2026-03-23 04:21:13]   ERROR: exit=1 elapsed=61.6s
[2026-03-23 04:21:13]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:21:13]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash
[2026-03-23 04:21:28]   ERROR: exit=1 elapsed=15.5s
[2026-03-23 04:21:28]   STDERR:  No such file or directory: '<workspace>/validation/runs/stability/rep1_google_gemini20flash/SRC_12/.slides_tmp/slide-019.png'

[2026-03-23 04:21:28]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash
[2026-03-23 04:22:50]   SUCCESS: exit=0 elapsed=82.3s
[2026-03-23 04:22:50]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-23 04:23:52]   ERROR: exit=1 elapsed=62.0s
[2026-03-23 04:23:52]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:23:52]   --- Repetition 2/3 ---
[2026-03-23 04:23:52]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash
[2026-03-23 04:24:21]   SUCCESS: exit=0 elapsed=28.3s
[2026-03-23 04:24:21]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash
[2026-03-23 04:24:31]   SUCCESS: exit=0 elapsed=10.8s
[2026-03-23 04:24:31]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash
[2026-03-23 04:24:40]   SUCCESS: exit=0 elapsed=8.6s
[2026-03-23 04:24:40]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-23 04:24:42]   SUCCESS: exit=0 elapsed=216.7s
[2026-03-23 04:24:42]   SKIP: already converted (<cached output>)
[2026-03-23 04:24:42]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-23 04:25:42]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 04:25:42]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:25:42]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash
[2026-03-23 04:25:43]   ERROR: exit=1 elapsed=61.6s
[2026-03-23 04:25:43]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:25:43]   --- Repetition 2/3 ---
[2026-03-23 04:25:43]   SKIP: already converted (<cached output>)
[2026-03-23 04:25:43]   SKIP: already converted (<cached output>)
[2026-03-23 04:25:43]   SKIP: already converted (<cached output>)
[2026-03-23 04:25:43]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-23 04:26:45]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 04:26:45]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:26:45]   SKIP: already converted (<cached output>)
[2026-03-23 04:26:45]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash
[2026-03-23 04:27:19]   TIMEOUT after 600.0s
[2026-03-23 04:27:19]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-23 04:28:07]   SUCCESS: exit=0 elapsed=81.3s
[2026-03-23 04:28:07]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-23 04:29:08]   ERROR: exit=1 elapsed=61.9s
[2026-03-23 04:29:08]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:29:08]   --- Repetition 3/3 ---
[2026-03-23 04:29:08]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash
[2026-03-23 04:29:11]   SUCCESS: exit=0 elapsed=209.7s
[2026-03-23 04:29:11]   SKIP: already converted (<cached output>)
[2026-03-23 04:29:11]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-23 04:29:36]   SUCCESS: exit=0 elapsed=27.8s
[2026-03-23 04:29:36]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash
[2026-03-23 04:29:48]   SUCCESS: exit=0 elapsed=11.5s
[2026-03-23 04:29:48]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash
[2026-03-23 04:29:58]   SUCCESS: exit=0 elapsed=10.2s
[2026-03-23 04:29:58]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-23 04:30:13]   ERROR: exit=1 elapsed=62.0s
[2026-03-23 04:30:13]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:30:13]   --- Repetition 3/3 ---
[2026-03-23 04:30:13]   SKIP: already converted (<cached output>)
[2026-03-23 04:30:13]   SKIP: already converted (<cached output>)
[2026-03-23 04:30:13]   SKIP: already converted (<cached output>)
[2026-03-23 04:30:13]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-23 04:31:00]   ERROR: exit=1 elapsed=61.9s
[2026-03-23 04:31:00]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:31:00]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash
[2026-03-23 04:31:15]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 04:31:15]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:31:15]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash
[2026-03-23 04:31:21]   ERROR: exit=1 elapsed=5.8s
[2026-03-23 04:31:21]   STDERR:  No such file or directory: '<workspace>/validation/runs/stability/rep3_google_gemini20flash/SRC_12/.slides_tmp/slide-026.png'

[2026-03-23 04:31:21]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash
[2026-03-23 04:31:24]   ERROR: exit=1 elapsed=23.8s
[2026-03-23 04:31:24]   STDERR: no 2] No such file or directory: '<workspace>/validation/runs/stability/rep3_google_gemini20flash/SRC_12/slides/slide-001.png'

[2026-03-23 04:31:24]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash
[2026-03-23 04:31:28]   ERROR: exit=1 elapsed=4.4s
[2026-03-23 04:31:28]   STDERR:  No such file or directory: '<workspace>/validation/runs/stability/rep3_google_gemini20flash/SRC_15/.slides_tmp/slide-004.png'

[2026-03-23 04:31:28]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-23 04:32:30]   ERROR: exit=1 elapsed=61.6s
[2026-03-23 04:32:30]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:32:30] 
============================================================
[2026-03-23 04:32:30] STABILITY: google_gemini20flash001
[2026-03-23 04:32:30] ============================================================
[2026-03-23 04:32:30]   --- Repetition 1/3 ---
[2026-03-23 04:32:30]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:32:45]   SUCCESS: exit=0 elapsed=84.9s
[2026-03-23 04:32:45]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-23 04:32:48]   SUCCESS: exit=0 elapsed=328.2s
[2026-03-23 04:32:48]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-23 04:32:59]   SUCCESS: exit=0 elapsed=29.0s
[2026-03-23 04:32:59]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:33:09]   SUCCESS: exit=0 elapsed=10.2s
[2026-03-23 04:33:09]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:33:18]   SUCCESS: exit=0 elapsed=9.0s
[2026-03-23 04:33:18]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:33:47]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 04:33:47]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:33:47] 
============================================================
[2026-03-23 04:33:47] STABILITY: google_gemini20flash001
[2026-03-23 04:33:47] ============================================================
[2026-03-23 04:33:47]   --- Repetition 1/3 ---
[2026-03-23 04:33:47]   SKIP: already converted (<cached output>)
[2026-03-23 04:33:47]   SKIP: already converted (<cached output>)
[2026-03-23 04:33:47]   SKIP: already converted (<cached output>)
[2026-03-23 04:33:47]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:33:49]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 04:33:49]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:33:49]   --- Repetition 3/3 ---
[2026-03-23 04:33:49]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25pro
[2026-03-23 04:34:20]   ERROR: exit=1 elapsed=62.0s
[2026-03-23 04:34:20]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:34:20]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:34:49]   ERROR: exit=1 elapsed=61.7s
[2026-03-23 04:34:49]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:34:49]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:38:11]   SUCCESS: exit=0 elapsed=231.2s
[2026-03-23 04:38:11]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:38:33]   SUCCESS: exit=0 elapsed=224.5s
[2026-03-23 04:38:33]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:39:37]   SUCCESS: exit=0 elapsed=86.4s
[2026-03-23 04:39:37]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:40:01]   SUCCESS: exit=0 elapsed=87.5s
[2026-03-23 04:40:01]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:40:39]   ERROR: exit=1 elapsed=62.1s
[2026-03-23 04:40:39]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:40:39]   --- Repetition 2/3 ---
[2026-03-23 04:40:39]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:41:02]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 04:41:02]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:41:02]   --- Repetition 2/3 ---
[2026-03-23 04:41:02]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:41:08]   SUCCESS: exit=0 elapsed=28.7s
[2026-03-23 04:41:08]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:41:18]   SUCCESS: exit=0 elapsed=10.4s
[2026-03-23 04:41:18]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:41:27]   SUCCESS: exit=0 elapsed=8.8s
[2026-03-23 04:41:27]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:41:33]   SUCCESS: exit=0 elapsed=30.4s
[2026-03-23 04:41:33]   SKIP: already converted (<cached output>)
[2026-03-23 04:41:33]   SKIP: already converted (<cached output>)
[2026-03-23 04:41:33]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:41:52]   SUCCESS: exit=0 elapsed=483.4s
[2026-03-23 04:41:52]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25pro
[2026-03-23 04:42:18]   SUCCESS: exit=0 elapsed=25.9s
[2026-03-23 04:42:18]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25pro
[2026-03-23 04:42:29]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 04:42:29]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:42:29]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:42:35]   ERROR: exit=1 elapsed=61.9s
[2026-03-23 04:42:35]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:42:35]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:42:50]   ERROR: exit=1 elapsed=15.6s
[2026-03-23 04:42:50]   STDERR:  such file or directory: '<workspace>/validation/runs/stability/rep2_google_gemini20flash001/SRC_12/.slides_tmp/slide-019.png'

[2026-03-23 04:42:50]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:44:13]   SUCCESS: exit=0 elapsed=82.7s
[2026-03-23 04:44:13]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:44:39]   SUCCESS: exit=0 elapsed=140.9s
[2026-03-23 04:44:39]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25pro
[2026-03-23 04:45:15]   ERROR: exit=1 elapsed=61.9s
[2026-03-23 04:45:15]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:45:15]   --- Repetition 3/3 ---
[2026-03-23 04:45:15]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:45:41]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 04:45:41]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:45:41]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25pro
[2026-03-23 04:45:42]   SUCCESS: exit=0 elapsed=27.4s
[2026-03-23 04:45:42]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:45:53]   SUCCESS: exit=0 elapsed=11.2s
[2026-03-23 04:45:53]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:46:03]   SUCCESS: exit=0 elapsed=9.1s
[2026-03-23 04:46:03]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:46:09]   SUCCESS: exit=0 elapsed=219.5s
[2026-03-23 04:46:09]   SKIP: already converted (<cached output>)
[2026-03-23 04:46:09]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:47:04]   ERROR: exit=1 elapsed=61.4s
[2026-03-23 04:47:04]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:47:04]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:47:10]   ERROR: exit=1 elapsed=61.7s
[2026-03-23 04:47:10]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:47:10]   --- Repetition 3/3 ---
[2026-03-23 04:47:10]   SKIP: already converted (<cached output>)
[2026-03-23 04:47:10]   SKIP: already converted (<cached output>)
[2026-03-23 04:47:10]   SKIP: already converted (<cached output>)
[2026-03-23 04:47:10]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:48:12]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 04:48:12]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:48:12]   SKIP: already converted (<cached output>)
[2026-03-23 04:48:12]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash001
[2026-03-23 04:49:39]   SUCCESS: exit=0 elapsed=86.9s
[2026-03-23 04:49:39]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:50:40]   ERROR: exit=1 elapsed=61.9s
[2026-03-23 04:50:40]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:50:40] 
============================================================
[2026-03-23 04:50:40] STABILITY: google_gemini20lite
[2026-03-23 04:50:40] ============================================================
[2026-03-23 04:50:40]   --- Repetition 1/3 ---
[2026-03-23 04:50:40]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20lite
[2026-03-23 04:50:44]   SUCCESS: exit=0 elapsed=219.7s
[2026-03-23 04:50:44]   SKIP: already converted (<cached output>)
[2026-03-23 04:50:44]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-23 04:51:05]   SUCCESS: exit=0 elapsed=24.4s
[2026-03-23 04:51:05]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20lite
[2026-03-23 04:51:15]   SUCCESS: exit=0 elapsed=9.9s
[2026-03-23 04:51:15]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20lite
[2026-03-23 04:51:23]   SUCCESS: exit=0 elapsed=8.3s
[2026-03-23 04:51:23]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-23 04:51:46]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 04:51:46]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:51:46] 
============================================================
[2026-03-23 04:51:46] STABILITY: google_gemini20lite
[2026-03-23 04:51:46] ============================================================
[2026-03-23 04:51:46]   --- Repetition 1/3 ---
[2026-03-23 04:51:46]   SKIP: already converted (<cached output>)
[2026-03-23 04:51:46]   SKIP: already converted (<cached output>)
[2026-03-23 04:51:46]   SKIP: already converted (<cached output>)
[2026-03-23 04:51:46]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-23 04:52:25]   ERROR: exit=1 elapsed=62.1s
[2026-03-23 04:52:25]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:52:25]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-23 04:52:47]   ERROR: exit=1 elapsed=61.3s
[2026-03-23 04:52:47]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:52:47]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-23 04:55:41]   TIMEOUT after 600.0s
[2026-03-23 04:55:41]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25pro
[2026-03-23 04:55:50]   SUCCESS: exit=0 elapsed=204.4s
[2026-03-23 04:55:50]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20lite
[2026-03-23 04:56:10]   SUCCESS: exit=0 elapsed=203.6s
[2026-03-23 04:56:10]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20lite
[2026-03-23 04:57:12]   SUCCESS: exit=0 elapsed=82.5s
[2026-03-23 04:57:12]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-23 04:57:28]   SUCCESS: exit=0 elapsed=77.8s
[2026-03-23 04:57:28]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-23 04:58:14]   ERROR: exit=1 elapsed=61.6s
[2026-03-23 04:58:14]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:58:14]   --- Repetition 2/3 ---
[2026-03-23 04:58:14]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20lite
[2026-03-23 04:58:30]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 04:58:30]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 04:58:30]   --- Repetition 2/3 ---
[2026-03-23 04:58:30]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20lite
[2026-03-23 04:58:40]   SUCCESS: exit=0 elapsed=25.9s
[2026-03-23 04:58:40]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20lite
[2026-03-23 04:58:50]   SUCCESS: exit=0 elapsed=10.0s
[2026-03-23 04:58:50]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20lite
[2026-03-23 04:58:54]   SUCCESS: exit=0 elapsed=24.3s
[2026-03-23 04:58:54]   SKIP: already converted (<cached output>)
[2026-03-23 04:58:54]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20lite
[2026-03-23 04:58:58]   SUCCESS: exit=0 elapsed=8.2s
[2026-03-23 04:58:58]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-23 04:59:02]   SUCCESS: exit=0 elapsed=8.0s
[2026-03-23 04:59:02]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-23 04:59:59]   ERROR: exit=1 elapsed=61.4s
[2026-03-23 04:59:59]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 04:59:59]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-23 05:00:03]   ERROR: exit=1 elapsed=61.4s
[2026-03-23 05:00:03]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 05:00:03]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-23 05:00:10]   SUCCESS: exit=0 elapsed=269.6s
[2026-03-23 05:00:10]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25pro
[2026-03-23 05:00:19]   ERROR: exit=1 elapsed=16.0s
[2026-03-23 05:00:19]   STDERR: ] No such file or directory: '<workspace>/validation/runs/stability/rep2_google_gemini20lite/SRC_12/.slides_tmp/slide-023.png'

[2026-03-23 05:00:19]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20lite
[2026-03-23 05:01:12]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 05:01:12]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 05:01:12] 
============================================================
[2026-03-23 05:01:12] STABILITY: google_gemini25flash
[2026-03-23 05:01:12] ============================================================
[2026-03-23 05:01:12]   --- Repetition 1/3 ---
[2026-03-23 05:01:12]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-23 05:01:39]   SUCCESS: exit=0 elapsed=79.8s
[2026-03-23 05:01:39]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-23 05:02:41]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 05:02:41]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 05:02:41]   --- Repetition 3/3 ---
[2026-03-23 05:02:41]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20lite
[2026-03-23 05:03:08]   SUCCESS: exit=0 elapsed=27.4s
[2026-03-23 05:03:08]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20lite
[2026-03-23 05:03:18]   SUCCESS: exit=0 elapsed=9.5s
[2026-03-23 05:03:18]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20lite
[2026-03-23 05:03:26]   SUCCESS: exit=0 elapsed=8.5s
[2026-03-23 05:03:26]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-23 05:03:27]   SUCCESS: exit=0 elapsed=207.7s
[2026-03-23 05:03:27]   SKIP: already converted (<cached output>)
[2026-03-23 05:03:27]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-23 05:04:28]   ERROR: exit=1 elapsed=61.4s
[2026-03-23 05:04:28]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 05:04:28]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-23 05:04:28]   ERROR: exit=1 elapsed=61.4s
[2026-03-23 05:04:28]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 05:04:28]   --- Repetition 3/3 ---
[2026-03-23 05:04:28]   SKIP: already converted (<cached output>)
[2026-03-23 05:04:28]   SKIP: already converted (<cached output>)
[2026-03-23 05:04:28]   SKIP: already converted (<cached output>)
[2026-03-23 05:04:28]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-23 05:05:30]   ERROR: exit=1 elapsed=61.6s
[2026-03-23 05:05:30]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 05:05:30]   SKIP: already converted (<cached output>)
[2026-03-23 05:05:30]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20lite
[2026-03-23 05:06:49]   SUCCESS: exit=0 elapsed=79.2s
[2026-03-23 05:06:49]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-23 05:07:08]   SUCCESS: exit=0 elapsed=356.4s
[2026-03-23 05:07:08]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25flash
[2026-03-23 05:07:27]   SUCCESS: exit=0 elapsed=18.4s
[2026-03-23 05:07:27]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25flash
[2026-03-23 05:07:51]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 05:07:51]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 05:07:51] 
Completed: 2026-03-23T05:07:51.105168
[2026-03-23 05:07:51] Total wall time: 67666s (18.8h)
[2026-03-23 05:07:56]   SUCCESS: exit=0 elapsed=208.7s
[2026-03-23 05:07:56]   SKIP: already converted (<cached output>)
[2026-03-23 05:07:56]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-23 05:08:42]   SUCCESS: exit=0 elapsed=75.1s
[2026-03-23 05:08:42]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-23 05:08:58]   ERROR: exit=1 elapsed=62.1s
[2026-03-23 05:08:58]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 05:08:58] 
Completed: 2026-03-23T05:08:58.928756
[2026-03-23 05:08:58] Total wall time: 73603s (20.4h)
[2026-03-23 05:09:44]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 05:09:44]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 05:09:44]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-23 05:16:19]   SUCCESS: exit=0 elapsed=394.8s
[2026-03-23 05:16:19]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-23 05:19:15]   SUCCESS: exit=0 elapsed=176.9s
[2026-03-23 05:19:15]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-23 05:20:18]   ERROR: exit=1 elapsed=62.4s
[2026-03-23 05:20:18]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 05:20:18]   --- Repetition 2/3 ---
[2026-03-23 05:20:18]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-23 05:26:22]   SUCCESS: exit=0 elapsed=364.2s
[2026-03-23 05:26:22]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25flash
[2026-03-23 05:26:40]   SUCCESS: exit=0 elapsed=18.1s
[2026-03-23 05:26:40]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25flash
[2026-03-23 05:28:07]   SUCCESS: exit=0 elapsed=86.4s
[2026-03-23 05:28:07]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-23 05:29:08]   ERROR: exit=1 elapsed=61.6s
[2026-03-23 05:29:08]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 05:29:08]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-23 05:54:01]   SUCCESS: exit=0 elapsed=1492.7s
[2026-03-23 05:54:01]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-23 05:56:43]   SUCCESS: exit=0 elapsed=161.9s
[2026-03-23 05:56:43]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-23 05:57:45]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 05:57:45]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 05:57:45]   --- Repetition 3/3 ---
[2026-03-23 05:57:45]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini25flash
[2026-03-23 06:52:48]   TIMEOUT after 3303.8s
[2026-03-23 06:52:48]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini25flash
[2026-03-23 06:53:11]   SUCCESS: exit=0 elapsed=22.6s
[2026-03-23 06:53:11]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini25flash
[2026-03-23 07:11:15]   SUCCESS: exit=0 elapsed=1083.5s
[2026-03-23 07:11:15]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini25flash
[2026-03-23 07:12:17]   ERROR: exit=1 elapsed=62.2s
[2026-03-23 07:12:17]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 07:12:17]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini25flash
[2026-03-23 07:19:15]   SUCCESS: exit=0 elapsed=418.3s
[2026-03-23 07:19:15]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini25flash
[2026-03-23 07:22:07]   SUCCESS: exit=0 elapsed=172.1s
[2026-03-23 07:22:07]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini25flash
[2026-03-23 07:23:09]   ERROR: exit=1 elapsed=62.1s
[2026-03-23 07:23:09]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 07:23:09] 
============================================================
[2026-03-23 07:23:09] STABILITY: google_gemini20flash
[2026-03-23 07:23:09] ============================================================
[2026-03-23 07:23:09]   --- Repetition 1/3 ---
[2026-03-23 07:23:09]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash
[2026-03-23 07:23:39]   SUCCESS: exit=0 elapsed=29.9s
[2026-03-23 07:23:39]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash
[2026-03-23 07:23:49]   SUCCESS: exit=0 elapsed=9.5s
[2026-03-23 07:23:49]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash
[2026-03-23 07:23:57]   SUCCESS: exit=0 elapsed=8.3s
[2026-03-23 07:23:57]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-23 07:24:58]   ERROR: exit=1 elapsed=61.4s
[2026-03-23 07:24:58]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 07:24:58]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash
[2026-03-23 07:28:39]   SUCCESS: exit=0 elapsed=220.9s
[2026-03-23 07:28:39]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash
[2026-03-23 07:30:01]   SUCCESS: exit=0 elapsed=81.3s
[2026-03-23 07:30:01]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-23 07:31:02]   ERROR: exit=1 elapsed=61.7s
[2026-03-23 07:31:02]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 07:31:02]   --- Repetition 2/3 ---
[2026-03-23 07:31:02]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash
[2026-03-23 07:31:33]   SUCCESS: exit=0 elapsed=30.3s
[2026-03-23 07:31:33]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash
[2026-03-23 07:31:43]   SUCCESS: exit=0 elapsed=10.6s
[2026-03-23 07:31:43]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash
[2026-03-23 07:31:52]   SUCCESS: exit=0 elapsed=8.6s
[2026-03-23 07:31:52]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-23 07:32:54]   ERROR: exit=1 elapsed=61.9s
[2026-03-23 07:32:54]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 07:32:54]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash
[2026-03-23 07:36:31]   SUCCESS: exit=0 elapsed=217.7s
[2026-03-23 07:36:31]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash
[2026-03-23 07:37:55]   SUCCESS: exit=0 elapsed=83.6s
[2026-03-23 07:37:55]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-23 07:38:57]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 07:38:57]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 07:38:57]   --- Repetition 3/3 ---
[2026-03-23 07:38:57]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash
[2026-03-23 07:39:26]   SUCCESS: exit=0 elapsed=29.5s
[2026-03-23 07:39:26]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash
[2026-03-23 07:39:36]   SUCCESS: exit=0 elapsed=10.3s
[2026-03-23 07:39:36]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash
[2026-03-23 07:39:45]   SUCCESS: exit=0 elapsed=8.1s
[2026-03-23 07:39:45]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash
[2026-03-23 07:40:46]   ERROR: exit=1 elapsed=62.0s
[2026-03-23 07:40:46]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 07:40:46]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash
[2026-03-23 07:44:33]   SUCCESS: exit=0 elapsed=226.9s
[2026-03-23 07:44:33]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash
[2026-03-23 08:03:18]   SUCCESS: exit=0 elapsed=1124.9s
[2026-03-23 08:03:18]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash
[2026-03-23 08:06:06]   ERROR: exit=1 elapsed=167.5s
[2026-03-23 08:06:06]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 08:06:06] 
============================================================
[2026-03-23 08:06:06] STABILITY: google_gemini20flash001
[2026-03-23 08:06:06] ============================================================
[2026-03-23 08:06:06]   --- Repetition 1/3 ---
[2026-03-23 08:06:06]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:06:38]   SUCCESS: exit=0 elapsed=32.7s
[2026-03-23 08:06:38]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:06:49]   SUCCESS: exit=0 elapsed=10.1s
[2026-03-23 08:06:49]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:06:57]   SUCCESS: exit=0 elapsed=8.5s
[2026-03-23 08:06:57]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-23 08:22:59]   ERROR: exit=1 elapsed=962.1s
[2026-03-23 08:22:59]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 08:22:59]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:35:59]   SUCCESS: exit=0 elapsed=779.7s
[2026-03-23 08:35:59]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:37:31]   SUCCESS: exit=0 elapsed=92.7s
[2026-03-23 08:37:31]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-23 08:38:33]   ERROR: exit=1 elapsed=61.9s
[2026-03-23 08:38:33]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 08:38:33]   --- Repetition 2/3 ---
[2026-03-23 08:38:33]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:39:06]   SUCCESS: exit=0 elapsed=32.5s
[2026-03-23 08:39:06]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:39:17]   SUCCESS: exit=0 elapsed=11.6s
[2026-03-23 08:39:17]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:39:26]   SUCCESS: exit=0 elapsed=8.4s
[2026-03-23 08:39:26]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-23 08:40:28]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 08:40:28]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 08:40:28]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:44:11]   SUCCESS: exit=0 elapsed=223.4s
[2026-03-23 08:44:11]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:45:34]   SUCCESS: exit=0 elapsed=82.9s
[2026-03-23 08:45:34]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-23 08:46:36]   ERROR: exit=1 elapsed=61.7s
[2026-03-23 08:46:36]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 08:46:36]   --- Repetition 3/3 ---
[2026-03-23 08:46:36]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:47:11]   SUCCESS: exit=0 elapsed=35.3s
[2026-03-23 08:47:11]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:47:23]   SUCCESS: exit=0 elapsed=11.8s
[2026-03-23 08:47:23]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:47:31]   SUCCESS: exit=0 elapsed=8.5s
[2026-03-23 08:47:31]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20flash001
[2026-03-23 08:50:58]   ERROR: exit=1 elapsed=206.9s
[2026-03-23 08:50:58]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 08:50:58]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20flash001
[2026-03-23 08:59:44]   SUCCESS: exit=0 elapsed=525.7s
[2026-03-23 08:59:44]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20flash001
[2026-03-23 09:01:09]   SUCCESS: exit=0 elapsed=85.5s
[2026-03-23 09:01:09]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20flash001
[2026-03-23 09:02:11]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 09:02:11]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 09:02:11] 
============================================================
[2026-03-23 09:02:11] STABILITY: google_gemini20lite
[2026-03-23 09:02:11] ============================================================
[2026-03-23 09:02:11]   --- Repetition 1/3 ---
[2026-03-23 09:02:11]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20lite
[2026-03-23 09:03:08]   SUCCESS: exit=0 elapsed=56.7s
[2026-03-23 09:03:08]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20lite
[2026-03-23 09:03:19]   SUCCESS: exit=0 elapsed=11.3s
[2026-03-23 09:03:19]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20lite
[2026-03-23 09:03:29]   SUCCESS: exit=0 elapsed=9.2s
[2026-03-23 09:03:29]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-23 09:04:30]   ERROR: exit=1 elapsed=61.8s
[2026-03-23 09:04:30]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 09:04:30]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-23 09:08:10]   SUCCESS: exit=0 elapsed=219.4s
[2026-03-23 09:08:10]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20lite
[2026-03-23 09:09:31]   SUCCESS: exit=0 elapsed=81.4s
[2026-03-23 09:09:31]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-23 09:10:33]   ERROR: exit=1 elapsed=61.7s
[2026-03-23 09:10:33]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 09:10:33]   --- Repetition 2/3 ---
[2026-03-23 09:10:33]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20lite
[2026-03-23 09:10:59]   SUCCESS: exit=0 elapsed=26.1s
[2026-03-23 09:10:59]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20lite
[2026-03-23 09:11:09]   SUCCESS: exit=0 elapsed=10.1s
[2026-03-23 09:11:09]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20lite
[2026-03-23 09:11:17]   SUCCESS: exit=0 elapsed=8.6s
[2026-03-23 09:11:17]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-23 09:12:19]   ERROR: exit=1 elapsed=61.5s
[2026-03-23 09:12:19]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 09:12:19]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-23 09:15:54]   SUCCESS: exit=0 elapsed=215.1s
[2026-03-23 09:15:54]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20lite
[2026-03-23 09:17:15]   SUCCESS: exit=0 elapsed=81.2s
[2026-03-23 09:17:15]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-23 09:18:18]   ERROR: exit=1 elapsed=62.7s
[2026-03-23 09:18:18]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 09:18:18]   --- Repetition 3/3 ---
[2026-03-23 09:18:18]   CMD: folio convert SRC_01.pdf --llm-profile google_gemini20lite
[2026-03-23 09:18:49]   SUCCESS: exit=0 elapsed=31.1s
[2026-03-23 09:18:49]   CMD: folio convert SRC_04.pdf --llm-profile google_gemini20lite
[2026-03-23 09:18:59]   SUCCESS: exit=0 elapsed=9.8s
[2026-03-23 09:18:59]   CMD: folio convert SRC_05.pdf --llm-profile google_gemini20lite
[2026-03-23 09:19:08]   SUCCESS: exit=0 elapsed=8.7s
[2026-03-23 09:19:08]   CMD: folio convert SRC_11.pptx --llm-profile google_gemini20lite
[2026-03-23 09:20:09]   ERROR: exit=1 elapsed=61.9s
[2026-03-23 09:20:09]   STDERR: Converting: SRC_11.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_11.pptx within 61s

[2026-03-23 09:20:09]   CMD: folio convert SRC_12.pdf --llm-profile google_gemini20lite
[2026-03-23 09:23:45]   SUCCESS: exit=0 elapsed=216.0s
[2026-03-23 09:23:45]   CMD: folio convert SRC_15.pdf --llm-profile google_gemini20lite
[2026-03-23 09:25:07]   SUCCESS: exit=0 elapsed=81.7s
[2026-03-23 09:25:07]   CMD: folio convert SRC_16.pptx --llm-profile google_gemini20lite
[2026-03-23 09:26:09]   ERROR: exit=1 elapsed=61.6s
[2026-03-23 09:26:09]   STDERR: : SRC_16.pptx
  Normalizing to PDF...
✗ Conversion failed: PowerPoint did not open SRC_16.pptx within 61s

[2026-03-23 09:26:09] 
Completed: 2026-03-23T09:26:09.245752
[2026-03-23 09:26:09] Total wall time: 90115s (25.0h)

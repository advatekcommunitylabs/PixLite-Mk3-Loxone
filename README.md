# PixLite Mk3 SHOWTime for Loxone

**Work in progress to help Advatek Users.**

Advatek's Product Management team is developing this template to help customers and integrators explore control of PixLite Mk3 SHOWTime from Loxone. We are sharing the work through Advatek Community Labs so users can follow progress, contribute and review the approach where they see fit. We feel transparency is key, the rest of this ReadMe covers where we're up to:

This is an unfinished development snapshot awaiting to be run on a Loxone Miniserver it is not yet approved for production installations. Public access to this repository does not mean the integration has completed customer validation or been approved for the Loxone Library.

## What we're building

The intended integration runs natively on the Loxone Miniserver, communicating directly with PixLite over HTTP(S). It aims to provide stored scene and playlist selection, playback controls, brightness and colour control, plus temperature, bank voltage and fuse/protection feedback where the controller supports those measurements.

## What is included today

| File | Current state |
| --- | --- |
| [Command example](examples/PixLite-SHOWTime-Commands-DRAFT.Loxone) | 42 unwired native HTTP command definitions for scene/playlist recall, transport, Live, Blank, Freeze, Stop, intensity presets, static colours and API reads. |
| [Telemetry example](examples/PixLite-SHOWTime-Telemetry-DRAFT.Loxone) | Adds a disabled native Program and read-only HTTP polling command for temperature, bank voltage and separate fuse/protection status. Native execution remains untested. |
| [Native telemetry details](docs/native-telemetry.md) | Inputs, outputs, validity rules and remaining qualification work. |
| `native/`, `tools/` and `tests/` | Native source, local project-generation tools and local tests. Python and the compiled test adapters are development tools, not a deployed runtime. |

Both examples target loopback HTTPS by default. Control commands are unwired, and the telemetry enable and commissioned-MAC inputs are disconnected. These files are example projects, not standalone Library template exports or finished operator dashboards.

## Validation so far

- Direct API tests on an A4-S Mk3 and E16-S Mk3 checked selected commands and supported telemetry. These were PC-to-PixLite checks, not commands executed by a Miniserver.
- Earlier example revisions opened, saved and reopened in Loxone Config 17.2.10.21.
- Local tests cover request validation, JSON decoding, units, unavailable telemetry, document wiring and simulated polling lifecycle cases.

## Remaining work

- Run the native Program on a test Miniserver and measure interpreter, memory, timing and response-file behaviour.
- Verify HTTPS trust, authentication, error responses, startup, restart and reconnect behaviour (running on Loxone Hardware).
- Complete continuous brightness, colour-picker and independent RGBW control, with priority indication and operator displays (running on Loxone Hardware).
- Complete media discovery, playlist coverage and handover between stored playback and live lighting control (running on Loxone Hardware).
- Validate the complete installation with customer test cases before recommending production use or seeking Loxone Library approval.

## Feedback

Use [GitHub Issues](https://github.com/advatekcommunitylabs/PixLite-Mk3-Loxone/issues) to share requirements, reproducible problems and test results. Include the Miniserver model, Loxone Config version, PixLite model and firmware, steps taken and observed result. Remove passwords, device identities, installation details and other private information before posting.

This repository is for development feedback. Loxone has not endorsed this project or approved it for the Library at this point. A redistribution licence has not yet been selected.


## Local development checks

Run `python -m unittest discover -s tests -v`.

The C decoder and lifecycle tests require host-only adapters. From a Visual Studio developer prompt, create `.local`, then compile `tests\native_core_host.c` and `tests\native_driver_host.c` with `cl /nologo /TC /D_CRT_SECURE_NO_WARNINGS`, using `/Fe:` and `/Fo:` paths inside `.local`. Set `PXL_NATIVE_CORE_EXE` and `PXL_NATIVE_DRIVER_EXE` to the resulting executable paths before running the tests. Without them, the native host tests are explicitly skipped. These executables are never installed on a PixLite or Miniserver.

To generate a project, save a new empty Config project and run `python tools/build_native.py --baseline PATH_TO_EMPTY_PROJECT --output OUTPUT.Loxone --channels 3`. Choose 3, 4 or 5 channels to match the configured colour type. Add `--telemetry` to include the disabled polling Program. The generator requires a genuine empty Config export because the complete Config document schema is not a published integration API.

`tools/capture_baseline.py` is an optional read-only bench tool. It requires explicit, time-limited device permission and a local receipt containing `started_utc`, `traffic_stop_utc` and `target_ips`. Keep receipts and raw captures in excluded local storage. Previous access does not authorise another session.

## References

- [Loxone templates](https://www.loxone.com/enen/kb/templates/).
- [Official Loxone HTTP command example](https://www.loxone.com/enen/kb/qmotion-blinds/), used as a serialization reference.

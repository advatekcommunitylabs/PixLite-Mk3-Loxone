# Follow-up validation, 29 October 2026

This follow-up bench session used read-only controller requests. It did not modify configuration, media, network, firmware, identify or operational modes.

Fresh version and constants matched the expected A4-S Mk3 and E16-S Mk3 identities, both running 3.15.0-Beta0. Full read-only baselines were captured separately from the previous session. Local addresses, MAC identities and raw snapshots remain in excluded local storage.

The session ended with zero device writes and zero background clients. Final version, constants, full configuration including saved state, full status and catalogue metadata exactly matched this session's baseline. Identify state was preserved on both controllers. Media file contents were not rehashed.

Config and test processes were closed after validation. Further work was limited to local source review.

Filtered `constantRead` and `statisticRead` requests were acknowledged with matching IDs on both devices. Reply sizes were 357/229 bytes for A4 capabilities/statistics and 360/122 bytes for E16 capabilities/statistics. The exact filtered response bodies were passed through a host build of the new native C decoder:

| Device | Decoder result |
| --- | --- |
| A4-S Mk3 | Temperature 27 C; bank 24.203 V, subject to ordinary float precision; four `fuseGood` flags true and four `Good` protection states |
| E16-S Mk3 | Temperature 28 C; zero monitored banks and no powered-output fuse telemetry, reported as unsupported |

Twenty-three local unittest cases pass with both C adapters enabled. One case includes fourteen deterministic driver scenarios: normal polling, default-disabled operation, disable after connection, invalid commissioned MAC, timeout with an old file, wrong response ID, JSON API error, connection loss, clock rollback, interval increase without extending cached validity, identity mismatch, truncated file, missing values after a valid sample, and an embedded NUL followed by trailing data. These replace SPS/file functions on the PC. They do not run a Loxone interpreter or HTTP client.

Config 17.2.10.21 established the `CmdAnswer`, `Analog` and `NoEmpty` attribute names through local property edits and save/readback. The generated native telemetry project opened with its Code16 Program, preserved script newlines, text output connection, `<v>` POST body and reply path. Config inferred a text command (`Tx=true`) and text OutputRef. Enable and commissioned MAC inputs remain disconnected. The target remains loopback HTTPS. No Miniserver was available.

No native-runtime, TLS, password-authentication, Loxone App display, fault injection or physical LED qualification is claimed. The [native telemetry qualification checklist](native-telemetry.md) remains open. Customer pilot recipients are unconfirmed; no package or message has been sent.

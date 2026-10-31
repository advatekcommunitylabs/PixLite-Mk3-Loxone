# Validation record, 28 October 2026

This record covers a command-template checkpoint, not a complete native integration or a release qualification.

## Device protocol bench

Tests used two local controllers in a time-limited bench session. No background client was left running. Device identities, addresses, configuration snapshots and raw request/response journals are excluded from this repository.

| Device | Observed firmware | Evidence |
| --- | --- | --- |
| PixLite A4-S Mk3 | 3.15.0-Beta0 | API v1.9 admitted; intensity 10 percent read back as factor 26; commissioned RGBWX static colour; Freeze, Blank and Live actual state readback; existing scene recalled; pause/resume acknowledged |
| PixLite E16-S Mk3 | 3.15.0-Beta0 | API v1.9 admitted; intensity 10 percent read back as factor 26; commissioned RGB static colour; Freeze, Blank and Live actual state readback |

Both devices exposed operator access without a password during this bench. Password authentication and TLS were not tested. Tests used direct HTTP POST from a manual diagnostic, not a Miniserver. Physical LED output was not observed. Playlist recall and every transport variant were not exercised.

The A4 returned approximately 26 degrees Celsius, one bank at approximately 24.2 V and four `fuseGood: true` values with `Good` status. The E16 returned approximately 28 degrees Celsius and advertised no powered-output telemetry. No eFuse trip/reset, fault injection or voltage excursion was tested. Fuse status does not establish electronic protection on every model.

Each controller was restored to its original Live mode, mode parameters, programmed intensity factors/priorities and identify state. Final readback matched the complete configuration including its saved flag, and scene/playlist catalogue metadata. Configuration, media, network and firmware were not written. Scene file contents were not downloaded or hashed.

## Native Config

Official stable Config 17.2.10.21 was installed from the signed Loxone installer. A new empty project was saved as the schema baseline. The generator added 42 unwired Virtual Output Commands with a loopback HTTPS target.

Config opened and saved the draft. It was then closed and reopened from disk. All 42 JSON bodies, POST method values and empty off commands survived serialization. The Live command property panel visibly showed `/v1.9/?user=oper`, its JSON body and POST. The connector panel visibly showed `https://127.0.0.1:4443`. This establishes document loading and selected property interpretation, not successful network execution by Loxone.

No Miniserver was available. Feedback processing, stale-data handling, dynamic controls, reconnect behaviour, TLS trust and Miniserver generation/version compatibility remain unqualified. No customer package was sent and no Loxone Library submission was made.

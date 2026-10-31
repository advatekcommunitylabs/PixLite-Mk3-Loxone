# Native telemetry candidate

This is an experimental Miniserver Program plus Virtual HTTP Output candidate. It is disabled by default and is not ready for customer distribution. The host tests exercise the same decoder and polling logic, with SPS and file functions replaced by test adapters. They do not execute Loxone's interpreter, HTTP stack, scheduler or filesystem.

The generated `examples/PixLite-SHOWTime-Telemetry-DRAFT.Loxone` adds one read-only POST command and one Code16 Program to the original 42 command definitions. The Program's Txt1 output supplies complete JSON bodies to the dedicated command. Its reply path is `/user/pixlite-telemetry.json`. The target remains loopback HTTPS. The enable and expected-MAC inputs remain disconnected.

The Program sends only `constantRead` and `statisticRead`. It rechecks the commissioned MAC and capabilities before each telemetry sample. It checks the response method and ID, rejects JSON error members, duplicate keys, malformed/truncated data and replies beyond its size/depth/token limits. An old file with another ID cannot renew data validity. The next ID avoids the cached ID and advances beyond it when the Program is armed. Cross-restart delivery races and ID wrap are still qualification cases, not a proved generation fence.

## Inputs and outputs

| Pin | Meaning |
| --- | --- |
| T1 | Commissioned MAC, exactly 12 uppercase hexadecimal digits, no separators |
| I1 | Enable. Leave disconnected until an engineer has qualified this candidate on a test Miniserver |
| I2 | Poll interval in seconds, 10 to 300; default 30 |
| Txt1 | Read-only JSON requests, linked to the dedicated HTTP output |
| Txt2 | Temperature and bank-voltage text, including explicit unavailable/unsupported states |
| Txt3 | Per-port physical fuse flag and protection status, kept separate |
| O1 | Fresh matching telemetry reply accepted. This does not mean that every sensor is supported or healthy |
| O2 | Temperature in degrees Celsius; -9999 when unavailable |
| O3 | Temperature validity, 0 or 1 |
| O4 to O11 | Input-bank voltages 1 to 8, in volts; -9999 when unavailable |
| O12 | Bank-validity bitmap; bit 0 corresponds to bank 1 |
| O13 | Powered pixel-port count; 0 means unsupported, -1 means unavailable |
| Etxt | Loxone interpreter error output; monitor separately from O1 |

Show numeric values only while O1 and their validity flag/bitmap bit are set. The -9999 marker is not a measurement and must not feed voltage/temperature alarms as a real value. Txt2 and Txt3 already describe unavailable states. The candidate admits up to 32 pixel ports and 8 input banks. Larger capability counts are rejected. String escapes are rejected rather than partially decoded. This deliberately limited parser only consumes small, filtered protocol replies.

Each poll invalidates the previous sample, then requests capabilities and statistics in sequence. A missing matching reply fails after more than five seconds. A sample also expires after the interval captured when it was received plus five seconds; increasing the interval cannot extend an existing sample's lifetime. Disabling clears readings and admits no new request. Native in-flight cancellation after disable still needs Miniserver validation.

## Required native qualification

1. Verify PicoC syntax, bounded memory/CPU use, Etxt handling and clean enable/disable on a test Miniserver. Config opens and serializes the script but does not prove execution. Loxone documents a maximum of eight Program blocks and a limited C interpreter.
2. Verify Txt1 substitution, first-send behavior, POST framing, operator password handling, HTTPS trust and non-200 responses. Saving a reply body does not itself expose the HTTP status to this parser. Do not bypass certificate verification or silently change transport.
3. Verify reply-file location, complete-write/read behavior and recovery from truncated files, file-write failure, restart, clock changes, delayed replies and ID wrap. Use a unique reply path in both the Program and HTTP command for every instance.
4. Measure SD-card write cost before selecting the poll interval. The design stores two HTTP replies per poll. No RAM-backed path is assumed or claimed.
5. Add commissioned Loxone App displays with validity gating, test fault presentation and retain physical fuse versus electronic protection semantics. No fault injection was performed on the bench devices.

These are release and pilot-readiness gaps. No engineer or customer should interpret host-side passing tests as completed native qualification.

## Primary references

- Advatek Lighting, PixLite Mk3 API v1.9, V20260617, 17 June 2026: Tables 29 to 30 and 70 to 71 define filtered reads. The exact versioned original is retained outside this repository.
- [Loxone custom script manual](https://updatefiles.loxone.com/KnowledgeBase/Online/Common/Documents/CustomScriptProgramming.pdf), accessed 29 October 2026: Program functions, file functions and interpreter limits.
- [Loxone Program documentation](https://www.loxone.com/plpl/kb/program/), accessed 29 October 2026: eight Program blocks, three text outputs and thirteen numeric outputs.
- [Loxone scripting documentation](https://www.loxone.com/eses/kb/programacion-script/), accessed 29 October 2026: scripts require the configuration to be saved to a Miniserver.
- [Flexum GmbH native POST example, V1.1](https://api.library.loxone.com/downloader/file/2733/Instruction%20Live-Data_FlexumShare%20platform_V1.1.pdf), accessed 29 October 2026: complete text body substitution through `<v>`.
- Native `CmdAnswer`, `Analog` and `NoEmpty` attribute names were established by property edits and save/readback in Config 17.2.10.21. The wiring schema follows Loxone's official QMotion project, linked in the main README.

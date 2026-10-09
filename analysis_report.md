# Analysis report — `client.luac`

## File identification

| Field | Value |
| --- | --- |
| Path | `client.luac` (untouched original preserved) |
| Size | 17830 bytes |
| MD5 | `e2e9d5b4e62aed244c93ba1f16c5c655` |
| SHA1 | `408d1db83b6f606cf13e02e6bb17ae9ea4179452` |
| SHA256 | `0cd5d38d4966b103876ad45854f5ddcce025863ece76bcb03cbb61c0d6009581` |
| First byte | `0x1C` |
| Entropy | ~7.99 bits/byte (ciphertext) |

`0x1C` is MTA’s `IsLuaObfuscatedScript` marker (`SharedUtil::IsLuaObfuscatedScript`). Standard Lua 5.1 compiled chunks start with `0x1B 'Lua'`.

This is **not** a raw Lua dump. It is an official `luac.mtasa.com` signed/encrypted client script.

## Bytecode format

After RSA decryption the payload is a little-endian Lua **5.1** chunk:

```
1B 4C 75 61 51 00 01 04 04 04 08 00
ESC Lua  5.1  fmt LE  int=4 size_t=4 insn=4 number=8 float
```

Source name embedded in the prototype: `@client.lua`.

## Protection analysis

### Layer 1 — signed MTA footer (157 bytes)

Trailer layout (from `netc.dll` parse at `0x10033240` / ByteRevenant Gafnium):

| Offset in trailer | Field |
| --- | --- |
| 0..7 | unused / reserved |
| 8..80 | XOR-obfuscated header (73 bytes) |
| 81 | magic `0xF14A55B7` |
| 85 | header offset (`filesize - 157`) |
| 89 | checksum of `data[0 .. filesize-69)` |
| 93..156 | 64-byte RSA signature block |

Header XOR (byte `i` in the 73-byte window):

```
mask = ((i % 12)²) XOR 0x5D XOR (1 << (i & 7))
```

Decoded header from this file:

| Field | Value |
| --- | --- |
| Compiled at | 2026-09-07 10:10:47 |
| Uploader IP | 1.1.1.1 |
| Min host version | `1.3.4-0.00000` |
| Min server run | `1.5.6-9.18728` |
| Min client run | `1.5.6-9.18728` |
| Encryption flag | 1 (bytecode RSA-encrypted) |
| Obfuscation level | **3** (`1.5.6-9.18728` ⇒ “Most”) |

Checksum matched (`0x00225CB1`).

### Layer 2 — RSA-512 of the Lua dump

- Public exponent `65537`
- 512-bit modulus from netc.dll (`01000100` + 64-byte little-endian `n`)
- Skip 5-byte prefix (`1C 4D 76 62 52` / `0x1C` + `MvbR`)
- Last 4 bytes of the inner blob = original plaintext length (`17383`)
- 64-byte blocks, public-key raw transform (little-endian integer), 63 payload bytes kept per block

RSA output starts with `\x1bLuaQ` and contains `@client.lua`.

### Layer 3 — LuaQ bytecode obfuscation (level 3)

Normalized with the MTA LuaQ table:

- String lengths pack a XOR key in the high byte; payload XOR’d with a 256-byte crypt table
- Leading `OP 0x27` instruction decrypts the code array in reverse
- Extra opcodes `0x26` (NOP) and `0x28` (FAIL) stripped
- `sBx > 60000` jump fix (`120000 - sBx`)

Normalizer stats on this file: **174 strings**, **37 code blocks**, **2 NOPs**, **48 jumps**.

After normalization the chunk is standard Lua 5.1 and parses cleanly:

- 40 function prototypes
- 1301 instructions
- 218 string constants
- lineinfo present (original source ~485 lines)
- local names / upvalue names stripped

## Tools and techniques used

1. Header/entropy forensics (Python).
2. Format ID against MTA `IsLuaObfuscatedScript` / `IsLuaCompiledScript`.
3. Trailer parser reversed from `netc.dll` `DeobfuscateScript`.
4. RSA-512 public-key transform (pycryptodome `pow`).
5. LuaQ normalizer (crypt table, XOR code blocks, NOP strip).
6. Custom Lua 5.1 undump + disassembly (`artifacts/disassembly.txt`).
7. Manual CFG reconstruction of all 40 prototypes.

Java/unluac was not runnable here (no JRE; GitHub release CDN blocked). Wine/`netc.dll` was not runnable (Linux sandbox, no Wine). Decryption was reimplemented instead of calling the DLL.

## Recovery results

The client is a **fullscreen rain overlay**:

1. On `onClientResourceStart`, compile an HLSL technique `BlackScreenRain`, create a screen source, and load up to **317** textures from `frames/1 (%d).png`.
2. On `onClientRender` (priority `low-999999999`):
   - Fade `gIntensity` toward 1 when raining (`getRainLevel() > 0.02` or weather 8/16), else 0.
   - Cycle rain-drop textures at 30 FPS.
   - `dxUpdateScreenSource` + `dxDrawImage` the shader over the whole screen.
3. On `onClientResourceStop`, destroy elements and remove the render handler.

Debug prefix: `[Rain]`.

Recovered artifacts:

| File | Role |
| --- | --- |
| `client_recovered.lua` | Level B source (original obfuscation retained) |
| `client_readable.lua` | Level C readable equivalent |
| `artifacts/client_decrypted.luac` | RSA-decrypted Lua 5.1 dump (still LuaQ) |
| `artifacts/client_normalized.luac` | Standard Lua 5.1 after LuaQ normalize |
| `artifacts/disassembly.txt` | Full prototype disassembly |
| `tools/mta_luac_decrypt.py` | Reproducible decrypt + normalize |

## Unresolved sections

- Exact original whitespace, comments, and local names (not in the dump).
- The 70-instruction dummy is `while l == 2` (EQ A=0 vs 2, JMP to RETURN). Body is unrolled ADD/DIV; F0 never calls it.
- Two anti-analysis helpers (`bump(nil) == 255`, `dead(nil, nil)` with `0xDEAD`) are dead at runtime; they are preserved in `client_recovered.lua`. `dead` is `a and b and a==b and a==57005`.
- 520 trailing bytes after the Lua chunk in the RSA plaintext were unused padding; ignored.
- Texture files themselves are not in this repository; only the loader path format is known.

## Confidence

| Item | Confidence |
| --- | --- |
| File is official MTA luac encryption | High |
| RSA + LuaQ decrypt to valid Lua 5.1 | High (header, checksum, `\x1bLua`, parse) |
| Event names, shader HLSL, config numbers | High (string constants) |
| Control flow / API call graph | High (full disassembly) |
| Original local names / comments | None (stripped) |
| Byte-identical original `.lua` text | None — Level B reconstruction |

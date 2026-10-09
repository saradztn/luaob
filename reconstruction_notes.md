# Reconstruction notes — `client.luac` → `client_recovered.lua`

Lua 5.1 comparison / TEST cheat-sheet used throughout:

| Insn | Skip next JMP when |
| --- | --- |
| `EQ A=0 B C` | `RK(B) == RK(C)` |
| `EQ A=1 B C` | `RK(B) ~= RK(C)` |
| `LT/LE A=0` | comparison true |
| `LT/LE A=1` | comparison false |
| `TEST A C=0` | `R(A)` is truthy |
| `TEST A C=1` | `R(A)` is falsy |

Level A = byte-identical original source (impossible: locals/comments stripped).  
Level B = control flow + constants + obfuscated identifiers from the dump.  
Level C = readable rename (`client_readable.lua`).

`client_recovered.lua` is **Level B**. Nested factories (F24/F29/F31) are kept where they match the prototype tree; F1’s ADD/DIV body is unrolled as in the dump (lineinfo is a single source line).

---

## Prototype map

Source name in the chunk: `@client.lua`. linedefined/lastlinedefined span **1–485**. 40 prototypes, 1301 instructions.

| Proto | Lines | Role | Recovery |
| --- | --- | --- | --- |
| F0 | 1–485 | chunk: tables, closures, two `addEventHandler`s | B |
| F1 | 1 | unused `while l == 2` ADD/DIV trap | B (unrolled) |
| F2 | 37–43 | `callF(id, ...)` via upvalue API table | B |
| F3 | 45–49 | `bind(id)` → F4 | B |
| F4 | 46–48 | `return callF(id, ...)` | B |
| F5 | 77–84 | `table.concat(string.char(...))` | B |
| F6 | 102–128 | config table + getters F7–F17 | B |
| F7 | 115 | `raw[k]` | B |
| F8–F17 | 117–126 | `maxTex`…`zero` thunks | B |
| F18 | 133–138 | weather set `{8,16} → true` | B |
| F19 | 143–183 | HLSL concat `BlackScreenRain` | A (string Ks) |
| F20 | 213–218 | `bump(v)` identity + dead `+1` | B |
| F21 | 220–225 | `dead(a,b)` / `0xDEAD` | B |
| F22 | 228–230 | `valid(el)` = `el and isElement(el)` | B |
| F23 | 233–235 | `ods("[Rain] "..tostring(msg), level or 3)` | B |
| F24 | 238–244 | path factory | B |
| F25 | 241–243 | `sfmt(fmt, folder, i)` | B |
| F26 | 247–269 | CLEANUP / destroy / IDLE | B |
| F27 | 272–295 | load `frames/1 (%d).png` 1..317 | B |
| F28 | 298–355 | INIT / start | B |
| F29 | 358–373 | rain factory | B (inlined as `isRaining`) |
| F30 | 362–372 | rain predicate | B |
| F31 | 376–394 | fade factory | B |
| F32 | 383–393 | `fade(cur, target, dt)` | B |
| F33 | 400–405 | RUNNING ∧ valid(shader) ∧ valid(screen) | B |
| F34 | 408–417 | intensity step | B |
| F35 | 420–432 | frame step (30 fps) | B |
| F36 | 435–446 | draw | B |
| F37 | 449–457 | render pipeline | B |
| F38 | 460–474 | resource start | B |
| F39 | 477–481 | resource stop | B |

---

## F0 — chunk layout (registers)

```
R0  F1 dummy          (never called)
R1  _   API alias table   (csh, css, …)
R2  __  empty table       (never read)
R3  N   string table      (evStart, pTex, …)
R4  F   numeric API map   1=dxCreateShader … 20=string.format
        then overwritten by F5 (chars)
R5  bind / later wx
R6  shader source fx
R7  ST  state enum
R8  S   runtime
R9–R22 closures as below
```

API map (F[n] = GETGLOBAL, then `_[alias] = bind(n)`):

| n | global | alias |
| --- | --- | --- |
| 1 | dxCreateShader | csh |
| 2 | dxCreateScreenSource | css |
| 3 | dxCreateTexture | ctx |
| 4 | dxSetShaderValue | ssv |
| 5 | dxUpdateScreenSource | uss |
| 6 | dxDrawImage | dim |
| 7 | getTickCount | gtc |
| 8 | getWeather | gw |
| 9 | getRainLevel | grl |
| 10 | guiGetScreenSize | gss |
| 11 | addEventHandler | aeh |
| 12 | outputDebugString | ods |
| 13 | fileExists | fe |
| 14 | isElement | ie |
| 15 | destroyElement | de |
| 16 | removeEventHandler | reh |
| 17 | tocolor | tc (bound, never called) |
| 18 | math.min | mmin |
| 19 | math.max | mmax |
| 20 | string.format | sfmt |

Char-code strings (F5):

| key | codes | value |
| --- | --- | --- |
| evStart | 111,110,67,108,105,101,110,116,82,101,115,111,117,114,99,101,83,116,97,114,116 | onClientResourceStart |
| evRender | 111,110,67,108,105,101,110,116,82,101,110,100,101,114 | onClientRender |
| evStop | …83,116,111,112 | onClientResourceStop |
| pTex | 103,84,101,120,116,117,114,101 | gTexture |
| pSrc | 103,83,99,114,101,101,110,83,111,117,114,99,101 | gScreenSource |
| pCrop | 103,67,114,111,112,72,101,105,103,104,116 | gCropHeight |
| pInt | 103,73,110,116,101,110,115,105,116,121 | gIntensity |
| folder | 102,114,97,109,101,115 | frames |
| fmtPath | 37,115,47,49,32,40,37,100,41,46,112,110,103 | `%s/1 (%d).png` |

Plain string constants (not char-coded): `"[Rain] "`, debug messages, HLSL fragments, `"low-999999999"`, state field names `lIlIl`…`llIIl`.

Runtime `S` fields (original keys, not invented):

| key | meaning |
| --- | --- |
| state | IDLE/INIT/RUNNING/ERROR/CLEANUP |
| shader / screen | elements |
| textures | array |
| lIlIl | frame index |
| lIIll | intensity |
| lllIl | written 0 on cleanup; never read |
| lIlII / lIIlI | screen w/h |
| lllII | last frame tick |
| lIIII | written 0 at init; never read |
| llIIl | last fade tick |

Chunk tail:

```
aeh(evStart, resourceRoot, F38)
aeh(evStop,  resourceRoot, F39)
```

---

## F1 dummy

```
EQ A=0  l, 2
JMP RETURN          -- taken when l ~= 2
-- 22× (ADD I,l; ADD I,l; DIV l,I) then one extra ADD
JMP loop
RETURN I
```

So the loop condition is **`l == 2`**, not `l ~= 2`. Never invoked from F0. Reconstruction keeps the unrolled arithmetic (one source line in lineinfo).

---

## F2–F4 API bind

```lua
-- F2 upvalue = numeric API table
local fn = api[id]
if type(fn) == "function" then return fn(...) end
return nil

-- F3
return function(...) return F2(id, ...) end
```

---

## F6 config

Sparse table, keys 161–170 (obfuscator numeric keys, not sequential 1..n):

| key | value | getter |
| --- | --- | --- |
| 161 | 317 | maxTex |
| 162 | 30 | fps |
| 163 | 0.5 | crop |
| 164 | 0.45 | fade |
| 165 | 1000 | msec |
| 166 | 0.001 | eps (never read after init) |
| 167 | 0.02 | rainThres |
| 168 | 0.001 | drawEps |
| 169 | 1 | one |
| 170 | 0 | zero |

F7 is `function(k) return raw[k] end`; F8–F17 tailcall it with the numeric key.

---

## F19 shader

Seven CONCAT groups, `table.concat(parts)`. Technique name **BlackScreenRain**, ps_2_0. Uniforms match pTex/pSrc/pCrop/pInt. Screen-space rain: luma of a cropped rain-video sample displaces the screen source, then screen-blend lerp by `gIntensity`. Early-out when `gIntensity <= 0.001` (same numeric as `eps`/`drawEps`).

String fragments are Level A (verbatim Ks). Newlines/spaces inside fragments are as compiled; surrounding Lua concat layout is Level B.

---

## F20 / F21 anti-analysis

**F20 `bump(v)`**

```
EQ A=0 v, nil     -- if v == nil, fall into type check; else return v
type(v) == "number" → return v+1
return v
```

`nil` is never a number, so `bump` is identity. F28 calls `bump(nil) == 255` and would zero width; the store never happens.

**F21 `dead(a,b)`**

```
EQ A=1 a, nil     -- require a ~= nil
EQ A=1 b, nil     -- require b ~= nil
EQ A=0 a, b       -- require a == b
EQ A=0 a, 57005   -- require a == 0xDEAD
return true / false
```

Equivalent to `a ~= nil and b ~= nil and a == b and a == 57005`.  
F27/F30 call `dead(nil, nil)` → always false. The `n = -1` / `return false` arms are dead.

---

## F22 `valid`

```
TEST C=0 el        -- falsy → false
ok = _["ie"](el)
TEST C=1 ok        -- truthy → return ok; else false
```

`return el and isElement(el)`.

---

## F23 log

`ods("[Rain] " .. tostring(msg), TESTSET(level) or 3)`.

Messages (plain Ks): `Screen size failed`, `Shader failed`, `ScreenSource failed`, `No textures found`, `Loaded: `, `Running - ` / ` textures`, `Stopped`. Error logs use level 1; info uses 3.

---

## F26 cleanup

1. `S.state = CLEANUP`
2. for i=1,#textures: if valid then destroy; `tex[i] = nil`
3. `S.textures = {}`
4. destroy shader/screen if valid
5. shader/screen = false; lIlIl=1; lIIll=0; lllIl=0; llIIl=nil
6. `S.state = IDLE`

Does not touch lIlII/lIIlI/lllII/lIIII.

---

## F27 loadTextures

```
n = 0
maxTex = cfg.maxTex()
if dead(nil,nil) then n = -1 end          -- dead
for i = 1, maxTex do
  path = filePath(i)
  TEST C=0 fileExists(path)
  JMP FORLOOP                              -- missing file → continue, not break
  tex = ctx(path)
  TEST C=0 tex
  JMP FORLOOP
  textures[#textures+1] = tex
  n = n + 1
end
log("Loaded: "..n, 3)
return n > 0                               -- LT A=1  0, n  →  0 < n
```

---

## F28 start

```
state = INIT
w, h = gss()                               -- nret=2
if not w or not h then log err; ERROR; return false end
if bump(nil) == 255 then w = 0 end         -- dead
lIlII, lIIlI = w, h
shader = csh(fx)
if not shader then log; ERROR; return false end
screen = css(w, h)
if not screen then log; cleanup(); ERROR; return false end
if not loadTextures() then log; cleanup(); ERROR; return false end
ssv(shader, pSrc, screen)
ssv(shader, pCrop, cfg.crop())
ssv(shader, pInt,  cfg.zero())
if textures[1] then ssv(shader, pTex, textures[1]) end
lIIll = zero(); llIIl = gtc(); lIlIl = 1; lllII = gtc()
state = RUNNING
log("Running - "..#textures.." textures", 3)
return true
```

Screen-size TEST: `TEST C=0 w` fail-path; then `TEST C=1 h` success-path. Shader/screen/load use `TEST C=1` (fail if falsy).

---

## F30 isRaining

```
rain = grl(); if not rain then rain = zero() end
if dead(nil,nil) then return false end     -- dead
if rainThres() < rain then return true end -- LT A=0 thres, rain
w1, w2 = gw()                              -- nret=2
return wx[w1] == true or wx[w2] == true    -- EQ A=1 vs true
```

Weathers 8 and 16 are GTA SA rain weathers.

F29 is a factory that closes over `cfg.rainThres` and returns F30. Reconstruction inlines that as `isRaining` (same upvalues, one less nested function).

---

## F32 fade

```
step = dt * fade()
if cur < target then return mmin(one(), cur + step) end
if target < cur then return mmax(zero(), cur - step) end
return cur
```

---

## F33 / F34 / F35 / F36 / F37

**F33 alive:** `state == RUNNING` (`EQ A=1` → not-equal returns false) then `valid(shader)` then `valid(screen)`.

**F34:** `dt = (now - llIIl) / msec()`; `llIIl = now`; target = raining ? one : zero (`TEST` on F30); `lIIll = fadeTo(lIIll, target, dt)`; `ssv(shader, pInt, lIIll)`.

**F35:** `interval = msec()/fps()`. `LE A=0 interval, (now-lllII)` → body when `dt >= interval`. Then `lIlIl = (lIlIl % #textures) + 1`; `lllII = now`; if `valid(tex)` then `ssv(pTex, tex)`.

**F36:** `LE A=0 lIIll, drawEps` → return (no draw). Else `uss(screen, true)` then `dim(0, 0, lIlII, lIIlI, shader)` — five args, no color/rotation.

**F37:** `if not steps[1]() then return end`; `now = gtc()`; `steps[2](now)`; `steps[3](now)`; `steps[4]()`.

---

## F38 / F39 events

**F38** (`EQ A=0` state, RUNNING then fall into RETURN):

```
if state == RUNNING then return end
start()
if state == RUNNING then
  aeh(evRender, root, onRender, false, "low-999999999")
end
```

**F39:** `reh(evRender, root, onRender)`; `cleanup()`; `log("Stopped", 3)`.

---

## What was not recovered

- Original local names (debug stripped; only `S` field strings remain).
- Comments and exact whitespace.
- Whether F1 was a `while` or a macro-unrolled one-liner (lineinfo says line 1 only).
- Whether F29/F31 were written as factories or as nested `local function`s — bytecode has factories.
- `cfg.eps` and `S.lIIII` / `S.lllIl` purpose beyond being stored.
- Texture assets (`frames/1 (1).png` …).

---

## Behavioural equivalence

A client with this reconstruction, the same `frames/` PNGs, and MTA 1.5.6+ should:

1. Build the rain shader and a full-screen source on resource start.
2. Load every existing `frames/1 (i).png` for i in 1..317 (gaps skipped).
3. Fade intensity in when `getRainLevel() > 0.02` or weather is 8/16.
4. Cycle textures at 30 fps and draw the shader over the framebuffer while intensity > 0.001.
5. Tear down on resource stop.

That is the observable contract of the dump. It is **not** a claim of byte-identical original source.

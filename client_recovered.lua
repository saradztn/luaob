--[[
  Level B reconstruction of client.luac (MTA:SA / luac.mtasa.com, LuaQ level 3).
  Identifiers, string payloads, numeric config, event names, shader source,
  and control flow were recovered from the decrypted Lua 5.1 prototype tree.
  Original comments, whitespace, and local names (stripped at compile time)
  are not present in the bytecode and are not claimed here.
]]

local function lI(l, I)
    -- F1: EQ A=0 vs 2 then JMP to RETURN. Body runs only while l == 2.
    while l == 2 do
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
        I = I + l
        l = l / I
        I = I + l
    end
    return I
end

local _ = {}
local __ = {}
local N = {}
local F = {}

F[1] = dxCreateShader
F[2] = dxCreateScreenSource
F[3] = dxCreateTexture
F[4] = dxSetShaderValue
F[5] = dxUpdateScreenSource
F[6] = dxDrawImage
F[7] = getTickCount
F[8] = getWeather
F[9] = getRainLevel
F[10] = guiGetScreenSize
F[11] = addEventHandler
F[12] = outputDebugString
F[13] = fileExists
F[14] = isElement
F[15] = destroyElement
F[16] = removeEventHandler
F[17] = tocolor
F[18] = math.min
F[19] = math.max
F[20] = string.format

local function callF(id, ...)
    local fn = F[id]
    if type(fn) == "function" then
        return fn(...)
    end
    return nil
end

local function bind(id)
    return function(...)
        return callF(id, ...)
    end
end

_[ "csh" ] = bind(1)
_[ "css" ] = bind(2)
_[ "ctx" ] = bind(3)
_[ "ssv" ] = bind(4)
_[ "uss" ] = bind(5)
_[ "dim" ] = bind(6)
_[ "gtc" ] = bind(7)
_[ "gw" ] = bind(8)
_[ "grl" ] = bind(9)
_[ "gss" ] = bind(10)
_[ "aeh" ] = bind(11)
_[ "ods" ] = bind(12)
_[ "fe" ] = bind(13)
_[ "ie" ] = bind(14)
_[ "de" ] = bind(15)
_[ "reh" ] = bind(16)
_[ "tc" ] = bind(17)
_[ "mmin" ] = bind(18)
_[ "mmax" ] = bind(19)
_[ "sfmt" ] = bind(20)

local function chars(...)
    local out = {}
    local src = { ... }
    for i = 1, #src do
        out[i] = string.char(src[i])
    end
    return table.concat(out)
end

N["evStart"] = chars(111, 110, 67, 108, 105, 101, 110, 116, 82, 101, 115, 111, 117, 114, 99, 101, 83, 116, 97, 114, 116)
N["evRender"] = chars(111, 110, 67, 108, 105, 101, 110, 116, 82, 101, 110, 100, 101, 114)
N["evStop"] = chars(111, 110, 67, 108, 105, 101, 110, 116, 82, 101, 115, 111, 117, 114, 99, 101, 83, 116, 111, 112)
N["pTex"] = chars(103, 84, 101, 120, 116, 117, 114, 101)
N["pSrc"] = chars(103, 83, 99, 114, 101, 101, 110, 83, 111, 117, 114, 99, 101)
N["pCrop"] = chars(103, 67, 114, 111, 112, 72, 101, 105, 103, 104, 116)
N["pInt"] = chars(103, 73, 110, 116, 101, 110, 115, 105, 116, 121)
N["folder"] = chars(102, 114, 97, 109, 101, 115)
N["fmtPath"] = chars(37, 115, 47, 49, 32, 40, 37, 100, 41, 46, 112, 110, 103)

local function makeCfg()
    local raw = {}
    raw[161] = 317
    raw[162] = 30
    raw[163] = 0.5
    raw[164] = 0.45
    raw[165] = 1000
    raw[166] = 0.001
    raw[167] = 0.02
    raw[168] = 0.001
    raw[169] = 1
    raw[170] = 0
    local function get(k)
        return raw[k]
    end
    local cfg = {}
    cfg.maxTex = function()
        return get(161)
    end
    cfg.fps = function()
        return get(162)
    end
    cfg.crop = function()
        return get(163)
    end
    cfg.fade = function()
        return get(164)
    end
    cfg.msec = function()
        return get(165)
    end
    cfg.eps = function()
        return get(166)
    end
    cfg.rainThres = function()
        return get(167)
    end
    cfg.drawEps = function()
        return get(168)
    end
    cfg.one = function()
        return get(169)
    end
    cfg.zero = function()
        return get(170)
    end
    return cfg
end

local function rainWeathers()
    local set = {}
    local ids = { 8, 16 }
    for i = 1, #ids do
        set[ids[i]] = true
    end
    return set
end

local function shaderSource()
    local parts = {}
    parts[1] = "texture gTexture;\n" ..
        "texture gScreenSource;\n" ..
        "float gCropHeight = 0.5;\n" ..
        "float gIntensity  = 0.0;\n"
    parts[2] = "sampler2D VideoSampler  = sampler_state" ..
        "{ Texture = <gTexture>;" ..
        "  MinFilter = LINEAR; MagFilter = LINEAR; };\n" ..
        "sampler2D ScreenSampler = sampler_state" ..
        "{ Texture = <gScreenSource>;" ..
        "  MinFilter = LINEAR; MagFilter = LINEAR; };\n"
    parts[3] = "struct PSInput { float2 TexCoord : TEXCOORD0; };\n"
    parts[4] = "float4 PS_Main(PSInput IN) : COLOR0\n{\n" ..
        "    float2 uv = IN.TexCoord;\n" ..
        "    if (gIntensity <= 0.001)\n    {\n" ..
        "        float3 plain = tex2D(ScreenSampler, uv).rgb;\n" ..
        "        return float4(plain, 1.0);\n    }\n"
    parts[5] = "    float2 rainUV = float2(uv.x, uv.y * gCropHeight);\n" ..
        "    float4 vid = tex2D(VideoSampler, rainUV);\n" ..
        "    float luma = dot(vid.rgb, float3(0.299, 0.587, 0.114));\n" ..
        "    float2 offset = (float2(luma,luma) - 0.1)" ..
        " * 0.008 * gIntensity;\n" ..
        "    float3 scene = tex2D(ScreenSampler," ..
        " saturate(uv + offset)).rgb;\n"
    parts[6] = "    float3 blended = 1.0 - (1.0 - scene) * (1.0 - vid.rgb);\n" ..
        "    float3 finalCol = lerp(scene, blended, gIntensity);\n" ..
        "    return float4(finalCol, 1.0);\n}\n"
    parts[7] = "technique BlackScreenRain\n{\n" ..
        "    pass P0 { PixelShader =" ..
        " compile ps_2_0 PS_Main(); }\n}\n"
    return table.concat(parts)
end

local cfg = makeCfg()
local wx = rainWeathers()
local fx = shaderSource()

local ST = {
    IDLE = 0,
    INIT = 1,
    RUNNING = 2,
    ERROR = 3,
    CLEANUP = 4,
}

local S = {
    state = ST.IDLE,
    shader = false,
    screen = false,
    textures = {},
    lIlIl = 1,
    lIIll = 0,
    lllIl = 0,
    lIlII = 0,
    lIIlI = 0,
    lllII = 0,
    lIIII = 0,
    llIIl = nil,
}

local function bump(v)
    if v == nil then
        if type(v) == "number" then
            return v + 1
        end
    end
    return v
end

local function dead(a, b)
    -- F21: a ~= nil and b ~= nil and a == b and a == 57005 (0xDEAD).
    if a == nil then
        return false
    end
    if b == nil then
        return false
    end
    if a ~= b then
        return false
    end
    if a == 57005 then
        return true
    end
    return false
end

local function valid(el)
    if not el then
        return false
    end
    local ok = _["ie"](el)
    if not ok then
        return false
    end
    return ok
end

local function log(msg, level)
    _["ods"]("[Rain] " .. tostring(msg), level or 3)
end

local function pathOf()
    local fmt = N["fmtPath"]
    local folder = N["folder"]
    return function(i)
        return _["sfmt"](fmt, folder, i)
    end
end

local filePath = pathOf()

local function cleanup()
    S.state = ST.CLEANUP
    local tex = S.textures
    for i = 1, #tex do
        if valid(tex[i]) then
            _["de"](tex[i])
        end
        tex[i] = nil
    end
    S.textures = {}
    if valid(S.shader) then
        _["de"](S.shader)
    end
    if valid(S.screen) then
        _["de"](S.screen)
    end
    S.shader = false
    S.screen = false
    S.lIlIl = 1
    S.lIIll = 0
    S.lllIl = 0
    S.llIIl = nil
    S.state = ST.IDLE
end

local function loadTextures()
    local n = 0
    local maxTex = cfg.maxTex()
    if dead(nil, nil) then
        n = -1
    end
    for i = 1, maxTex do
        local path = filePath(i)
        if not _["fe"](path) then
            -- skip missing frame
        else
            local tex = _["ctx"](path)
            if tex then
                S.textures[#S.textures + 1] = tex
                n = n + 1
            end
        end
    end
    log("Loaded: " .. n, 3)
    return n > 0
end

local function start()
    S.state = ST.INIT
    local w, h = _["gss"]()
    if not w or not h then
        log("Screen size failed", 1)
        S.state = ST.ERROR
        return false
    end
    if bump(nil) == 255 then
        w = 0
    end
    S.lIlII = w
    S.lIIlI = h
    local shader = _["csh"](fx)
    if not shader then
        log("Shader failed", 1)
        S.state = ST.ERROR
        return false
    end
    S.shader = shader
    local screen = _["css"](w, h)
    if not screen then
        log("ScreenSource failed", 1)
        cleanup()
        S.state = ST.ERROR
        return false
    end
    S.screen = screen
    if not loadTextures() then
        log("No textures found", 1)
        cleanup()
        S.state = ST.ERROR
        return false
    end
    _["ssv"](S.shader, N["pSrc"], S.screen)
    _["ssv"](S.shader, N["pCrop"], cfg.crop())
    _["ssv"](S.shader, N["pInt"], cfg.zero())
    if S.textures[1] then
        _["ssv"](S.shader, N["pTex"], S.textures[1])
    end
    S.lIIll = cfg.zero()
    S.llIIl = _["gtc"]()
    S.lIlIl = 1
    S.lllII = _["gtc"]()
    S.state = ST.RUNNING
    log("Running - " .. #S.textures .. " textures", 3)
    return true
end

local function isRaining()
    local rain = _["grl"]()
    if not rain then
        rain = cfg.zero()
    end
    if dead(nil, nil) then
        return false
    end
    if cfg.rainThres() < rain then
        return true
    end
    local w1, w2 = _["gw"]()
    if wx[w1] == true then
        return true
    end
    if wx[w2] == true then
        return true
    end
    return false
end

local function makeFade()
    local rate = cfg.fade
    local one = cfg.one
    local zero = cfg.zero
    local mmin = _["mmin"]
    local mmax = _["mmax"]
    return function(cur, target, dt)
        local step = dt * rate()
        if cur < target then
            return mmin(one(), cur + step)
        end
        if target < cur then
            return mmax(zero(), cur - step)
        end
        return cur
    end
end

local fadeTo = makeFade()

local function alive()
    if S.state ~= ST.RUNNING then
        return false
    end
    if not valid(S.shader) then
        return false
    end
    if not valid(S.screen) then
        return false
    end
    return true
end

local function stepIntensity(now)
    local dt = (now - S.llIIl) / cfg.msec()
    S.llIIl = now
    local target
    if isRaining() then
        target = cfg.one()
    else
        target = cfg.zero()
    end
    S.lIIll = fadeTo(S.lIIll, target, dt)
    _["ssv"](S.shader, N["pInt"], S.lIIll)
end

local function stepFrame(now)
    local interval = cfg.msec() / cfg.fps()
    -- F35 LE A=0: update when interval <= (now - last), i.e. dt >= interval.
    if now - S.lllII < interval then
        return
    end
    S.lIlIl = (S.lIlIl % #S.textures) + 1
    S.lllII = now
    local tex = S.textures[S.lIlIl]
    if valid(tex) then
        _["ssv"](S.shader, N["pTex"], tex)
    end
end

local function stepDraw()
    if S.lIIll <= cfg.drawEps() then
        return
    end
    _["uss"](S.screen, true)
    _["dim"](0, 0, S.lIlII, S.lIIlI, S.shader)
end

local steps = {}
steps[1] = alive
steps[2] = stepIntensity
steps[3] = stepFrame
steps[4] = stepDraw

local function onRender()
    if not steps[1]() then
        return
    end
    local now = _["gtc"]()
    steps[2](now)
    steps[3](now)
    steps[4]()
end

local function onStart()
    if S.state == ST.RUNNING then
        return
    end
    start()
    if S.state == ST.RUNNING then
        _["aeh"](N["evRender"], root, onRender, false, "low-999999999")
    end
end

local function onStop()
    _["reh"](N["evRender"], root, onRender)
    cleanup()
    log("Stopped", 3)
end

_["aeh"](N["evStart"], resourceRoot, onStart)
_["aeh"](N["evStop"], resourceRoot, onStop)

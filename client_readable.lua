--[[
  Level C readable reconstruction of client.luac.

  Same MTA client behaviour as client_recovered.lua, with decoded strings
  and named fields. Not the original source text.
]]

local API = {
    createShader = dxCreateShader,
    createScreenSource = dxCreateScreenSource,
    createTexture = dxCreateTexture,
    setShaderValue = dxSetShaderValue,
    updateScreenSource = dxUpdateScreenSource,
    drawImage = dxDrawImage,
    getTickCount = getTickCount,
    getWeather = getWeather,
    getRainLevel = getRainLevel,
    getScreenSize = guiGetScreenSize,
    addEventHandler = addEventHandler,
    outputDebugString = outputDebugString,
    fileExists = fileExists,
    isElement = isElement,
    destroyElement = destroyElement,
    removeEventHandler = removeEventHandler,
}

local CFG = {
    maxTextures = 317,
    fps = 30,
    cropHeight = 0.5,
    fadeRate = 0.45,
    msec = 1000,
    epsilon = 0.001,
    rainThreshold = 0.02,
    drawEpsilon = 0.001,
}

local RAIN_WEATHER = {
    [8] = true,
    [16] = true,
}

local TEXTURE_FOLDER = "frames"
local TEXTURE_FMT = "%s/1 (%d).png"

local SHADER_HLSL = [[
texture gTexture;
texture gScreenSource;
float gCropHeight = 0.5;
float gIntensity  = 0.0;
sampler2D VideoSampler  = sampler_state { Texture = <gTexture>;  MinFilter = LINEAR; MagFilter = LINEAR; };
sampler2D ScreenSampler = sampler_state { Texture = <gScreenSource>;  MinFilter = LINEAR; MagFilter = LINEAR; };
struct PSInput { float2 TexCoord : TEXCOORD0; };
float4 PS_Main(PSInput IN) : COLOR0
{
    float2 uv = IN.TexCoord;
    if (gIntensity <= 0.001)
    {
        float3 plain = tex2D(ScreenSampler, uv).rgb;
        return float4(plain, 1.0);
    }
    float2 rainUV = float2(uv.x, uv.y * gCropHeight);
    float4 vid = tex2D(VideoSampler, rainUV);
    float luma = dot(vid.rgb, float3(0.299, 0.587, 0.114));
    float2 offset = (float2(luma,luma) - 0.1) * 0.008 * gIntensity;
    float3 scene = tex2D(ScreenSampler, saturate(uv + offset)).rgb;
    float3 blended = 1.0 - (1.0 - scene) * (1.0 - vid.rgb);
    float3 finalCol = lerp(scene, blended, gIntensity);
    return float4(finalCol, 1.0);
}
technique BlackScreenRain
{
    pass P0 { PixelShader = compile ps_2_0 PS_Main(); }
}
]]

local STATE = {
    IDLE = 0,
    INIT = 1,
    RUNNING = 2,
    ERROR = 3,
    CLEANUP = 4,
}

local ctx = {
    state = STATE.IDLE,
    shader = false,
    screen = false,
    textures = {},
    frameIndex = 1,
    intensity = 0,
    screenW = 0,
    screenH = 0,
    lastFadeTick = 0,
    lastFrameTick = 0,
}

local function logRain(message, level)
    API.outputDebugString("[Rain] " .. tostring(message), level or 3)
end

local function alive(el)
    return el and API.isElement(el)
end

local function texturePath(index)
    return string.format(TEXTURE_FMT, TEXTURE_FOLDER, index)
end

local function destroyAll()
    ctx.state = STATE.CLEANUP
    for i = 1, #ctx.textures do
        if alive(ctx.textures[i]) then
            API.destroyElement(ctx.textures[i])
        end
        ctx.textures[i] = nil
    end
    ctx.textures = {}
    if alive(ctx.shader) then
        API.destroyElement(ctx.shader)
    end
    if alive(ctx.screen) then
        API.destroyElement(ctx.screen)
    end
    ctx.shader = false
    ctx.screen = false
    ctx.frameIndex = 1
    ctx.intensity = 0
    ctx.lastFadeTick = nil
    ctx.state = STATE.IDLE
end

local function loadTextures()
    local loaded = 0
    for i = 1, CFG.maxTextures do
        local path = texturePath(i)
        if API.fileExists(path) then
            local tex = API.createTexture(path)
            if tex then
                ctx.textures[#ctx.textures + 1] = tex
                loaded = loaded + 1
            end
        end
    end
    logRain("Loaded: " .. loaded, 3)
    return loaded > 0
end

local function startRain()
    ctx.state = STATE.INIT
    local w, h = API.getScreenSize()
    if not w or not h then
        logRain("Screen size failed", 1)
        ctx.state = STATE.ERROR
        return false
    end
    ctx.screenW = w
    ctx.screenH = h

    local shader = API.createShader(SHADER_HLSL)
    if not shader then
        logRain("Shader failed", 1)
        ctx.state = STATE.ERROR
        return false
    end
    ctx.shader = shader

    local screen = API.createScreenSource(w, h)
    if not screen then
        logRain("ScreenSource failed", 1)
        destroyAll()
        ctx.state = STATE.ERROR
        return false
    end
    ctx.screen = screen

    if not loadTextures() then
        logRain("No textures found", 1)
        destroyAll()
        ctx.state = STATE.ERROR
        return false
    end

    API.setShaderValue(ctx.shader, "gScreenSource", ctx.screen)
    API.setShaderValue(ctx.shader, "gCropHeight", CFG.cropHeight)
    API.setShaderValue(ctx.shader, "gIntensity", 0)
    if ctx.textures[1] then
        API.setShaderValue(ctx.shader, "gTexture", ctx.textures[1])
    end

    ctx.intensity = 0
    ctx.lastFadeTick = API.getTickCount()
    ctx.frameIndex = 1
    ctx.lastFrameTick = API.getTickCount()
    ctx.state = STATE.RUNNING
    logRain("Running - " .. #ctx.textures .. " textures", 3)
    return true
end

local function isRaining()
    local rainLevel = API.getRainLevel() or 0
    if CFG.rainThreshold < rainLevel then
        return true
    end
    local weather, weather2 = API.getWeather()
    return RAIN_WEATHER[weather] == true or RAIN_WEATHER[weather2] == true
end

local function fade(current, target, dt)
    local step = dt * CFG.fadeRate
    if current < target then
        return math.min(1, current + step)
    end
    if target < current then
        return math.max(0, current - step)
    end
    return current
end

local function isRunning()
    return ctx.state == STATE.RUNNING and alive(ctx.shader) and alive(ctx.screen)
end

local function updateIntensity(now)
    local dt = (now - ctx.lastFadeTick) / CFG.msec
    ctx.lastFadeTick = now
    local target = isRaining() and 1 or 0
    ctx.intensity = fade(ctx.intensity, target, dt)
    API.setShaderValue(ctx.shader, "gIntensity", ctx.intensity)
end

local function updateFrame(now)
    local interval = CFG.msec / CFG.fps
    if now - ctx.lastFrameTick < interval then
        return
    end
    ctx.frameIndex = (ctx.frameIndex % #ctx.textures) + 1
    ctx.lastFrameTick = now
    local tex = ctx.textures[ctx.frameIndex]
    if alive(tex) then
        API.setShaderValue(ctx.shader, "gTexture", tex)
    end
end

local function drawRain()
    if ctx.intensity <= CFG.drawEpsilon then
        return
    end
    API.updateScreenSource(ctx.screen, true)
    API.drawImage(0, 0, ctx.screenW, ctx.screenH, ctx.shader)
end

local function onClientRender()
    if not isRunning() then
        return
    end
    local now = API.getTickCount()
    updateIntensity(now)
    updateFrame(now)
    drawRain()
end

local function onResourceStart()
    if ctx.state == STATE.RUNNING then
        return
    end
    startRain()
    if ctx.state == STATE.RUNNING then
        API.addEventHandler("onClientRender", root, onClientRender, false, "low-999999999")
    end
end

local function onResourceStop()
    API.removeEventHandler("onClientRender", root, onClientRender)
    destroyAll()
    logRain("Stopped", 3)
end

API.addEventHandler("onClientResourceStart", resourceRoot, onResourceStart)
API.addEventHandler("onClientResourceStop", resourceRoot, onResourceStop)

#Requires AutoHotkey v2.0

UI_CATCH_BAR_PIXEL := {x: 399, y: 505, colour: "0x434b5b"}
CEREBRA_CATCH_BAR_SEARCH := {x1: 248, y1: 500, x2: 568, y2: 560}
CEREBRA_CATCH_BAR_COLORS := ["0xff16a7", "0xff2dbd", "0xff54ca", "0xff7ed8", "0xf8a6e4", "0xff4ec7", "0xff9ce6"]
CEREBRA_CATCH_BAR_COLOR_VARIATION := 68
CEREBRA_SHAKE_NO_IMAGE_FRAMES := 18
CEREBRA_SHAKE_FALLBACK_CLICK_INTERVAL := 6
CEREBRA_FORCE_ADVANCE_NO_IMAGE_FRAMES := 8
CEREBRA_FORCE_ADVANCE_MAX_FRAMES := 14
FAST_LURE_SKIP_THRESHOLD := 100
FAST_LURE_FORCE_ADVANCE_FRAMES := 4
FAST_LURE_NO_IMAGE_ADVANCE_FRAMES := 2

SHAKE_AREA := {x1: 20, y1: 40, x2: 780, y2: 580}
SHAKE_AREA_CONFIGURED := false
SHAKE_DEBUG_ENABLED := false
SHAKE_USE_FIXED_AREA := true
SHAKE_FIXED_AREA := {x1: 20, y1: 40, x2: 780, y2: 580}
SHAKE_IMAGE := 'Assets\Shake.png'
SHAKE_IMAGE_BASE_WIDTH := 46
SHAKE_IMAGE_BASE_HEIGHT := 14
SHAKE_BASE_CLIENT_WIDTH := 800
SHAKE_BASE_CLIENT_HEIGHT := 600
MAX_SHAKES := 50

CATCH_BAR_MIN_RUN_RATIO := 0.11
CATCH_BAR_MIN_RUN_PX := 30

ensureShakeAreaConfigured() {
    global SHAKE_AREA_CONFIGURED, SHAKE_USE_FIXED_AREA, SHAKE_FIXED_AREA

    if SHAKE_USE_FIXED_AREA {
        SHAKE_AREA := {x1: SHAKE_FIXED_AREA.x1, y1: SHAKE_FIXED_AREA.y1, x2: SHAKE_FIXED_AREA.x2, y2: SHAKE_FIXED_AREA.y2}
        SHAKE_AREA_CONFIGURED := true
        return
    }

    if SHAKE_AREA_CONFIGURED
        return

    if applySavedShakeArea() {
        SHAKE_AREA_CONFIGURED := true
        return
    }

    configureShakeAreaBeforeStart()
}

redoShakeAreaSetup() {
    global SHAKE_AREA_CONFIGURED
    SHAKE_AREA_CONFIGURED := false
    configureShakeAreaBeforeStart()
}

configureShakeAreaBeforeStart() {
    global SHAKE_AREA, SHAKE_AREA_CONFIGURED

    activateRoblox()
    WinGetClientPos &winX, &winY, , , "ahk_exe RobloxPlayerBeta.exe"

    previewW := SHAKE_AREA.x2 - SHAKE_AREA.x1 + 1
    previewH := SHAKE_AREA.y2 - SHAKE_AREA.y1 + 1
    if previewW < 220
        previewW := 420
    if previewH < 120
        previewH := 260

    guiX := winX + SHAKE_AREA.x1
    guiY := winY + SHAKE_AREA.y1

    overlay := Gui("+AlwaysOnTop -Caption +ToolWindow +Border +Resize +MinSize220x120", "Shake Scan Setup")
    overlay.BackColor := "102210"
    overlay.MarginX := 0
    overlay.MarginY := 0
    fill := overlay.AddText("x0 y0 w" previewW " h" previewH " Background3CFF00")
    overlay.OnEvent("Size", overlayResized)
    overlay.Show("x" guiX " y" guiY " w" previewW " h" previewH)

    overlayResized(thisGui, minMax, guiW, guiH) {
        if guiW < 1 || guiH < 1
            return
        fill.Move(0, 0, guiW, guiH)
    }

    info := Gui("+AlwaysOnTop +ToolWindow", "Shake Scan Setup Controls")
    setGuiDarkBase(info)
    info.SetFont("s10 cEAEAEA", "Segoe UI")
    info.AddText("xm ym", "Drag/resize green box over shake region.")
    info.AddText("xm y+8", "Enter = confirm, Escape = exit macro.")
    applyGuiDarkTheme(info)
    info.Show("AutoSize x" (winX + 10) " y" (winY + 34))

    ih := InputHook("L0 V")
    ih.KeyOpt("{Enter}{Escape}", "E")
    ih.Start()
    ih.Wait()

    if ih.EndKey = "Escape" {
        try info.Destroy()
        try overlay.Destroy()
        ExitApp
    }

    WinGetPos &boxX, &boxY, &boxW, &boxH, overlay.Hwnd
    localX1 := boxX - winX
    localY1 := boxY - winY
    localX2 := localX1 + boxW - 1
    localY2 := localY1 + boxH - 1

    SHAKE_AREA := {x1: localX1, y1: localY1, x2: localX2, y2: localY2}
    SHAKE_AREA_CONFIGURED := true

    IniWrite(localX1, A_ScriptDir "\\info.ini", "", "ShakeAreaX1")
    IniWrite(localY1, A_ScriptDir "\\info.ini", "", "ShakeAreaY1")
    IniWrite(localX2, A_ScriptDir "\\info.ini", "", "ShakeAreaX2")
    IniWrite(localY2, A_ScriptDir "\\info.ini", "", "ShakeAreaY2")

    try info.Destroy()
    try overlay.Destroy()
}

applySavedShakeArea() {
    global SHAKE_AREA

    x1 := parseOptionalNumber(getInfoConfigValue("ShakeAreaX1", ""), "")
    y1 := parseOptionalNumber(getInfoConfigValue("ShakeAreaY1", ""), "")
    x2 := parseOptionalNumber(getInfoConfigValue("ShakeAreaX2", ""), "")
    y2 := parseOptionalNumber(getInfoConfigValue("ShakeAreaY2", ""), "")

    if x1 = "" || y1 = "" || x2 = "" || y2 = ""
        return false
    if x2 <= x1 || y2 <= y1
        return false

    SHAKE_AREA := {x1: Round(x1), y1: Round(y1), x2: Round(x2), y2: Round(y2)}
    return true
}

getShakeImageSearchSpec(variation := 10) {
    global SHAKE_IMAGE, SHAKE_IMAGE_BASE_WIDTH, SHAKE_IMAGE_BASE_HEIGHT, SHAKE_BASE_CLIENT_WIDTH, SHAKE_BASE_CLIENT_HEIGHT

    WinGetClientPos ,, &clientW, &clientH, "ahk_exe RobloxPlayerBeta.exe"
    if clientW <= 0 || clientH <= 0
        return "*" variation " *TransFF0000 " SHAKE_IMAGE

    scaleX := clientW / SHAKE_BASE_CLIENT_WIDTH
    scaleY := clientH / SHAKE_BASE_CLIENT_HEIGHT
    targetW := Round(Max(8, SHAKE_IMAGE_BASE_WIDTH * scaleX))
    targetH := Round(Max(6, SHAKE_IMAGE_BASE_HEIGHT * scaleY))

    return "*" variation " *TransFF0000 *w" targetW " *h" targetH " " SHAKE_IMAGE
}

findShakeImageBySpec(&outX, &outY, spec) {
    global SHAKE_AREA, SHAKE_IMAGE

    if ImageSearch(&outX, &outY, SHAKE_AREA.x1, SHAKE_AREA.y1, SHAKE_AREA.x2, SHAKE_AREA.y2, spec)
        return true

    fallbackSpec := "*10 *TransFF0000 " SHAKE_IMAGE
    return ImageSearch(&outX, &outY, SHAKE_AREA.x1, SHAKE_AREA.y1, SHAKE_AREA.x2, SHAKE_AREA.y2, fallbackSpec)
}

autoShake() {
    previousMouseDelay := A_MouseDelay
    SetMouseDelay -1

    try {
        ensureShakeAreaConfigured()
        SHAKE_DEBUG_ENABLED := StrLower(Trim(getInfoConfigValue("ShakeScanDebug", "false"))) = "true"

        updateStatus("Shaking.")

        activateRoblox()

        shakePin := createShakeAreaPin()
        shakeSearchSpec := getShakeImageSearchSpec(10)

        lastShake := {x: 0, y: 0}
        success := false

        Loop MAX_SHAKES {
            updateStatus("Shaking: " A_Index "/" MAX_SHAKES)

            activateRoblox()

            if findShakeImageBySpec(&X, &Y, shakeSearchSpec) {
                SendEvent "{Click, " X ", " Y "}"
                lastShake := {x: X, y: Y}
                MouseMove SHAKE_AREA.x2, SHAKE_AREA.y2
                Loop 5 {
                    if !findShakeImageBySpec(&X, &Y, shakeSearchSpec)
                        break
                    Sleep 10
                }
            }
            Sleep 10

            if isCatchBarDisplayed() {
                updateStatus("")
                success := true
                break
            }
        }

        if IsObject(shakePin)
            shakePin.Destroy()

        updateStatus("")
        return success
    } finally {
        SetMouseDelay previousMouseDelay
    }
}

isFastLureSpeedRod() {
    global FAST_LURE_SKIP_THRESHOLD
    lure := getSelectedLureSpeedPercent()
    return lure >= FAST_LURE_SKIP_THRESHOLD
}

isCerebraRodSelected() {
    global SELECTED_ROD_NAME

    rodName := ""
    try rodName := SELECTED_ROD_NAME
    if rodName = ""
        return false
    return RegExMatch(StrLower(rodName), "\bcerebra\b")
}

getSelectedLureSpeedPercent() {
    stats := getSelectedRodStats()
    if !IsObject(stats)
        return 0
    if !stats.HasOwnProp("lure")
        return 0

    lureRaw := stats.lure
    try return Number(lureRaw)

    text := Trim("" lureRaw)
    if RegExMatch(text, "([+\-]?\d+(?:\.\d+)?)", &match)
        return Number(match[1])
    return 0
}

isCatchBarDisplayed() {
    global CATCH_SCAN_AREA, CATCH_SCAN_LINE, CATCH_SCAN_COLOR_SET, CATCH_SCAN_COLOR_VARIATION, CATCH_BAR_TOP_LINE

    activateRoblox()

    ; Fast legacy point check first to avoid missing quick transitions.
    pixel := UI_CATCH_BAR_PIXEL
    if PixelSearch(&X, &Y, pixel.x, pixel.y, pixel.x, pixel.y, pixel.colour, 2)
        return true

    ; 1px line scan using configured color set.
    if IsObject(CATCH_SCAN_LINE) && IsObject(CATCH_SCAN_COLOR_SET) {
        for _, target in CATCH_SCAN_COLOR_SET {
            if PixelSearch(&foundX, &foundY, CATCH_SCAN_LINE.x1, CATCH_SCAN_LINE.y, CATCH_SCAN_LINE.x2, CATCH_SCAN_LINE.y, target, CATCH_SCAN_COLOR_VARIATION)
                return true
        }
    }

    ; Light area fallback (coarse stepping) for harder visual presets.
    if IsObject(CATCH_SCAN_AREA) && IsObject(CATCH_SCAN_COLOR_SET) {
        y := CATCH_SCAN_AREA.y1
        while y <= CATCH_SCAN_AREA.y2 {
            for _, target in CATCH_SCAN_COLOR_SET {
                if PixelSearch(&fx, &fy, CATCH_SCAN_AREA.x1, y, CATCH_SCAN_AREA.x2, y, target, CATCH_SCAN_COLOR_VARIATION)
                    return true
            }
            y += 4
        }
    }

    if isCerebraRodSelected() {
        if isCerebraCatchBarDisplayedByColor()
            return true
        if findFishIndicatorX(CATCH_BAR_TOP_LINE, &fishX)
            return true
    }

    return false
}

hasCatchColorRunOnLine(x1, y, x2, colorSet, variation, minRun) {
    run := 0
    bestRun := 0

    x := x1
    while x <= x2 {
        color := PixelGetColor(x, y, "RGB")
        if isColorInSet(color, colorSet, variation) {
            run += 1
            if run > bestRun
                bestRun := run
        } else {
            run := 0
        }
        x += 1
    }

    return bestRun >= minRun
}

isColorInSet(color, colorSet, variation) {
    for _, target in colorSet {
        if areColorsSimilar(color, target, variation)
            return true
    }
    return false
}

isCerebraCatchBarDisplayedByColor() {
    global CEREBRA_CATCH_BAR_SEARCH

    if hasCerebraPrimaryPinkRun(&primaryRun) && primaryRun >= 160
        return true

    pinkCount := 0
    y := CEREBRA_CATCH_BAR_SEARCH.y1
    while y <= CEREBRA_CATCH_BAR_SEARCH.y2 {
        x := CEREBRA_CATCH_BAR_SEARCH.x1
        while x <= CEREBRA_CATCH_BAR_SEARCH.x2 {
            if isCerebraPinkPixel(x, y)
                pinkCount += 1
            x += 16
        }
        y += 3
    }
    return pinkCount >= 10
}

hasCerebraPrimaryPinkRun(&bestRun) {
    global CEREBRA_CATCH_BAR_SEARCH

    bestRun := 0
    y := CEREBRA_CATCH_BAR_SEARCH.y1
    while y <= CEREBRA_CATCH_BAR_SEARCH.y2 {
        run := 0
        x := CEREBRA_CATCH_BAR_SEARCH.x1
        while x <= CEREBRA_CATCH_BAR_SEARCH.x2 {
            if isCerebraPinkPixel(x, y) {
                run += 1
                if run > bestRun
                    bestRun := run
            } else {
                run := 0
            }
            x += 1
        }
        y += 2
    }
    return bestRun > 0
}

isCerebraPinkPixel(x, y) {
    global CEREBRA_CATCH_BAR_COLORS, CEREBRA_CATCH_BAR_COLOR_VARIATION

    color := PixelGetColor(x, y, "RGB")
    for _, target in CEREBRA_CATCH_BAR_COLORS {
        if areColorsSimilar(color, target, CEREBRA_CATCH_BAR_COLOR_VARIATION)
            return true
    }
    return false
}

createShakeAreaPin() {
    global SHAKE_AREA, SHAKE_DEBUG_ENABLED

    if !SHAKE_DEBUG_ENABLED
        return false

    WinGetClientPos &winX0, &winY0, , , "ahk_exe RobloxPlayerBeta.exe"
    x1 := winX0 + SHAKE_AREA.x1
    y1 := winY0 + SHAKE_AREA.y1
    x2 := winX0 + SHAKE_AREA.x2
    y2 := winY0 + SHAKE_AREA.y2
    return Pin(x1, y1, x2, y2, 60000, "b1 flash0 c3cff00")
}

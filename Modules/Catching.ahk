#Requires AutoHotkey v2.0

CATCH_BAR := {x1: 249, y1: 502, x2: 551, y2: 517, xLeft: 288, xRight: 511}
CATCH_BAR_TOP_LINE := {x1: 238, y1: 501, x2: 561, y2: 501}
CATCH_BAR_ARROW_LINE := {x1: 239, y1: 508, x2: 560, y2: 508}

LEFT_ARROW_TO_MIDDLE_OFFSET := 0
RIGHT_ARROW_TO_MIDDLE_OFFSET := 0
CONTROL_BAR_HALF_WIDTH := 0
CONTROL_BAR_WIDTH := 0
CATCHING_SELECTED_CONTROL := 0.0

CATCH_BAR_LEFT_X := 0
CATCH_BAR_RIGHT_X := 0

ROBLOX_X := 0
ROBLOX_Y := 0

CATCHING_CENTER_RATIO := 0.35
CATCHING_LOOKAHEAD_MS := 60
CATCHING_BRAKE_SPEED := 0.95
CATCHING_DEADZONE_PX := 3
CATCHING_FISH_VELOCITY_SMOOTHING := 0.45
CATCHING_BAR_VELOCITY_SMOOTHING := 0.40
CATCHING_DIRECTION_SWITCH_COOLDOWN_MS := 14
CATCHING_MAX_POSITION_JUMP_PX := 140
CATCH_MAX_DURATION_MS := 35000
NORMAL_END_NO_STRONG_SIGNAL_MS := 4500

CATCH_ARROW_COLOR := "0x787878"
CATCH_ARROW_TOLERANCE := 4
CALIBRATION_FISH_COLOR := "0x434B5B"
CALIBRATION_FISH_TOLERANCE := 4

HEARTBEAT_MARKER_COLOR := "0x000000"
HEARTBEAT_MARKER_TOLERANCE := 5
HEARTBEAT_CONTROL_BASE_RATIO := 0.30
HEARTBEAT_CONTROL_MIN_RATIO := 0.18
HEARTBEAT_CONTROL_MAX_RATIO := 0.92
HEARTBEAT_SCAN_CENTER_Y := 513
HEARTBEAT_SCAN_Y_RADIUS := 2
HEARTBEAT_MAX_JUMP_PX := 70

LAST_HEARTBEAT_X := 0
LAST_CATCH_LEARNING_METRICS := false


CATCH_SCAN_LINE_CONFIGURED := false
CATCH_SCAN_LINE := {x1: 234, y: 513, x2: 565}
CATCH_SCAN_AREA := {x1: 234, y1: 502, x2: 565, y2: 517}
CATCH_SCAN_COLOR_VARIATION := 24
CATCH_SCAN_DEBUG_ENABLED := true
CATCH_SCAN_COLOR_SET := ["0x434B5B", "0x787878", "0xF1F1F1", "0xF1F1F1"]
CATCH_USE_FIXED_AREA := true
CATCH_FIXED_AREA := {x1: 249, y1: 502, x2: 551, y2: 517}
CATCH_WHITE_VARIATION := 18
CATCH_CENTER_CUT_RATIO := 0.22

configureCatchScanLineBeforeStart() {
    global CATCH_SCAN_LINE_CONFIGURED, CATCH_SCAN_LINE, CATCH_SCAN_AREA, CATCH_BAR, CATCH_BAR_TOP_LINE, CATCH_BAR_ARROW_LINE

    activateRoblox()
    WinGetClientPos &winX, &winY, , , "ahk_exe RobloxPlayerBeta.exe"

    previewW := CATCH_SCAN_AREA.x2 - CATCH_SCAN_AREA.x1 + 1
    previewH := CATCH_SCAN_AREA.y2 - CATCH_SCAN_AREA.y1 + 1
    if previewW < 120
        previewW := 320
    if previewH < 12
        previewH := 16

    guiX := winX + CATCH_SCAN_AREA.x1
    guiY := winY + CATCH_SCAN_AREA.y1

    overlay := Gui("+AlwaysOnTop -Caption +ToolWindow +Border +Resize +MinSize120x12", "Catch Scan Setup")
    overlay.BackColor := "1C1230"
    overlay.MarginX := 0
    overlay.MarginY := 0
    areaFill := overlay.AddText("x0 y0 w" previewW " h" previewH " Background5E2CA5")
    midY := Round(previewH / 2)
    scanLine := overlay.AddText("x0 y" midY " w" previewW " h1 BackgroundFFFFFF")
    overlay.OnEvent("Size", overlayResized)
    overlay.Show("x" guiX " y" guiY " w" previewW " h" previewH)

    overlayResized(thisGui, minMax, guiW, guiH) {
        local midLineY

        if guiW < 1 || guiH < 1
            return

        areaFill.Move(0, 0, guiW, guiH)
        midLineY := Round(guiH / 2)
        scanLine.Move(0, midLineY, guiW, 1)
    }

    info := Gui("+AlwaysOnTop +ToolWindow", "Catch Scan Setup Controls")
    setGuiDarkBase(info)
    info.SetFont("s10 cEAEAEA", "Segoe UI")
    info.AddText("xm ym", "Drag and resize the purple box onto the catch bar area.")
    info.AddText("xm y+6", "White line = 1px scan line used for fish detection.")
    info.AddText("xm y+8", "Press Enter to confirm. Press Escape to exit macro.")
    applyGuiDarkTheme(info)
    info.Show("AutoSize x" (winX + 10) " y" (winY + 10))

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
    lineY := localY1 + Round((boxH - 1) / 2)

    CATCH_SCAN_AREA := {x1: localX1, y1: localY1, x2: localX2, y2: localY2}
    CATCH_SCAN_LINE := {x1: localX1, y: lineY, x2: localX2}

    CATCH_BAR := {x1: localX1, y1: localY1, x2: localX2, y2: localY2, xLeft: localX1, xRight: localX2}
    CATCH_BAR_TOP_LINE := {x1: localX1, y1: lineY, x2: localX2, y2: lineY}
    CATCH_BAR_ARROW_LINE := {x1: localX1, y1: lineY, x2: localX2, y2: lineY}

    CATCH_SCAN_LINE_CONFIGURED := true
    IniWrite(localX1, A_ScriptDir "\info.ini", "", "CatchScanX1")
    IniWrite(localY1, A_ScriptDir "\info.ini", "", "CatchScanY1")
    IniWrite(localX2, A_ScriptDir "\info.ini", "", "CatchScanX2")
    IniWrite(localY2, A_ScriptDir "\info.ini", "", "CatchScanY2")

    try info.Destroy()
    try overlay.Destroy()
}


redoCatchScanSetup() {
    global CATCH_SCAN_LINE_CONFIGURED
    CATCH_SCAN_LINE_CONFIGURED := false
    configureCatchScanLineBeforeStart()
}

ensureCatchScanConfigured() {
    global CATCH_SCAN_LINE_CONFIGURED, CATCH_USE_FIXED_AREA, CATCH_FIXED_AREA

    if CATCH_USE_FIXED_AREA {
        applyCatchArea(CATCH_FIXED_AREA.x1, CATCH_FIXED_AREA.y1, CATCH_FIXED_AREA.x2, CATCH_FIXED_AREA.y2)
        CATCH_SCAN_LINE_CONFIGURED := true
        return
    }

    if CATCH_SCAN_LINE_CONFIGURED
        return

    if applySavedCatchScanArea() {
        CATCH_SCAN_LINE_CONFIGURED := true
        return
    }

    configureCatchScanLineBeforeStart()
}

applyCatchArea(x1, y1, x2, y2) {
    global CATCH_SCAN_AREA, CATCH_SCAN_LINE, CATCH_BAR, CATCH_BAR_TOP_LINE, CATCH_BAR_ARROW_LINE

    lineY := y1 + Round((y2 - y1) / 2)
    CATCH_SCAN_AREA := {x1: Round(x1), y1: Round(y1), x2: Round(x2), y2: Round(y2)}
    CATCH_SCAN_LINE := {x1: Round(x1), y: Round(lineY), x2: Round(x2)}
    CATCH_BAR := {x1: Round(x1), y1: Round(y1), x2: Round(x2), y2: Round(y2), xLeft: Round(x1), xRight: Round(x2)}
    CATCH_BAR_TOP_LINE := {x1: Round(x1), y1: Round(lineY), x2: Round(x2), y2: Round(lineY)}
    CATCH_BAR_ARROW_LINE := {x1: Round(x1), y1: Round(lineY), x2: Round(x2), y2: Round(lineY)}
}

applySavedCatchScanArea() {
    global CATCH_SCAN_AREA, CATCH_SCAN_LINE, CATCH_BAR, CATCH_BAR_TOP_LINE, CATCH_BAR_ARROW_LINE

    x1 := parseOptionalNumber(getInfoConfigValue("CatchScanX1", ""), "")
    y1 := parseOptionalNumber(getInfoConfigValue("CatchScanY1", ""), "")
    x2 := parseOptionalNumber(getInfoConfigValue("CatchScanX2", ""), "")
    y2 := parseOptionalNumber(getInfoConfigValue("CatchScanY2", ""), "")

    if x1 = "" || y1 = "" || x2 = "" || y2 = ""
        return false
    if x2 <= x1 || y2 <= y1
        return false

    applyCatchArea(x1, y1, x2, y2)
    return true
}

createCatchScanDebugPins() {
    global CATCH_SCAN_DEBUG_ENABLED, CATCH_SCAN_AREA, CATCH_SCAN_LINE

    if !CATCH_SCAN_DEBUG_ENABLED
        return false

    WinGetClientPos &winX, &winY, , , "ahk_exe RobloxPlayerBeta.exe"
    areaPin := Pin(winX + CATCH_SCAN_AREA.x1, winY + CATCH_SCAN_AREA.y1, winX + CATCH_SCAN_AREA.x2, winY + CATCH_SCAN_AREA.y2, 60000, "b1 flash0 c8a2be2")
    linePin := Pin(winX + CATCH_SCAN_LINE.x1, winY + CATCH_SCAN_LINE.y, winX + CATCH_SCAN_LINE.x2, winY + CATCH_SCAN_LINE.y, 60000, "b1 flash0 cffffff")
    return {area: areaPin, line: linePin}
}

destroyCatchScanDebugPins(pins) {
    if !IsObject(pins)
        return
    try pins.area.Destroy()
    try pins.line.Destroy()
}

catchFish() {
    global

    ensureCatchScanConfigured()
    WinGetClientPos &ROBLOX_X, &ROBLOX_Y, , , "ahk_exe RobloxPlayerBeta.exe"
    learning := createCatchLearningMetrics()
    loopStartTick := A_TickCount
    state := createCatchingState()
    heartbeatMode := isHeartbeatControlModeSelected()

    activateRoblox()
    if heartbeatMode
        applyHeartbeatControlScaling()
    else
        getArrowOffsets()

    if CONTROL_BAR_WIDTH <= 0 {
        CONTROL_BAR_HALF_WIDTH := 15
        CONTROL_BAR_WIDTH := 30
    }

    catchMinX := CATCH_BAR_TOP_LINE.x1
    catchMaxX := CATCH_BAR_TOP_LINE.x2
    initialInset := Round(Max(2, CONTROL_BAR_WIDTH * CATCH_CENTER_CUT_RATIO))
    CATCH_BAR_LEFT_X := clampValue(catchMinX + initialInset, catchMinX, catchMaxX)
    CATCH_BAR_RIGHT_X := clampValue(catchMaxX - initialInset, catchMinX, catchMaxX)

    missingFishFrames := 0
    uiMissingFrames := 0
    staleSignalFrames := 0
    startupGraceFrames := 10
    lastStrongSignalTick := loopStartTick
    lastTick := A_TickCount
    breakReason := ""

    debugPins := createCatchScanDebugPins()
    showCatchDebugBar()

    updateStatus("Catching: loop")
    Loop {
        now := A_TickCount
        dt := Max(now - lastTick, 1)
        lastTick := now
        elapsedMs := now - loopStartTick

        learning.frames += 1
        if isCatchBarDisplayed()
            uiMissingFrames := 0
        else
            uiMissingFrames += 1

        fishDetected := findFishIndicatorX(CATCH_BAR_TOP_LINE, &xFish)
        if fishDetected {
            missingFishFrames := 0
            learning.fishDetectedFrames += 1
        } else {
            missingFishFrames += 1
            if !state.hasFish && missingFishFrames >= 18 {
                breakReason := "no_fish"
                break
            }
            xFish := Round(clampValue(state.lastFishX + (state.fishVelocity * dt), catchMinX, catchMaxX))
            learning.fallbackFishFrames += 1
        }
        updateFishState(state, xFish, dt)

        barMiddleX := false
        if findWhiteControlBarBoundsOnLine(CATCH_SCAN_LINE.y, &whiteBounds) {
            CONTROL_BAR_WIDTH := whiteBounds.width
            CONTROL_BAR_HALF_WIDTH := Round(whiteBounds.width / 2)
            barMiddleX := Round((whiteBounds.x1 + whiteBounds.x2) / 2)
            learning.whiteBarFrames += 1
            insetPx := Round(Max(2, whiteBounds.width * CATCH_CENTER_CUT_RATIO))
            CATCH_BAR_LEFT_X := whiteBounds.x1 + insetPx
            CATCH_BAR_RIGHT_X := whiteBounds.x2 - insetPx
        } else if state.hasBar {
            learning.multicolorBarFrames += 1
            barMiddleX := state.lastBarMiddleX + (state.barVelocity * dt)
        }

        if !barMiddleX {
            staleSignalFrames += 1
            if staleSignalFrames > 26
                staleSignalFrames := 20
            updateCatchDebugBar(catchMinX, catchMaxX, xFish, state.hasBar ? state.lastBarMiddleX : catchMinX, CATCH_BAR_LEFT_X, CATCH_BAR_RIGHT_X, "no-bar")
            Sleep 2
            continue
        }

        staleSignalFrames := 0
        lastStrongSignalTick := now
        updateBarState(state, barMiddleX, dt)

        absError := Abs(xFish - barMiddleX)
        learning.errorSamples += 1
        learning.totalAbsErrorPx += absError
        if absError > learning.maxAbsErrorPx
            learning.maxAbsErrorPx := absError

        if elapsedMs >= CATCH_MAX_DURATION_MS {
            breakReason := "max_duration"
            break
        }
        if A_Index > startupGraceFrames && uiMissingFrames >= 30 {
            breakReason := "ui_missing"
            break
        }
        if elapsedMs > 5000 && (now - lastStrongSignalTick) >= NORMAL_END_NO_STRONG_SIGNAL_MS {
            breakReason := "no_strong_signal"
            break
        }

        CATCH_BAR_LEFT_X := clampValue(CATCH_BAR_LEFT_X, catchMinX, catchMaxX)
        CATCH_BAR_RIGHT_X := clampValue(CATCH_BAR_RIGHT_X, catchMinX, catchMaxX)

        if xFish > CATCH_BAR_RIGHT_X {
            setControlDirection(state, 1)
            Sleep 12
            continue
        }
        if xFish < CATCH_BAR_LEFT_X {
            setControlDirection(state, -1)
            Sleep 12
            continue
        }

        inCenterZone := (xFish >= CATCH_BAR_LEFT_X && xFish <= CATCH_BAR_RIGHT_X)
        updateCatchDebugBar(catchMinX, catchMaxX, xFish, barMiddleX, CATCH_BAR_LEFT_X, CATCH_BAR_RIGHT_X, inCenterZone ? "CENTER" : "TRACK")

        if inCenterZone {
            if state.clickDown
                setControlDirection(state, -1)
            Sleep 2
            continue
        }

        setControlDirection(state, xFish > CATCH_BAR_RIGHT_X ? 1 : -1)
        Sleep 6
    }

    releaseControl(state)
    destroyCatchScanDebugPins(debugPins)
    hideCatchDebugBar()
    finalizeCatchLearningMetrics(learning, loopStartTick)
    if breakReason = ""
        breakReason := "loop_end"
}

isHeartbeatControlModeSelected() {
    global SELECTED_ROD_NAME

    rodName := ""
    try rodName := SELECTED_ROD_NAME
    if rodName = ""
        return false
    return RegExMatch(StrLower(rodName), "\bcerebra\b")
}

applyHeartbeatControlScaling() {
    global CATCHING_SELECTED_CONTROL, HEARTBEAT_CONTROL_BASE_RATIO, HEARTBEAT_CONTROL_MIN_RATIO, HEARTBEAT_CONTROL_MAX_RATIO
    global CATCH_BAR_TOP_LINE, CONTROL_BAR_WIDTH, CONTROL_BAR_HALF_WIDTH, LEFT_ARROW_TO_MIDDLE_OFFSET, RIGHT_ARROW_TO_MIDDLE_OFFSET

    regionWidth := CATCH_BAR_TOP_LINE.x2 - CATCH_BAR_TOP_LINE.x1 + 1
    if regionWidth <= 0
        return

    controlUnit := normalizeHeartbeatControl(CATCHING_SELECTED_CONTROL)
    ratio := HEARTBEAT_CONTROL_BASE_RATIO + controlUnit
    ratio := clampValue(ratio, HEARTBEAT_CONTROL_MIN_RATIO, HEARTBEAT_CONTROL_MAX_RATIO)
    width := Round(clampValue(regionWidth * ratio, 12, regionWidth - 4))

    CONTROL_BAR_WIDTH := width
    CONTROL_BAR_HALF_WIDTH := Round(width / 2)
    LEFT_ARROW_TO_MIDDLE_OFFSET := Max(1, CONTROL_BAR_HALF_WIDTH - 9)
    RIGHT_ARROW_TO_MIDDLE_OFFSET := Max(1, CONTROL_BAR_HALF_WIDTH - 9)
}

normalizeHeartbeatControl(controlValue) {
    value := 0.0
    try value := Number(controlValue)

    ; Support both unit input (0.2) and percent-like input (20).
    if Abs(value) > 1.0
        value := value / 100.0

    return clampValue(value, -0.6, 0.8)
}

ensureRodEquippedQuick() {
    activateRoblox()
    SendEvent "{2}"
    Sleep 60
    SendEvent "{1}"
    Sleep 80

    try return isRodEquipped()
    catch
        return false
}

createCatchLearningMetrics() {
    return {
        frames: 0,
        fishDetectedFrames: 0,
        fallbackFishFrames: 0,
        whiteBarFrames: 0,
        multicolorBarFrames: 0,
        errorSamples: 0,
        totalAbsErrorPx: 0.0,
        maxAbsErrorPx: 0.0,
        avgAbsErrorPx: 0.0,
        durationMs: 0,
        popupDetected: false,
        popupKnown: false,
        outcome: "unknown"
    }
}

finalizeCatchLearningMetrics(learning, loopStartTick) {
    global LAST_CATCH_LEARNING_METRICS

    if !IsObject(learning)
        return

    learning.durationMs := Max(0, A_TickCount - loopStartTick)
    if learning.errorSamples > 0
        learning.avgAbsErrorPx := Round(learning.totalAbsErrorPx / learning.errorSamples, 3)

    popupResult := detectCatchPopupResult()
    learning.popupKnown := popupResult.known
    learning.popupDetected := popupResult.detected
    learning.outcome := popupResult.outcome
    LAST_CATCH_LEARNING_METRICS := learning
}

getLastCatchLearningMetrics() {
    global LAST_CATCH_LEARNING_METRICS
    if !IsObject(LAST_CATCH_LEARNING_METRICS)
        return false
    return LAST_CATCH_LEARNING_METRICS
}

detectCatchPopupResult() {
    if !isCatchPopupDetectionEnabled()
        return {known: false, detected: false, outcome: "unknown"}

    timeoutMs := Round(parseOptionalNumber(getInfoConfigValue("CatchPopupTimeoutMs", "1100"), 1100))
    timeoutMs := Max(100, Min(timeoutMs, 3000))
    deadline := A_TickCount + timeoutMs
    ocrAvailable := true
    while A_TickCount <= deadline {
        if detectCatchPopupByRegex(&matchType, &ocrText, &ocrAvailable) {
            if matchType = "success"
                return {known: true, detected: true, outcome: "success"}
            if matchType = "failure"
                return {known: true, detected: false, outcome: "failure"}
        }
        if !ocrAvailable
            return {known: false, detected: false, outcome: "unknown"}
        Sleep 45
    }

    return {known: true, detected: false, outcome: "failure"}
}

isCatchPopupDetectionEnabled() {
    mode := StrLower(Trim(getInfoConfigValue("CatchPopupDetect", "regex")))
    if mode = "off" || mode = "0" || mode = "false"
        return false
    if mode = "regex" || mode = "auto" || mode = "on" || mode = "1" || mode = "true"
        return hasCatchPopupRegexConfigured()
    return false
}

hasCatchPopupRegexConfigured() {
    successRegex := Trim(getInfoConfigValue("CatchPopupSuccessRegex", ""))
    failureRegex := Trim(getInfoConfigValue("CatchPopupFailureRegex", ""))

    if successRegex != "" && isValidCatchPopupRegex(successRegex)
        return true
    if failureRegex != "" && isValidCatchPopupRegex(failureRegex)
        return true
    return false
}

isValidCatchPopupRegex(pattern) {
    try {
        RegExMatch("", pattern)
        return true
    } catch {
        return false
    }
}

detectCatchPopupByRegex(&matchType, &ocrText, &ocrAvailable) {
    matchType := ""
    ocrText := readCatchPopupOcrText(&ocrAvailable)
    if !ocrAvailable
        return false

    text := Trim(RegExReplace(ocrText, "\s+", " "))
    if text = ""
        return false
    normalizedText := normalizeCatchPopupOcrText(text)

    successRegex := Trim(getInfoConfigValue("CatchPopupSuccessRegex", ""))
    if successRegex != "" {
        if matchCatchPopupRegex(successRegex, text, normalizedText) {
            matchType := "success"
            return true
        }
    }

    failureRegex := Trim(getInfoConfigValue("CatchPopupFailureRegex", ""))
    if failureRegex != "" {
        if matchCatchPopupRegex(failureRegex, text, normalizedText) {
            matchType := "failure"
            return true
        }
    }

    return false
}

matchCatchPopupRegex(pattern, rawText, normalizedText := "") {
    try {
        if RegExMatch(rawText, pattern)
            return true
    } catch {
        return false
    }

    if normalizedText = ""
        return false

    try return RegExMatch(normalizedText, pattern)
    catch
        return false
}

normalizeCatchPopupOcrText(text) {
    cleaned := StrLower(text)
    cleaned := RegExReplace(cleaned, "[^a-z0-9]+", " ")
    return Trim(RegExReplace(cleaned, "\s+", " "))
}

readCatchPopupOcrText(&ocrAvailable := true) {
    global ROBLOX_X, ROBLOX_Y

    search := getCatchPopupSearchArea()
    width := search.x2 - search.x1 + 1
    height := search.y2 - search.y1 + 1
    if width <= 0 || height <= 0 {
        ocrAvailable := false
        return ""
    }

    winX := ROBLOX_X
    winY := ROBLOX_Y
    if winX = 0 && winY = 0 {
        try WinGetClientPos &winX, &winY, , , "ahk_exe RobloxPlayerBeta.exe"
        catch {
            ocrAvailable := false
            return ""
        }
    }

    scale := parseOptionalNumber(getInfoConfigValue("CatchPopupOcrScale", "2.2"), 2.2)
    scale := Max(0.5, Min(scale, 4.0))
    lang := Trim(getInfoConfigValue("CatchPopupOcrLang", "auto"))
    if lang = ""
        lang := "auto"

    screenX := winX + search.x1
    screenY := winY + search.y1
    languages := []
    if StrLower(lang) = "auto" {
        languages.Push("")
        languages.Push("en-US")
    } else {
        languages.Push(lang)
    }

    for _, selectedLang in languages {
        try {
            if selectedLang = ""
                ocrResult := OCR.FromRect(screenX, screenY, width, height, , scale)
            else
                ocrResult := OCR.FromRect(screenX, screenY, width, height, selectedLang, scale)
            return IsObject(ocrResult) ? ("" ocrResult.Text) : ""
        } catch {
        }
    }

    ocrAvailable := false
    return ""
}

getCatchPopupSearchArea() {
    defaultArea := {x1: 120, y1: 250, x2: 760, y2: 560}
    x1 := parseOptionalNumber(getInfoConfigValue("CatchPopupX1", ""), "")
    y1 := parseOptionalNumber(getInfoConfigValue("CatchPopupY1", ""), "")
    x2 := parseOptionalNumber(getInfoConfigValue("CatchPopupX2", ""), "")
    y2 := parseOptionalNumber(getInfoConfigValue("CatchPopupY2", ""), "")

    if x1 = "" || y1 = "" || x2 = "" || y2 = ""
        return defaultArea
    if x2 < x1 || y2 < y1
        return defaultArea
    return {x1: Round(x1), y1: Round(y1), x2: Round(x2), y2: Round(y2)}
}

configureCatchingForRod(rodStats) {
    global CATCHING_CENTER_RATIO, CATCHING_LOOKAHEAD_MS, CATCHING_BRAKE_SPEED, CATCHING_DEADZONE_PX, CATCHING_SELECTED_CONTROL

    if !IsObject(rodStats)
        return

    control := 0.0
    resilience := 0.0
    try control := Number(rodStats.control)
    try resilience := Number(rodStats.resilience)

    CATCHING_SELECTED_CONTROL := control
    CATCHING_CENTER_RATIO := 0.35
    CATCHING_LOOKAHEAD_MS := Round(clampValue(60 - (resilience * 0.20), 28, 75))
    CATCHING_BRAKE_SPEED := clampValue(0.95 - (control * 0.45), 0.50, 1.20)
    CATCHING_DEADZONE_PX := Round(clampValue(3 + ((20 - resilience) / 20), 2, 6))

    if rodStats.HasOwnProp("catching") && IsObject(rodStats.catching)
        applyCatchingTuning(rodStats.catching)

    if isHeartbeatControlModeSelected()
        applyHeartbeatControlScaling()
}

applyCatchingTuning(tuning) {
    global

    if !IsObject(tuning)
        return

    if tuning.HasOwnProp("centerRatio")
        try CATCHING_CENTER_RATIO := clampValue(Number(tuning.centerRatio), 0.15, 0.48)
    if tuning.HasOwnProp("lookaheadMs")
        try CATCHING_LOOKAHEAD_MS := Round(clampValue(Number(tuning.lookaheadMs), 15, 120))
    if tuning.HasOwnProp("brakeSpeed")
        try CATCHING_BRAKE_SPEED := clampValue(Number(tuning.brakeSpeed), 0.20, 1.60)
    if tuning.HasOwnProp("deadzonePx")
        try CATCHING_DEADZONE_PX := Round(clampValue(Number(tuning.deadzonePx), 1, 10))
    if tuning.HasOwnProp("fishVelocitySmoothing")
        try CATCHING_FISH_VELOCITY_SMOOTHING := clampValue(Number(tuning.fishVelocitySmoothing), 0.05, 0.95)
    if tuning.HasOwnProp("barVelocitySmoothing")
        try CATCHING_BAR_VELOCITY_SMOOTHING := clampValue(Number(tuning.barVelocitySmoothing), 0.05, 0.95)
}

createCatchingState() {
    return {
        hasFish: false,
        lastFishX: 0,
        fishVelocity: 0.0,
        fishDirection: 0,
        hasBar: false,
        lastBarMiddleX: 0,
        barVelocity: 0.0,
        barDirection: 0,
        clickDown: GetKeyState("LButton", "P"),
        commandedDirection: 0,
        lastSwitchTick: 0,
        lastHoldEnsureTick: 0
    }
}

updateFishState(state, xFish, dt) {
    global CATCHING_MAX_POSITION_JUMP_PX, CATCHING_FISH_VELOCITY_SMOOTHING

    if !state.hasFish {
        state.hasFish := true
        state.lastFishX := xFish
        return
    }

    deltaX := xFish - state.lastFishX
    if Abs(deltaX) > CATCHING_MAX_POSITION_JUMP_PX {
        state.lastFishX := xFish
        return
    }
    instantVelocity := deltaX / dt
    smoothing := CATCHING_FISH_VELOCITY_SMOOTHING
    state.fishVelocity := (state.fishVelocity * (1 - smoothing)) + (instantVelocity * smoothing)
    if Abs(deltaX) >= 1
        state.fishDirection := deltaX > 0 ? 1 : -1
    state.lastFishX := xFish
}

updateBarState(state, barMiddleX, dt) {
    global CATCHING_MAX_POSITION_JUMP_PX, CATCHING_BAR_VELOCITY_SMOOTHING

    if !state.hasBar {
        state.hasBar := true
        state.lastBarMiddleX := barMiddleX
        return
    }

    deltaX := barMiddleX - state.lastBarMiddleX
    if Abs(deltaX) > CATCHING_MAX_POSITION_JUMP_PX {
        state.lastBarMiddleX := barMiddleX
        return
    }
    instantVelocity := deltaX / dt
    smoothing := CATCHING_BAR_VELOCITY_SMOOTHING
    state.barVelocity := (state.barVelocity * (1 - smoothing)) + (instantVelocity * smoothing)
    if Abs(deltaX) >= 1
        state.barDirection := deltaX > 0 ? 1 : -1
    state.lastBarMiddleX := barMiddleX
}

setControlDirection(state, direction) {
    global CATCHING_DIRECTION_SWITCH_COOLDOWN_MS

    if !IsObject(state)
        return

    ; Keep internal state aligned with actual input state.
    state.clickDown := GetKeyState("LButton", "P")

    now := A_TickCount
    if direction != state.commandedDirection {
        if state.lastSwitchTick > 0 && (now - state.lastSwitchTick) < CATCHING_DIRECTION_SWITCH_COOLDOWN_MS
            return
        state.lastSwitchTick := now
        state.commandedDirection := direction
    }

    if direction > 0 {
        if !state.clickDown {
            SendEvent "{Click down}"
            state.clickDown := true
            state.lastHoldEnsureTick := now
        }
        return
    }
    if direction < 0 && state.clickDown {
        SendEvent "{Click up}"
        state.clickDown := false
    }
}

releaseControl(state) {
    if IsObject(state) && state.clickDown {
        SendEvent "{Click up}"
        state.clickDown := false
    }
}

estimateBarMiddleFromArrow(arrowX, state) {
    global LEFT_ARROW_TO_MIDDLE_OFFSET, RIGHT_ARROW_TO_MIDDLE_OFFSET, CATCH_BAR_ARROW_LINE

    if state.barDirection > 0
        xMiddle := arrowX + LEFT_ARROW_TO_MIDDLE_OFFSET
    else if state.barDirection < 0
        xMiddle := arrowX - RIGHT_ARROW_TO_MIDDLE_OFFSET
    else if state.clickDown
        xMiddle := arrowX + LEFT_ARROW_TO_MIDDLE_OFFSET
    else
        xMiddle := arrowX - RIGHT_ARROW_TO_MIDDLE_OFFSET

    return clampValue(xMiddle, CATCH_BAR_ARROW_LINE.x1, CATCH_BAR_ARROW_LINE.x2)
}

computePulseDelay(positionError, speedGap) {
    global CATCHING_DEADZONE_PX

    magnitude := Abs(positionError)
    speedBias := Abs(speedGap) * 5
    nearTargetPenalty := magnitude <= (CATCHING_DEADZONE_PX * 2) ? 0.0 : 0.8
    return Round(clampValue(2 + (magnitude * 0.05) + speedBias + nearTargetPenalty, 2, 10))
}

clampValue(value, minValue, maxValue) {
    if value < minValue
        return minValue
    if value > maxValue
        return maxValue
    return value
}

findFishIndicatorX(search, &xFish) {
    global CATCH_SCAN_COLOR_SET, CATCH_SCAN_COLOR_VARIATION, CALIBRATION_FISH_COLOR, CALIBRATION_FISH_TOLERANCE

    ; Legacy-first path keeps white-bar behavior stable.
    if PixelSearch(&foundX, &Y, search.x1, search.y1, search.x2, search.y2, CALIBRATION_FISH_COLOR, CALIBRATION_FISH_TOLERANCE) {
        xFish := foundX
        return true
    }

    if IsObject(CATCH_SCAN_COLOR_SET) {
        for _, color in CATCH_SCAN_COLOR_SET {
            if color = CALIBRATION_FISH_COLOR
                continue
            if PixelSearch(&foundX, &Y, search.x1, search.y1, search.x2, search.y2, color, CATCH_SCAN_COLOR_VARIATION) {
                xFish := foundX
                return true
            }
        }
    }

    return false
}

findWhiteControlBarBoundsOnLine(y, &bounds) {
    global CATCH_BAR, CATCH_WHITE_VARIATION

    runStart := 0
    bestStart := 0
    bestEnd := 0

    x := CATCH_BAR.x1
    while x <= CATCH_BAR.x2 {
        color := PixelGetColor(x, y, "RGB")
        if areColorsSimilar(color, "0xFFFFFF", CATCH_WHITE_VARIATION) {
            if runStart = 0
                runStart := x
        } else if runStart > 0 {
            runEnd := x - 1
            if (runEnd - runStart) > (bestEnd - bestStart) {
                bestStart := runStart
                bestEnd := runEnd
            }
            runStart := 0
        }
        x += 1
    }

    if runStart > 0 {
        runEnd := CATCH_BAR.x2
        if (runEnd - runStart) > (bestEnd - bestStart) {
            bestStart := runStart
            bestEnd := runEnd
        }
    }

    if bestEnd <= bestStart
        return false

    width := bestEnd - bestStart + 1
    if width < 18
        return false

    bounds := {x1: bestStart, x2: bestEnd, width: width}
    return true
}

getControlBarProperties(heartbeatMode := false) {
    global CATCH_BAR, CONTROL_BAR_WIDTH, CONTROL_BAR_HALF_WIDTH

    if heartbeatMode {
        if findHeartbeatMarkerX(CATCH_BAR, &markerX) {
            barLeft := Round(clampValue(markerX - CONTROL_BAR_HALF_WIDTH, CATCH_BAR.x1, CATCH_BAR.x2))
            return {isWhite: true, x: barLeft, source: "heartbeat", score: 100}
        }
    }

    if PixelSearch(&X, &Y, CATCH_BAR.x1, CATCH_BAR.y1, CATCH_BAR.x2, CATCH_BAR.y2, "0xffffff", 1)
        return {isWhite: true, x: X, source: "white", score: 0}

    return {isWhite: false, x: 0, source: "", score: 0}
}

findHeartbeatMarkerX(searchArea, &xCenter) {
    global HEARTBEAT_MARKER_COLOR, HEARTBEAT_MARKER_TOLERANCE, LAST_HEARTBEAT_X
    global HEARTBEAT_SCAN_CENTER_Y, HEARTBEAT_SCAN_Y_RADIUS, HEARTBEAT_MAX_JUMP_PX

    preferredX := LAST_HEARTBEAT_X > 0 ? LAST_HEARTBEAT_X : Round((searchArea.x1 + searchArea.x2) / 2)
    bestX := 0
    bestDelta := 999999

    yStart := Max(searchArea.y1, HEARTBEAT_SCAN_CENTER_Y - HEARTBEAT_SCAN_Y_RADIUS)
    yEnd := Min(searchArea.y2, HEARTBEAT_SCAN_CENTER_Y + HEARTBEAT_SCAN_Y_RADIUS)
    y := yStart
    while y <= yEnd {
        if PixelSearch(&foundX, &foundY, searchArea.x1, y, searchArea.x2, y, HEARTBEAT_MARKER_COLOR, HEARTBEAT_MARKER_TOLERANCE) {
            delta := Abs(foundX - preferredX)
            if delta < bestDelta {
                bestDelta := delta
                bestX := foundX
            }
        }
        y += 1
    }

    if bestX <= 0
        return false
    if LAST_HEARTBEAT_X > 0 && Abs(bestX - LAST_HEARTBEAT_X) > HEARTBEAT_MAX_JUMP_PX
        bestX := Round((LAST_HEARTBEAT_X * 0.7) + (bestX * 0.3))

    LAST_HEARTBEAT_X := bestX
    xCenter := bestX
    return true
}

getArrowOffsets() {
    global

    ; Always start from stable defaults so non-heartbeat rods recover cleanly
    ; even when calibration cannot find the arrow/fish pixels.
    LEFT_ARROW_TO_MIDDLE_OFFSET := 15
    RIGHT_ARROW_TO_MIDDLE_OFFSET := 15
    CONTROL_BAR_HALF_WIDTH := 15
    CONTROL_BAR_WIDTH := 30

    activateRoblox()
    area := CATCH_BAR_TOP_LINE
    if PixelSearch(&xFish, &Y, area.x1, area.y1, area.x2, area.y2, CALIBRATION_FISH_COLOR, CALIBRATION_FISH_TOLERANCE) {
        xFishMiddle := xFish + 1
        area := CATCH_BAR_ARROW_LINE
        if PixelSearch(&leftArrowX, &Y, area.x1, area.y1, area.x2, area.y2, CATCH_ARROW_COLOR, CATCH_ARROW_TOLERANCE) {
            LEFT_ARROW_TO_MIDDLE_OFFSET := xFishMiddle - leftArrowX
            RIGHT_ARROW_TO_MIDDLE_OFFSET := Max(1, LEFT_ARROW_TO_MIDDLE_OFFSET - 10)
            CONTROL_BAR_HALF_WIDTH := LEFT_ARROW_TO_MIDDLE_OFFSET + 9
            CONTROL_BAR_WIDTH := CONTROL_BAR_HALF_WIDTH * 2
            return
        }
    }
}

; ============================================================
; CEREBRA MINIGAME STATE MACHINE (Modular Extension)
; IDLE -> BITE_DETECTED -> MINIGAME_ACTIVE -> COMPLETE
; ============================================================

CEREBRA_STATE_IDLE := "IDLE"
CEREBRA_STATE_BITE_DETECTED := "BITE_DETECTED"
CEREBRA_STATE_MINIGAME_ACTIVE := "MINIGAME_ACTIVE"
CEREBRA_STATE_COMPLETE := "COMPLETE"

; Window Spy calibration note:
; 1) Open Window Spy while Roblox is active and set CoordMode Pixel/Mouse to Client.
; 2) Hover an always-on minigame UI pixel and copy client X/Y + color.
; 3) Put those values into CEREBRA_MINIGAME_START_PIXEL below.
CEREBRA_MINIGAME_START_PIXEL := {x: 400, y: 513, color: "0x434B5B", tolerance: 20}
CEREBRA_MINIGAME_START_IMAGE := "image.png"
CEREBRA_MINIGAME_START_IMAGE_ALT_1 := "image.webp"
CEREBRA_MINIGAME_START_IMAGE_ALT_2 := "CerebraMinigameUI.png"
CEREBRA_MINIGAME_START_IMAGE_ALT_3 := "CerebraMinigame.png"
CEREBRA_MINIGAME_START_TIMEOUT_MS := 5000
CEREBRA_MINIGAME_LOST_MAX_FRAMES := 20
CEREBRA_MINIGAME_START_REQUIRE_HEARTBEAT := false
CEREBRA_MINIGAME_START_CONFIRM_FRAMES := 2
CEREBRA_MINIGAME_REARM_DELAY_MS := 700
CEREBRA_MINIGAME_IMAGE_VARIATION := 65
CEREBRA_MINIGAME_IMAGE_SEARCH_PADDING_X := 120
CEREBRA_MINIGAME_IMAGE_SEARCH_PADDING_Y := 90
CEREBRA_MINIGAME_START_MIN_SCORE := 1
CEREBRA_MINIGAME_ICON_COLOR := "0xFF00A8"
CEREBRA_MINIGAME_ICON_COLOR_TOLERANCE := 65
CEREBRA_MINIGAME_ICON_MIN_HITS := 6
CEREBRA_MINIGAME_POLL_MIN_MS := 30
CEREBRA_MINIGAME_POLL_MAX_MS := 50
CEREBRA_INPUT_RANDOM_MIN_MS := 20
CEREBRA_INPUT_RANDOM_MAX_MS := 60
CEREBRA_USE_HOLD_REEL := true
CEREBRA_FORCE_CORRECT_ERROR_PX := 18
CEREBRA_TEXT_LOCK_ENABLED := true
CEREBRA_TEXT_LOCK_DARK_LUMA_MAX := 72
CEREBRA_TEXT_LOCK_MIN_PIXELS := 28
CEREBRA_TEXT_LOCK_MIN_WIDTH := 26
CEREBRA_TEXT_LOCK_MIN_HEIGHT := 6
CEREBRA_TEXT_LOCK_MAX_JUMP_PX := 90
CEREBRA_LAST_MINIGAME_END_TICK := 0
CEREBRA_LAST_TEXT_TARGET_X := 0
CEREBRA_IMAGE_TEMPLATE_WARNED := false
CEREBRA_IMAGESEARCH_ERROR_WARNED := false
CEREBRA_IMAGE_UNSUPPORTED_WARNED := false
CEREBRA_IMAGE_DISCOVERY_LOGGED := false

runCerebraMinigameAutomation() {
    global CEREBRA_STATE_BITE_DETECTED

    cerebraResetCycleState()
    sm := createCerebraMinigameState()
    cerebraSetState(sm, CEREBRA_STATE_BITE_DETECTED)
    sm.biteTick := A_TickCount

    updateStatus("Cerebra: waiting for minigame")
    Loop {
        result := cerebraTickMinigameState(sm)
        if result.done {
            cerebraResetCycleState()
            return result.success
        }
        Sleep cerebraGetPollDelay()
    }
}

createCerebraMinigameState() {
    global CEREBRA_STATE_IDLE

    return {
        state: CEREBRA_STATE_IDLE,
        biteTick: 0,
        minigameStartTick: 0,
        lastTick: A_TickCount,
        lostFrames: 0,
        startConfirmStreak: 0,
        startLastBy: "",
        controlState: createCatchingState(),
        success: false,
        reason: ""
    }
}

cerebraTickMinigameState(sm) {
    global CEREBRA_STATE_BITE_DETECTED, CEREBRA_STATE_MINIGAME_ACTIVE, CEREBRA_STATE_COMPLETE
    global CEREBRA_MINIGAME_START_TIMEOUT_MS, CEREBRA_MINIGAME_LOST_MAX_FRAMES
    global CEREBRA_MINIGAME_START_CONFIRM_FRAMES, CEREBRA_MINIGAME_REARM_DELAY_MS, CEREBRA_LAST_MINIGAME_END_TICK

    if !IsObject(sm)
        return {done: true, success: false, reason: "invalid_state"}

    now := A_TickCount
    if sm.state = CEREBRA_STATE_BITE_DETECTED {
        ; Rearm guard: prevent end-of-minigame remnants from instantly retriggering.
        if CEREBRA_LAST_MINIGAME_END_TICK > 0 && (now - CEREBRA_LAST_MINIGAME_END_TICK) < CEREBRA_MINIGAME_REARM_DELAY_MS
            return {done: false}

        startDetected := detectCerebraMinigameStart(&detectedBy)
        ; Multi-signal detector already scores independent cues; no fish-gate needed here.
        qualifies := startDetected
        if qualifies {
            sm.startConfirmStreak += 1
            sm.startLastBy := detectedBy
            updateStatus("Cerebra: start signal " sm.startConfirmStreak "/" CEREBRA_MINIGAME_START_CONFIRM_FRAMES " (" detectedBy ")")
            if sm.startConfirmStreak >= CEREBRA_MINIGAME_START_CONFIRM_FRAMES {
                cerebraSetState(sm, CEREBRA_STATE_MINIGAME_ACTIVE)
                sm.minigameStartTick := now
                updateStatus("Cerebra: minigame active (" sm.startLastBy ")")
                return {done: false}
            }
        } else {
            sm.startConfirmStreak := 0
            sm.startLastBy := ""
        }

        if (now - sm.biteTick) > CEREBRA_MINIGAME_START_TIMEOUT_MS {
            sm.reason := "minigame_start_timeout"
            cerebraSetState(sm, CEREBRA_STATE_COMPLETE)
            cerebraMarkMinigameEnd()
            logErrorCode("CEREBRA_START_TIMEOUT", "Minigame did not appear in time. Resetting cycle.", "WARN")
            return {done: true, success: false, reason: sm.reason}
        }
        return {done: false}
    }

    if sm.state = CEREBRA_STATE_MINIGAME_ACTIVE {
        if !isCatchBarDisplayed() {
            sm.lostFrames += 1
            if sm.lostFrames > CEREBRA_MINIGAME_LOST_MAX_FRAMES {
                sm.reason := "minigame_lost"
                cerebraSetState(sm, CEREBRA_STATE_COMPLETE)
                releaseControl(sm.controlState)
                cerebraMarkMinigameEnd()
                return {done: true, success: false, reason: sm.reason}
            }
        } else {
            sm.lostFrames := 0
        }

        if detectCatchPopupByRegex(&matchType, &ocrText, &ocrAvailable) {
            sm.reason := "popup_" matchType
            sm.success := (matchType = "success")
            cerebraSetState(sm, CEREBRA_STATE_COMPLETE)
            releaseControl(sm.controlState)
            cerebraMarkMinigameEnd()
            return {done: true, success: sm.success, reason: sm.reason}
        }

        if !cerebraHandleMinigameControl(sm.controlState) {
            sm.reason := "control_signal_missing"
            cerebraSetState(sm, CEREBRA_STATE_COMPLETE)
            releaseControl(sm.controlState)
            cerebraMarkMinigameEnd()
            return {done: true, success: false, reason: sm.reason}
        }

        return {done: false}
    }

    if sm.state = CEREBRA_STATE_COMPLETE
        return {done: true, success: sm.success, reason: sm.reason}

    return {done: true, success: false, reason: "unexpected_state"}
}

cerebraSetState(sm, nextState) {
    if !IsObject(sm)
        return
    sm.state := nextState
}

cerebraMarkMinigameEnd() {
    global CEREBRA_LAST_MINIGAME_END_TICK
    CEREBRA_LAST_MINIGAME_END_TICK := A_TickCount
}

cerebraResetCycleState() {
    global CEREBRA_LAST_TEXT_TARGET_X, LAST_HEARTBEAT_X

    CEREBRA_LAST_TEXT_TARGET_X := 0
    LAST_HEARTBEAT_X := 0
    try SendEvent "{Click up}"
}

detectCerebraMinigameStart(&detectedBy := "") {
    global CEREBRA_MINIGAME_START_PIXEL, CEREBRA_MINIGAME_START_IMAGE, CATCH_BAR
    global CEREBRA_MINIGAME_START_REQUIRE_HEARTBEAT, CEREBRA_MINIGAME_START_MIN_SCORE
    global CEREBRA_IMAGE_TEMPLATE_WARNED

    detectedBy := ""
    activateRoblox()

    signalScore := 0
    reason := ""

    if cerebraDetectMinigameByImage(&imageReason, &imageAttempted) {
        detectedBy := imageReason
        return true
    } else if !CEREBRA_IMAGE_TEMPLATE_WARNED {
        CEREBRA_IMAGE_TEMPLATE_WARNED := true
        logErrorCode("CEREBRA_IMAGE_TEMPLATE_MISSING", "No Cerebra minigame template found in Assets. Using signal fallback.", "WARN")
    }

    if cerebraHasActiveBarRun() {
        signalScore += 1
        reason .= "barrun+"
    }

    if isCatchBarDisplayed() {
        signalScore += 1
        reason .= "catchbar+"
    }

    heartbeatFound := false
    if findHeartbeatMarkerX(CATCH_BAR, &hbX) {
        heartbeatFound := true
        signalScore += 1
        reason .= "heartbeat+"
    }

    if PixelSearch(&ax, &ay, CATCH_BAR_ARROW_LINE.x1, CATCH_BAR_ARROW_LINE.y1, CATCH_BAR_ARROW_LINE.x2, CATCH_BAR_ARROW_LINE.y2, CATCH_ARROW_COLOR, CATCH_ARROW_TOLERANCE + 6) {
        signalScore += 1
        reason .= "arrow+"
    }

    if cerebraDetectMinigameByIconColor() {
        signalScore += 1
        reason .= "iconcolor+"
    }

    ; Single-pixel check (Window Spy calibrated).
    p := CEREBRA_MINIGAME_START_PIXEL
    color := PixelGetColor(p.x, p.y, "RGB")
    if areColorsSimilar(color, p.color, p.tolerance) {
        signalScore += 1
        reason .= "pixel+"
    }

    ; Pixel samples across active row to avoid single-point misses.
    sampleY := p.y
    sampleX := [CATCH_BAR.x1 + 24, Round((CATCH_BAR.x1 + CATCH_BAR.x2) / 2), CATCH_BAR.x2 - 24]
    for _, sx in sampleX {
        c := PixelGetColor(sx, sampleY, "RGB")
        if areColorsSimilar(c, p.color, p.tolerance + 10) {
            signalScore += 1
            reason .= "scan+"
            break
        }
    }

    if CEREBRA_MINIGAME_START_REQUIRE_HEARTBEAT && !heartbeatFound
        return false

    ; Require multiple independent signals to avoid false positives at teardown.
    if signalScore >= CEREBRA_MINIGAME_START_MIN_SCORE {
        detectedBy := RTrim(reason, "+")
        return true
    }

    return false
}

cerebraDetectMinigameByIconColor() {
    global CATCH_BAR, CEREBRA_MINIGAME_ICON_COLOR, CEREBRA_MINIGAME_ICON_COLOR_TOLERANCE, CEREBRA_MINIGAME_ICON_MIN_HITS

    ; Scan around the minigame widget where the magenta icon/text appears.
    x1 := Max(0, CATCH_BAR.x1 - 150)
    y1 := Max(0, CATCH_BAR.y1 - 120)
    x2 := CATCH_BAR.x2 + 150
    y2 := CATCH_BAR.y2 - 8
    if x2 <= x1 || y2 <= y1
        return false

    hits := 0
    probeX := x1
    loop 18 {
        if probeX > x2
            break
        if PixelSearch(&fx, &fy, probeX, y1, x2, y2, CEREBRA_MINIGAME_ICON_COLOR, CEREBRA_MINIGAME_ICON_COLOR_TOLERANCE) {
            hits += 1
            if hits >= CEREBRA_MINIGAME_ICON_MIN_HITS
                return true
            probeX := fx + 8
            continue
        }
        break
    }
    return false
}

cerebraDetectMinigameByImage(&reason := "", &attempted := false) {
    global CEREBRA_MINIGAME_START_IMAGE, CEREBRA_MINIGAME_START_IMAGE_ALT_1, CEREBRA_MINIGAME_START_IMAGE_ALT_2, CEREBRA_MINIGAME_START_IMAGE_ALT_3
    global CEREBRA_MINIGAME_IMAGE_VARIATION, CEREBRA_MINIGAME_IMAGE_SEARCH_PADDING_X, CEREBRA_MINIGAME_IMAGE_SEARCH_PADDING_Y
    global CATCH_BAR, CEREBRA_IMAGESEARCH_ERROR_WARNED, CEREBRA_IMAGE_UNSUPPORTED_WARNED

    reason := ""
    attempted := false
    candidates := getCerebraImageTemplateCandidates()

    baseX1 := Max(0, CATCH_BAR.x1 - CEREBRA_MINIGAME_IMAGE_SEARCH_PADDING_X)
    baseY1 := Max(0, CATCH_BAR.y1 - CEREBRA_MINIGAME_IMAGE_SEARCH_PADDING_Y)
    baseX2 := CATCH_BAR.x2 + CEREBRA_MINIGAME_IMAGE_SEARCH_PADDING_X
    baseY2 := CATCH_BAR.y2 + CEREBRA_MINIGAME_IMAGE_SEARCH_PADDING_Y
    regions := [
        {x1: baseX1, y1: baseY1, x2: baseX2, y2: baseY2},
        {x1: CATCH_BAR.x1, y1: Max(0, CATCH_BAR.y1 - 25), x2: CATCH_BAR.x2, y2: CATCH_BAR.y2},
        {x1: CATCH_BAR.x1 + 25, y1: Max(0, CATCH_BAR.y1 - 40), x2: CATCH_BAR.x2 - 25, y2: CATCH_BAR.y2}
    ]
    variations := [40, 55, CEREBRA_MINIGAME_IMAGE_VARIATION, 80]

    for _, templatePath in candidates {
        attempted := true
        ext := StrLower("." RegExReplace(templatePath, "^.*\.([^.\\\/]+)$", "$1"))
        if ext != ".png" && ext != ".bmp" && ext != ".jpg" && ext != ".jpeg" {
            if !CEREBRA_IMAGE_UNSUPPORTED_WARNED {
                CEREBRA_IMAGE_UNSUPPORTED_WARNED := true
                logErrorCode("CEREBRA_IMAGE_UNSUPPORTED", "Unsupported ImageSearch format: " templatePath ". Use PNG/JPG/BMP.", "WARN")
            }
            continue
        }

        ; Use safe native-size matching first (avoids invalid scale parameters).
        for _, reg in regions {
            for _, v in variations {
                spec := "*" v " " templatePath
                if safeImageSearch(&ix, &iy, reg.x1, reg.y1, reg.x2, reg.y2, spec) {
                    reason := "image:" templatePath "@v" v
                    return true
                }
            }
        }

        ; Tiny bright glyph templates often benefit from transparency matching.
        for _, reg in regions {
            specTrans := "*" CEREBRA_MINIGAME_IMAGE_VARIATION " *TransBlack " templatePath
            if safeImageSearch(&ix, &iy, reg.x1, reg.y1, reg.x2, reg.y2, specTrans) {
                reason := "image:" templatePath "@trans"
                return true
            }
        }
    }

    if attempted && !CEREBRA_IMAGESEARCH_ERROR_WARNED {
        CEREBRA_IMAGESEARCH_ERROR_WARNED := true
        logEvent("ImageSearch attempted but no supported template matched. Prefer Assets\\image.png.", "WARN")
    }
    return false
}

getCerebraImageTemplateCandidates() {
    global CEREBRA_MINIGAME_START_IMAGE, CEREBRA_MINIGAME_START_IMAGE_ALT_1, CEREBRA_MINIGAME_START_IMAGE_ALT_2, CEREBRA_MINIGAME_START_IMAGE_ALT_3
    global CEREBRA_IMAGE_DISCOVERY_LOGGED

    candidates := []
    seen := Map()
    assetDirs := getCerebraAssetDirectories()

    ; Preferred explicit paths first.
    appendUniqueTemplateCandidate(&candidates, seen, CEREBRA_MINIGAME_START_IMAGE, assetDirs)
    appendUniqueTemplateCandidate(&candidates, seen, CEREBRA_MINIGAME_START_IMAGE_ALT_1, assetDirs)
    appendUniqueTemplateCandidate(&candidates, seen, CEREBRA_MINIGAME_START_IMAGE_ALT_2, assetDirs)
    appendUniqueTemplateCandidate(&candidates, seen, CEREBRA_MINIGAME_START_IMAGE_ALT_3, assetDirs)

    ; Auto-discover supported templates in Assets.
    for _, assetsDir in assetDirs {
        if DirExist(assetsDir) {
            Loop Files, assetsDir "\*.*", "F" {
                ext := StrLower(A_LoopFileExt)
                if ext = "png" || ext = "jpg" || ext = "jpeg" || ext = "bmp"
                    appendUniqueTemplateCandidate(&candidates, seen, A_LoopFilePath, assetDirs)
            }
        }
    }

    if !CEREBRA_IMAGE_DISCOVERY_LOGGED {
        CEREBRA_IMAGE_DISCOVERY_LOGGED := true
        logEvent("Cerebra image discovery dirs=" joinArray(assetDirs, ";") " candidates=" candidates.Length, "DEBUG")
    }

    return candidates
}

appendUniqueTemplateCandidate(&candidates, seenMap, pathOrName, assetDirs) {
    p := resolveTemplatePath(pathOrName, assetDirs)
    if p = ""
        return
    key := StrLower(p)
    if seenMap.Has(key)
        return
    seenMap[key] := true
    candidates.Push(p)
}

resolveTemplatePath(pathOrName, assetDirs) {
    value := Trim("" pathOrName)
    if value = ""
        return ""

    if FileExist(value)
        return value

    for _, dirPath in assetDirs {
        candidate := dirPath "\" value
        if FileExist(candidate)
            return candidate
    }
    return ""
}

getCerebraAssetDirectories() {
    dirs := []
    seen := Map()
    appendUniqueDirectory(&dirs, seen, A_ScriptDir "\Assets")
    appendUniqueDirectory(&dirs, seen, A_ScriptDir "\..\Assets")
    appendUniqueDirectory(&dirs, seen, A_WorkingDir "\Assets")

    return dirs
}

appendUniqueDirectory(&dirs, seenMap, path) {
    p := Trim("" path)
    if p = ""
        return
    key := StrLower(p)
    if seenMap.Has(key)
        return
    seenMap[key] := true
    dirs.Push(p)
}

joinArray(values, sep := ",") {
    out := ""
    for idx, val in values {
        if idx > 1
            out .= sep
        out .= val
    }
    return out
}


safeImageSearch(&outX, &outY, x1, y1, x2, y2, spec) {
    global CEREBRA_IMAGESEARCH_ERROR_WARNED

    if x2 <= x1 || y2 <= y1
        return false
    try {
        return ImageSearch(&outX, &outY, x1, y1, x2, y2, spec)
    } catch as err {
        if !CEREBRA_IMAGESEARCH_ERROR_WARNED {
            CEREBRA_IMAGESEARCH_ERROR_WARNED := true
            logErrorCode("CEREBRA_IMAGESEARCH_INVALID", "ImageSearch invalid parameter. Spec='" spec "'. " err.Message, "WARN")
        }
        return false
    }
}

cerebraHasActiveBarRun() {
    global CATCH_BAR_TOP_LINE, CATCH_BAR_ACTIVE_COLOR, CATCH_BAR_ACTIVE_VARIATION, CATCH_BAR_ACTIVE_MIN_RUN
    global CALIBRATION_FISH_COLOR, CALIBRATION_FISH_TOLERANCE

    targetColor := IsSet(CATCH_BAR_ACTIVE_COLOR) ? CATCH_BAR_ACTIVE_COLOR : CALIBRATION_FISH_COLOR
    tol := IsSet(CATCH_BAR_ACTIVE_VARIATION) ? CATCH_BAR_ACTIVE_VARIATION : Max(8, CALIBRATION_FISH_TOLERANCE + 12)
    minRun := IsSet(CATCH_BAR_ACTIVE_MIN_RUN) ? CATCH_BAR_ACTIVE_MIN_RUN : 48

    run := 0
    bestRun := 0
    x := CATCH_BAR_TOP_LINE.x1
    y := CATCH_BAR_TOP_LINE.y1
    while x <= CATCH_BAR_TOP_LINE.x2 {
        c := PixelGetColor(x, y, "RGB")
        if areColorsSimilar(c, targetColor, tol) {
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

cerebraHandleMinigameControl(controlState) {
    global CATCH_BAR_TOP_LINE, CONTROL_BAR_HALF_WIDTH, CEREBRA_FORCE_CORRECT_ERROR_PX, CEREBRA_TEXT_LOCK_ENABLED
    global CATCHING_LOOKAHEAD_MS, CATCHING_DEADZONE_PX

    if !IsObject(controlState)
        return false

    now := A_TickCount
    if !controlState.HasOwnProp("lastTick")
        controlState.lastTick := now
    dt := Max(now - controlState.lastTick, 1)

    fishDetected := false
    if CEREBRA_TEXT_LOCK_ENABLED
        fishDetected := detectCerebraBlackTextTargetX(&xFish, &textPixels, &textW, &textH)

    if !fishDetected
        fishDetected := findFishIndicatorX(CATCH_BAR_TOP_LINE, &xFish)
    if !fishDetected {
        if !controlState.hasFish
            return false
        xFish := Round(clampValue(controlState.lastFishX, CATCH_BAR_TOP_LINE.x1, CATCH_BAR_TOP_LINE.x2))
    }
    updateFishState(controlState, xFish, dt)

    controlBar := getControlBarProperties(true)
    if !controlBar.isWhite
        return false

    barMiddleX := controlBar.x + CONTROL_BAR_HALF_WIDTH
    updateBarState(controlState, barMiddleX, dt)
    controlState.lastTick := now

    ; In Cerebra lock mode we want direct overlap on the black text/wave target.
    predictedFishX := clampValue(xFish, CATCH_BAR_TOP_LINE.x1, CATCH_BAR_TOP_LINE.x2)
    error := predictedFishX - barMiddleX
    deadzone := Max(2, Floor(CATCHING_DEADZONE_PX * 0.7))
    forceThreshold := Max(CEREBRA_FORCE_CORRECT_ERROR_PX, Round(CONTROL_BAR_HALF_WIDTH * 0.8))
    direction := Abs(error) <= deadzone ? 0 : (error > 0 ? 1 : -1)
    if Abs(error) >= forceThreshold
        direction := error > 0 ? 1 : -1
    cerebraApplyHumanInput(controlState, direction)
    return true
}

detectCerebraBlackTextTargetX(&targetX, &pixelCount := 0, &boxW := 0, &boxH := 0) {
    global CATCH_BAR, CATCH_BAR_TOP_LINE, CEREBRA_TEXT_LOCK_DARK_LUMA_MAX, CEREBRA_TEXT_LOCK_MIN_PIXELS
    global CEREBRA_TEXT_LOCK_MIN_WIDTH, CEREBRA_TEXT_LOCK_MIN_HEIGHT, CEREBRA_TEXT_LOCK_MAX_JUMP_PX, CEREBRA_LAST_TEXT_TARGET_X

    x1 := CATCH_BAR.x1 + 18
    x2 := CATCH_BAR.x2 - 18
    y1 := Max(0, CATCH_BAR_TOP_LINE.y1 - 8)
    y2 := CATCH_BAR_TOP_LINE.y1 + 8
    if x2 <= x1 || y2 <= y1
        return false

    minX := 99999
    maxX := -1
    minY := 99999
    maxY := -1
    pixels := 0

    y := y1
    while y <= y2 {
        x := x1
        while x <= x2 {
            c := PixelGetColor(x, y, "RGB")
            if getPixelLuma(c) <= CEREBRA_TEXT_LOCK_DARK_LUMA_MAX {
                pixels += 1
                if x < minX
                    minX := x
                if x > maxX
                    maxX := x
                if y < minY
                    minY := y
                if y > maxY
                    maxY := y
            }
            x += 1
        }
        y += 1
    }

    if pixels < CEREBRA_TEXT_LOCK_MIN_PIXELS
        return false
    if maxX <= minX || maxY <= minY
        return false

    width := maxX - minX + 1
    height := maxY - minY + 1
    if width < CEREBRA_TEXT_LOCK_MIN_WIDTH || height < CEREBRA_TEXT_LOCK_MIN_HEIGHT
        return false

    cx := Round((minX + maxX) / 2)
    if CEREBRA_LAST_TEXT_TARGET_X > 0 && Abs(cx - CEREBRA_LAST_TEXT_TARGET_X) > CEREBRA_TEXT_LOCK_MAX_JUMP_PX
        cx := Round((CEREBRA_LAST_TEXT_TARGET_X * 0.65) + (cx * 0.35))

    CEREBRA_LAST_TEXT_TARGET_X := cx
    targetX := cx
    pixelCount := pixels
    boxW := width
    boxH := height
    return true
}

cerebraApplyHumanInput(controlState, direction) {
    global CEREBRA_USE_HOLD_REEL, CEREBRA_INPUT_RANDOM_MIN_MS, CEREBRA_INPUT_RANDOM_MAX_MS

    if CEREBRA_USE_HOLD_REEL {
        setControlDirectionSafe(controlState, direction)
        if direction = 0
            releaseControl(controlState)
    } else {
        if direction > 0 {
            if ensureInputCursorInRoblox()
                SendEvent "{Click}"
        } else {
            releaseControl(controlState)
        }
    }

    Sleep cerebraRandomDelay(CEREBRA_INPUT_RANDOM_MIN_MS, CEREBRA_INPUT_RANDOM_MAX_MS)
}

setControlDirectionSafe(state, direction) {
    activateRoblox()
    if !ensureInputCursorInRoblox() {
        releaseControl(state)
        return
    }
    setControlDirection(state, direction)

    ; Watchdog: if we still need hold but state isn't down, force it periodically.
    if IsObject(state) && direction > 0 {
        now := A_TickCount
        if !state.clickDown || (now - state.lastHoldEnsureTick) > 350 {
            SendEvent "{Click up}"
            Sleep 10
            SendEvent "{Click down}"
            state.clickDown := true
            state.lastHoldEnsureTick := now
        }
    }
}

canSendInputToRoblox() {
    hwnd := WinExist("ahk_exe RobloxPlayerBeta.exe")
    if !hwnd
        return false
    if !WinActive("ahk_id " hwnd)
        return false
    WinGetClientPos &cx, &cy, &cw, &ch, "ahk_id " hwnd
    if cw <= 0 || ch <= 0
        return false
    return true
}

ensureInputCursorInRoblox() {
    global CATCH_BAR_TOP_LINE

    if !canSendInputToRoblox() {
        activateRoblox()
        Sleep 20
    }
    if !canSendInputToRoblox()
        return false

    hwnd := WinExist("ahk_exe RobloxPlayerBeta.exe")
    WinGetClientPos &cx, &cy, &cw, &ch, "ahk_id " hwnd
    if cw <= 0 || ch <= 0
        return false

    oldMouseMode := A_CoordModeMouse
    CoordMode "Mouse", "Screen"
    MouseGetPos &mx, &my

    inside := (mx >= cx && mx <= (cx + cw) && my >= cy && my <= (cy + ch))
    if !inside {
        safeClientX := Round(clampValue((CATCH_BAR_TOP_LINE.x1 + CATCH_BAR_TOP_LINE.x2) / 2, 0, cw - 1))
        safeClientY := Round(clampValue(CATCH_BAR_TOP_LINE.y1, 0, ch - 1))
        MouseMove(cx + safeClientX, cy + safeClientY, 0)
    }

    CoordMode "Mouse", oldMouseMode
    return true
}

cerebraGetPollDelay() {
    global CEREBRA_MINIGAME_POLL_MIN_MS, CEREBRA_MINIGAME_POLL_MAX_MS
    return cerebraRandomDelay(CEREBRA_MINIGAME_POLL_MIN_MS, CEREBRA_MINIGAME_POLL_MAX_MS)
}

cerebraRandomDelay(minMs, maxMs) {
    return Random(minMs, maxMs)
}

getPixelLuma(color) {
    c := colorToInt(color)
    r := (c >> 16) & 0xFF
    g := (c >> 8) & 0xFF
    b := c & 0xFF
    return (0.2126 * r) + (0.7152 * g) + (0.0722 * b)
}

areColorsSimilar(colorA, colorB, tolerance) {
    cA := colorToInt(colorA)
    cB := colorToInt(colorB)

    rA := (cA >> 16) & 0xFF
    gA := (cA >> 8) & 0xFF
    bA := cA & 0xFF

    rB := (cB >> 16) & 0xFF
    gB := (cB >> 8) & 0xFF
    bB := cB & 0xFF

    return Abs(rA - rB) <= tolerance && Abs(gA - gB) <= tolerance && Abs(bA - bB) <= tolerance
}

colorToInt(colorValue) {
    if IsNumber(colorValue)
        return colorValue + 0
    value := Trim("" colorValue)
    if value = ""
        return 0
    if RegExMatch(value, "i)^0x[0-9a-f]+$")
        return value + 0
    try return value + 0
    catch
        return 0
}

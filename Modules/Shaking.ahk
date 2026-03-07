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
SHAKE_IMAGE := 'Assets\Shake.png'
MAX_SHAKES := 50


autoShake() {
    previousMouseDelay := A_MouseDelay
    SetMouseDelay -1

    try {
        updateStatus("Shaking.")

        activateRoblox()

        shakePin := createShakeAreaPin()
        cerebraMode := isCerebraRodSelected()
        fastLureMode := isFastLureSpeedRod()

        ; High-lure rods (including Cerebra) frequently skip visible shake almost instantly.
        if fastLureMode || cerebraMode {
            updateStatus("Shaking: fast skip")
            Loop 2 {
                if ImageSearch(&X, &Y, SHAKE_AREA.x1, SHAKE_AREA.y1, SHAKE_AREA.x2, SHAKE_AREA.y2, "*40 *TransFF0000 " SHAKE_IMAGE)
                    SendEvent "{Click, " X ", " Y "}"
                Sleep 20
            }
            Sleep 160
            shakePin.Destroy()
            updateStatus("")
            return true
        }

        lastShake := {x: 0, y: 0}
        success := false
        shakeClicks := 0
        noShakeFrames := 0

        Loop MAX_SHAKES {
            updateStatus("Shaking: " A_Index "/" MAX_SHAKES)

            activateRoblox()

            if ImageSearch(&X, &Y, SHAKE_AREA.x1, SHAKE_AREA.y1, SHAKE_AREA.x2, SHAKE_AREA.y2, "*40 *TransFF0000 " SHAKE_IMAGE) {
                SendEvent "{Click, " X ", " Y "}"
                lastShake := {x: X, y: Y}
                shakeClicks += 1
                noShakeFrames := 0
                MouseMove SHAKE_AREA.x2, SHAKE_AREA.y2
                Loop 5 {
                    if !ImageSearch(&X, &Y, SHAKE_AREA.x1, SHAKE_AREA.y1, SHAKE_AREA.x2, SHAKE_AREA.y2, "*40 *TransFF0000 " SHAKE_IMAGE)
                        break
                    Sleep 10
                }
            } else if cerebraMode || fastLureMode {
                noShakeFrames += 1
                if cerebraMode && Mod(noShakeFrames, CEREBRA_SHAKE_FALLBACK_CLICK_INTERVAL) = 0 {
                    fallbackX := Round((SHAKE_AREA.x1 + SHAKE_AREA.x2) / 2)
                    fallbackY := Round((SHAKE_AREA.y1 + SHAKE_AREA.y2) / 2)
                    SendEvent "{Click, " fallbackX ", " fallbackY "}"
                }
            }
            Sleep 10

            if isCatchBarDisplayed() {
                updateStatus("")
                success := true
                break
            }
            if fastLureMode {
                if noShakeFrames >= FAST_LURE_NO_IMAGE_ADVANCE_FRAMES || A_Index >= FAST_LURE_FORCE_ADVANCE_FRAMES {
                    updateStatus("")
                    success := true
                    break
                }
            }
            if cerebraMode {
                if isCerebraCatchBarDisplayedByColor() {
                    updateStatus("")
                    success := true
                    break
                }
                if noShakeFrames >= CEREBRA_FORCE_ADVANCE_NO_IMAGE_FRAMES || A_Index >= CEREBRA_FORCE_ADVANCE_MAX_FRAMES {
                    updateStatus("")
                    success := true
                    break
                }
            }
            if cerebraMode && noShakeFrames >= CEREBRA_SHAKE_NO_IMAGE_FRAMES {
                if shakeClicks > 0 || isCerebraCatchBarDisplayedByColor() {
                    updateStatus("")
                    success := true
                    break
                }
                noShakeFrames := 0
            }
        }

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
    global CATCH_SCAN_AREA, CATCH_SCAN_LINE, CATCH_SCAN_COLOR_SET, CATCH_SCAN_COLOR_VARIATION

    activateRoblox()

    if IsObject(CATCH_SCAN_AREA) && IsObject(CATCH_SCAN_COLOR_SET) {
        y1 := CATCH_SCAN_AREA.y1
        y2 := CATCH_SCAN_AREA.y2
        while y1 <= y2 {
            if hasCatchColorOnLine(CATCH_SCAN_AREA.x1, y1, CATCH_SCAN_AREA.x2, CATCH_SCAN_COLOR_SET, CATCH_SCAN_COLOR_VARIATION)
                return true
            y1 += 2
        }
        if hasCatchColorOnLine(CATCH_SCAN_LINE.x1, CATCH_SCAN_LINE.y, CATCH_SCAN_LINE.x2, CATCH_SCAN_COLOR_SET, CATCH_SCAN_COLOR_VARIATION)
            return true
    }

    pixel := UI_CATCH_BAR_PIXEL
    if PixelSearch(&X, &Y, pixel.x, pixel.y, pixel.x, pixel.y, pixel.colour, 2)
        return true

    if isCerebraRodSelected()
        return isCerebraCatchBarDisplayedByColor()
    return false
}

hasCatchColorOnLine(x1, y, x2, colorSet, variation) {
    for _, target in colorSet {
        if PixelSearch(&foundX, &foundY, x1, y, x2, y, target, variation)
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
    WinGetClientPos &winX0, &winY0, , , "ahk_exe RobloxPlayerBeta.exe"
    x1 := winX0 + SHAKE_AREA.x1
    y1 := winY0 + SHAKE_AREA.y1
    x2 := winX0 + SHAKE_AREA.x2
    y2 := winY0 + SHAKE_AREA.y2
    return Pin(x1, y1, x2, y2, 60000, "b1 flash0 c3cff00")
}

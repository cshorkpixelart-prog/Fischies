#Requires AutoHotkey v2.0

UI_CATCH_BAR_PIXEL := {x: 399, y: 505, colour: "0x434b5b"}
CATCH_BAR_ACTIVE_SCAN := {x1: 300, y1: 503, x2: 500, y2: 513}
CATCH_BAR_ACTIVE_COLOR := "0x434b5b"
CATCH_BAR_ACTIVE_VARIATION := 18
CATCH_BAR_ACTIVE_MIN_RUN := 52
FAST_LURE_SKIP_THRESHOLD := 100
FAST_LURE_FORCE_ADVANCE_FRAMES := 4
FAST_LURE_NO_IMAGE_ADVANCE_FRAMES := 2
FAST_SKIP_CLICK_DELAY_MS := 0
FAST_SKIP_SETTLE_DELAY_MS := 1
SHAKE_LOOP_DELAY_MS := 0

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
        fastLureMode := isFastLureSpeedRod()

        ; High-lure rods often skip visible shake almost instantly.
        if fastLureMode {
            updateStatus("Shaking: fast skip")
            Loop 2 {
                if ImageSearch(&X, &Y, SHAKE_AREA.x1, SHAKE_AREA.y1, SHAKE_AREA.x2, SHAKE_AREA.y2, "*40 *TransFF0000 " SHAKE_IMAGE)
                    SendEvent "{Click, " X ", " Y "}"
                Sleep FAST_SKIP_CLICK_DELAY_MS
            }
            Sleep FAST_SKIP_SETTLE_DELAY_MS
            shakePin.Destroy()
            updateStatus("")
            return true
        }

        lastShake := {x: 0, y: 0}
        success := false
        noShakeFrames := 0

        Loop MAX_SHAKES {

            updateStatus("Shaking: " A_Index "/" MAX_SHAKES)

            activateRoblox()

            if ImageSearch(&X, &Y, SHAKE_AREA.x1, SHAKE_AREA.y1, SHAKE_AREA.x2, SHAKE_AREA.y2, "*40 *TransFF0000 " SHAKE_IMAGE) {
                SendEvent "{Click, " X ", " Y "}"
                lastShake := {x: X, y: Y}
                noShakeFrames := 0
            } else if fastLureMode {
                noShakeFrames += 1
            }
            Sleep SHAKE_LOOP_DELAY_MS

            if isCatchBarDisplayed() {
                updateStatus("")
                success := true
                break
            }
            if fastLureMode {
                ; Rods with >=100% lure speed usually skip shake almost immediately.
                if noShakeFrames >= FAST_LURE_NO_IMAGE_ADVANCE_FRAMES || A_Index >= FAST_LURE_FORCE_ADVANCE_FRAMES {
                    updateStatus("")
                    success := true
                    break
                }
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
    activateRoblox()
    area := CATCH_BAR_ACTIVE_SCAN
    target := CATCH_BAR_ACTIVE_COLOR
    variation := CATCH_BAR_ACTIVE_VARIATION
    minRun := CATCH_BAR_ACTIVE_MIN_RUN

    y := area.y1
    while y <= area.y2 {
        run := 0
        bestRun := 0
        x := area.x1
        while x <= area.x2 {
            color := PixelGetColor(x, y, "RGB")
            if areColorsSimilar(color, target, variation) {
                run += 1
                if run > bestRun
                    bestRun := run
            } else {
                run := 0
            }
            x += 1
        }
        if bestRun >= minRun
            return true
        y += 2
    }

    ; Fallback point check to avoid regressions on unusual graphics settings.
    pixel := UI_CATCH_BAR_PIXEL
    return PixelSearch(&X, &Y, pixel.x, pixel.y, pixel.x, pixel.y, pixel.colour, 2)
}

createShakeAreaPin() {
    WinGetClientPos &winX0, &winY0, , , "ahk_exe RobloxPlayerBeta.exe"
    x1 := winX0 + SHAKE_AREA.x1
    y1 := winY0 + SHAKE_AREA.y1
    x2 := winX0 + SHAKE_AREA.x2
    y2 := winY0 + SHAKE_AREA.y2
    return Pin(x1, y1, x2, y2, 60000, "b1 flash0 c3cff00")
}

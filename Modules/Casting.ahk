#Requires AutoHotkey v2.0

; Green target zone doesn't detect well at night.

CAST_BAR_SEARCH := {x1: 1, y1: 57, x2: 804, y2: 620}
CAST_BAR_GREEN := "0x5da349"
CAST_BAR_WHITE := "0xfbfbf0"

CAST_MAX_LOOPS := 5
CAST_TOOLTIP_LOCATION := {x: 1000, y: 10}

MIDDLE_SCREEN_X := 400
MIDDLE_SCREEN_Y := 300


TARGET_ZONE_Y_OFFSET := 5
TARGET_ZONE_X_OFFSET := 2

castLine() {
    activateRoblox()
    updateStatus("Casting line.")

    MouseMove MIDDLE_SCREEN_X, MIDDLE_SCREEN_Y

    SendEvent "{Click down}"

    Loop CAST_MAX_LOOPS {
        activateRoblox()
        Sleep 10

        updateStatus("Casting line: " A_Index "/" CAST_MAX_LOOPS)

        slider := getTopOfSlider()
        if !slider
            continue

        MouseMove slider.x, slider.y

        if isInTargetZone(slider)
            break
    }

    SendEvent "{Click up}"
    Sleep 100

    updateStatus("")
    return true
}

isInTargetZone(slider) {
    return PixelSearch(&X, &Y, slider.x - TARGET_ZONE_X_OFFSET, slider.y - TARGET_ZONE_Y_OFFSET, slider.x + TARGET_ZONE_X_OFFSET, slider.y, CAST_BAR_GREEN, 25)
}

getTopOfSlider() {
    if PixelSearch(&X, &Y, CAST_BAR_SEARCH.x1, CAST_BAR_SEARCH.y1, CAST_BAR_SEARCH.x2, CAST_BAR_SEARCH.y2, CAST_BAR_WHITE, 2)
        return {x: X, y: Y}
    else
        return false
}

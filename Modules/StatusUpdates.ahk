#Requires AutoHotkey v2.0

STATUS_HUD_GUI := false
STATUS_HUD_TITLE_CTRL := false
STATUS_HUD_TIME_CTRL := false
STATUS_HUD_STATUS_CTRL := false
STATUS_HUD_LOG_CTRL := false
STATUS_HUD_LINES := []

CATCH_DEBUG_GUI := false
CATCH_DEBUG_TRACK_W := 620
CATCH_DEBUG_MIN_X := 0
CATCH_DEBUG_MAX_X := 1
CATCH_DEBUG_BOUND_LEFT := false
CATCH_DEBUG_BOUND_RIGHT := false
CATCH_DEBUG_FISH := false
CATCH_DEBUG_BAR := false
CATCH_DEBUG_TEXT := false
CATCH_DEBUG_LAST_CATCH_MIN_X := 0
CATCH_DEBUG_LAST_CATCH_MAX_X := 1

initStatusHud() {
    global STATUS_HUD_GUI, STATUS_HUD_TITLE_CTRL, STATUS_HUD_TIME_CTRL, STATUS_HUD_STATUS_CTRL, STATUS_HUD_LOG_CTRL

    if IsObject(STATUS_HUD_GUI)
        return

    guiObj := Gui("+AlwaysOnTop -Caption +ToolWindow +Border", "")
    guiObj.BackColor := "081428"
    guiObj.MarginX := 10
    guiObj.MarginY := 8
    guiObj.SetFont("s9 cB7C8FF", "Consolas")

    STATUS_HUD_TITLE_CTRL := guiObj.AddText("xm ym w180 c9FD3FF", "● STATUS HUD")
    STATUS_HUD_TIME_CTRL := guiObj.AddText("x+10 yp w90 Right c4D6B90", "00:00:00")
    guiObj.AddText("xm y+6 w280 h1 Background17365A")
    STATUS_HUD_STATUS_CTRL := guiObj.AddText("xm y+8 w280 cDCE8FF", "Idle")
    STATUS_HUD_LOG_CTRL := guiObj.AddText("xm y+8 w280 h90 c6E8CBE", "")

    guiObj.Show("NoActivate x12 y12 AutoSize")
    STATUS_HUD_GUI := guiObj
}

renderStatusHudLog() {
    global STATUS_HUD_LOG_CTRL, STATUS_HUD_LINES

    if !IsObject(STATUS_HUD_LOG_CTRL)
        return

    text := ""
    for _, line in STATUS_HUD_LINES {
        if text != ""
            text .= "`n"
        text .= line
    }
    STATUS_HUD_LOG_CTRL.Text := text
}

appendStatusHudLog(message) {
    global STATUS_HUD_LINES

    if !IsObject(STATUS_HUD_LINES)
        STATUS_HUD_LINES := []

    clean := Trim("" message)
    if clean = ""
        return

    stamp := FormatTime(A_Now, "HH:mm:ss")
    STATUS_HUD_LINES.Push(">> " stamp "  " clean)
    while STATUS_HUD_LINES.Length > 6
        STATUS_HUD_LINES.RemoveAt(1)

    renderStatusHudLog()
}

updateStatusHudClock() {
    global STATUS_HUD_TIME_CTRL
    if IsObject(STATUS_HUD_TIME_CTRL)
        STATUS_HUD_TIME_CTRL.Text := FormatTime(A_Now, "HH:mm:ss")
}

updateStatus(message) {
    global LAST_STATUS_MESSAGE, STATUS_HUD_STATUS_CTRL

    LAST_STATUS_MESSAGE := message
    logStatus(message)
    try WinSetTitle(message, "ahk_exe RobloxPlayerBeta.exe")

    initStatusHud()
    updateStatusHudClock()

    if IsObject(STATUS_HUD_STATUS_CTRL)
        STATUS_HUD_STATUS_CTRL.Text := (message = "" ? "Idle" : message)

    if message != ""
        appendStatusHudLog(message)
}


positionCatchDebugBar(catchMinX := 0, catchMaxX := 0) {
    global CATCH_DEBUG_GUI, CATCH_DEBUG_TRACK_W, CATCH_BAR

    if !IsObject(CATCH_DEBUG_GUI)
        return

    try WinGetClientPos &winX, &winY, , , "ahk_exe RobloxPlayerBeta.exe"
    catch
        return

    if catchMaxX > catchMinX {
        guiW := CATCH_DEBUG_TRACK_W + 16
        centerX := winX + Round((catchMinX + catchMaxX) / 2)
        guiX := centerX - Round(guiW / 2)
        catchTop := 520
        if IsObject(CATCH_BAR) && CATCH_BAR.HasOwnProp("y1")
            catchTop := CATCH_BAR.y1
        guiY := winY + catchTop - 86
        CATCH_DEBUG_GUI.Show("NoActivate x" guiX " y" guiY)
        return
    }

    CATCH_DEBUG_GUI.Show("NoActivate x" (winX + 100) " y" (winY + 420))
}

showCatchDebugBar() {
    global CATCH_DEBUG_GUI, CATCH_DEBUG_TRACK_W
    global CATCH_DEBUG_BOUND_LEFT, CATCH_DEBUG_BOUND_RIGHT, CATCH_DEBUG_FISH, CATCH_DEBUG_BAR, CATCH_DEBUG_TEXT

    if IsObject(CATCH_DEBUG_GUI)
        return

    guiObj := Gui("+AlwaysOnTop -Caption +ToolWindow +Border", "")
    guiObj.BackColor := "101010"
    guiObj.MarginX := 8
    guiObj.MarginY := 8
    guiObj.SetFont("s9 cCFCFCF", "Consolas")

    guiObj.AddText("xm ym c93B8FF", "DEBUG BAR")
    CATCH_DEBUG_TEXT := guiObj.AddText("x+12 yp w520 c99A8B8", "waiting...")
    guiObj.AddText("xm y+8 w" CATCH_DEBUG_TRACK_W " h1 Background2A2A2A")

    ; Track lane
    guiObj.AddText("xm y+6 w" CATCH_DEBUG_TRACK_W " h24 Background141414")
    CATCH_DEBUG_BOUND_LEFT := guiObj.AddText("x0 y0 w2 h24 BackgroundFFAA00")
    CATCH_DEBUG_BOUND_RIGHT := guiObj.AddText("x0 y0 w2 h24 BackgroundFFAA00")
    CATCH_DEBUG_FISH := guiObj.AddText("x0 y0 w2 h24 Background00FF9D")
    CATCH_DEBUG_BAR := guiObj.AddText("x0 y0 w2 h24 Background00C6FF")

    guiObj.Show("NoActivate AutoSize")
    CATCH_DEBUG_GUI := guiObj
    positionCatchDebugBar(CATCH_DEBUG_LAST_CATCH_MIN_X, CATCH_DEBUG_LAST_CATCH_MAX_X)
}

hideCatchDebugBar() {
    global CATCH_DEBUG_GUI
    if IsObject(CATCH_DEBUG_GUI)
        try CATCH_DEBUG_GUI.Destroy()
    CATCH_DEBUG_GUI := false
}

mapCatchDebugX(gameX) {
    global CATCH_DEBUG_TRACK_W, CATCH_DEBUG_MIN_X, CATCH_DEBUG_MAX_X

    span := Max(1, CATCH_DEBUG_MAX_X - CATCH_DEBUG_MIN_X)
    clamped := gameX
    if clamped < CATCH_DEBUG_MIN_X
        clamped := CATCH_DEBUG_MIN_X
    if clamped > CATCH_DEBUG_MAX_X
        clamped := CATCH_DEBUG_MAX_X

    return Round(((clamped - CATCH_DEBUG_MIN_X) / span) * (CATCH_DEBUG_TRACK_W - 1))
}

updateCatchDebugBar(catchMinX, catchMaxX, fishX, barMiddleX, leftX, rightX, note := "") {
    global CATCH_DEBUG_GUI, CATCH_DEBUG_TRACK_W, CATCH_DEBUG_MIN_X, CATCH_DEBUG_MAX_X
    global CATCH_DEBUG_BOUND_LEFT, CATCH_DEBUG_BOUND_RIGHT, CATCH_DEBUG_FISH, CATCH_DEBUG_BAR, CATCH_DEBUG_TEXT
    global CATCH_DEBUG_LAST_CATCH_MIN_X, CATCH_DEBUG_LAST_CATCH_MAX_X

    showCatchDebugBar()

    if !IsObject(CATCH_DEBUG_GUI)
        return

    CATCH_DEBUG_MIN_X := catchMinX
    CATCH_DEBUG_MAX_X := catchMaxX
    CATCH_DEBUG_LAST_CATCH_MIN_X := catchMinX
    CATCH_DEBUG_LAST_CATCH_MAX_X := catchMaxX
    positionCatchDebugBar(catchMinX, catchMaxX)

    trackLeft := 8
    trackTop := 24

    leftPx := mapCatchDebugX(leftX)
    rightPx := mapCatchDebugX(rightX)
    fishPx := mapCatchDebugX(fishX)
    barPx := mapCatchDebugX(barMiddleX)

    CATCH_DEBUG_BOUND_LEFT.Move(trackLeft + leftPx, trackTop, 2, 24)
    CATCH_DEBUG_BOUND_RIGHT.Move(trackLeft + rightPx, trackTop, 2, 24)
    CATCH_DEBUG_FISH.Move(trackLeft + fishPx, trackTop, 2, 24)
    CATCH_DEBUG_BAR.Move(trackLeft + barPx, trackTop, 2, 24)

    if IsObject(CATCH_DEBUG_TEXT)
        CATCH_DEBUG_TEXT.Text := "fish=" Round(fishX) " bar=" Round(barMiddleX) " left=" Round(leftX) " right=" Round(rightX) (note != "" ? "  " note : "")
}

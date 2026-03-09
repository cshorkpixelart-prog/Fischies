#Requires AutoHotkey v2.0

COLOR_PRESET_DIR := A_ScriptDir "\\ColorPresets"
ACTIVE_COLOR_PRESET := "default.ini"
COLOR_CONFIG_GUI := false

initColorConfig() {
    global COLOR_PRESET_DIR
    if !DirExist(COLOR_PRESET_DIR)
        DirCreate(COLOR_PRESET_DIR)

    defaultPreset := COLOR_PRESET_DIR "\\default.ini"
    if !FileExist(defaultPreset)
        writeColorPresetFile(defaultPreset, getDefaultColorConfig())
}

loadColorPresetConfig() {
    global ACTIVE_COLOR_PRESET
    initColorConfig()

    activePreset := Trim(getInfoConfigValue("ColorPreset", "default.ini"))
    if activePreset = ""
        activePreset := "default.ini"

    presetPath := getPresetPath(activePreset)
    if !FileExist(presetPath) {
        activePreset := "default.ini"
        presetPath := getPresetPath(activePreset)
        if !FileExist(presetPath)
            writeColorPresetFile(presetPath, getDefaultColorConfig())
    }

    ACTIVE_COLOR_PRESET := activePreset
    applyColorConfigFromPreset(presetPath)
    IniWrite(ACTIVE_COLOR_PRESET, A_ScriptDir "\\info.ini", "", "ColorPreset")
}

showColorConfigGui() {
    global COLOR_CONFIG_GUI, MACRO_TITLE

    initColorConfig()
    if IsObject(COLOR_CONFIG_GUI) {
        try COLOR_CONFIG_GUI.Show()
        return
    }

    guiObj := Gui("+AlwaysOnTop +ToolWindow", MACRO_TITLE " - Color Configuration")
    COLOR_CONFIG_GUI := guiObj
    setGuiDarkBase(guiObj)

    guiObj.SetFont("s10 cF0F0F0", "Segoe UI")
    guiObj.AddText("xm ym", "Preset:")
    presetList := getPresetNames()
    presetDropdown := guiObj.AddDropDownList("x+8 w180", presetList)
    activeIndex := findItemIndex(presetList, ACTIVE_COLOR_PRESET)
    presetDropdown.Choose(activeIndex = 0 ? 1 : activeIndex)

    loadButton := guiObj.AddButton("x+8 w70", "Load")
    newButton := guiObj.AddButton("x+6 w70", "New")
    saveButton := guiObj.AddButton("x+6 w70", "Save")

    guiObj.AddText("xm y+16", "Target Line Color:")
    targetEdit := guiObj.AddEdit("x+10 yp-2 w90", "")
    targetPreview := guiObj.AddText("x+8 yp+2 w70 h20 +0x4")
    targetPick := guiObj.AddButton("x+8 yp-2 w80", "Pick Color")
    guiObj.AddText("xm y+6", "Target Tolerance:")
    targetTol := guiObj.AddEdit("x+10 yp-2 w55 Number", "")

    guiObj.AddText("xm y+12", "Indicator Arrow Color:")
    arrowEdit := guiObj.AddEdit("x+10 yp-2 w90", "")
    arrowPreview := guiObj.AddText("x+8 yp+2 w70 h20 +0x4")
    arrowPick := guiObj.AddButton("x+8 yp-2 w80", "Pick Color")
    guiObj.AddText("xm y+6", "Arrow Tolerance:")
    arrowTol := guiObj.AddEdit("x+10 yp-2 w55 Number", "")

    guiObj.AddText("xm y+12", "Box Left Color:")
    leftEdit := guiObj.AddEdit("x+10 yp-2 w90", "")
    leftPreview := guiObj.AddText("x+8 yp+2 w70 h20 +0x4")
    leftPick := guiObj.AddButton("x+8 yp-2 w80", "Pick Color")

    guiObj.AddText("xm y+12", "Box Right Color:")
    rightEdit := guiObj.AddEdit("x+10 yp-2 w90", "")
    rightPreview := guiObj.AddText("x+8 yp+2 w70 h20 +0x4")
    rightPick := guiObj.AddButton("x+8 yp-2 w80", "Pick Color")
    guiObj.AddText("xm y+6", "Box Tolerance:")
    boxTol := guiObj.AddEdit("x+10 yp-2 w55 Number", "")

    applyBtn := guiObj.AddButton("xm y+16 w100", "Apply")
    closeBtn := guiObj.AddButton("x+10 w100", "Close")

    loadPresetIntoControls(getPresetPath(ACTIVE_COLOR_PRESET), targetEdit, targetPreview, targetTol, arrowEdit, arrowPreview, arrowTol, leftEdit, leftPreview, rightEdit, rightPreview, boxTol)

    targetPick.OnEvent("Click", (*) => pickColorToControl(targetEdit, targetPreview))
    arrowPick.OnEvent("Click", (*) => pickColorToControl(arrowEdit, arrowPreview))
    leftPick.OnEvent("Click", (*) => pickColorToControl(leftEdit, leftPreview))
    rightPick.OnEvent("Click", (*) => pickColorToControl(rightEdit, rightPreview))

    loadButton.OnEvent("Click", (*) => loadSelectedPreset(presetDropdown, targetEdit, targetPreview, targetTol, arrowEdit, arrowPreview, arrowTol, leftEdit, leftPreview, rightEdit, rightPreview, boxTol))
    newButton.OnEvent("Click", (*) => createColorPresetFromControls(presetDropdown, targetEdit, targetTol, arrowEdit, arrowTol, leftEdit, rightEdit, boxTol))
    saveButton.OnEvent("Click", (*) => saveCurrentPresetFromControls(presetDropdown, targetEdit, targetTol, arrowEdit, arrowTol, leftEdit, rightEdit, boxTol))
    applyBtn.OnEvent("Click", (*) => applyColorControls(targetEdit, targetTol, arrowEdit, arrowTol, leftEdit, rightEdit, boxTol))
    closeBtn.OnEvent("Click", (*) => guiObj.Destroy())
    guiObj.OnEvent("Close", (*) => onColorConfigGuiClosed())
    guiObj.OnEvent("Escape", (*) => guiObj.Destroy())

    applyGuiDarkTheme(guiObj)
    guiObj.Show("AutoSize Center")
}

onColorConfigGuiClosed() {
    global COLOR_CONFIG_GUI
    COLOR_CONFIG_GUI := false
}

loadSelectedPreset(presetDropdown, targetEdit, targetPreview, targetTol, arrowEdit, arrowPreview, arrowTol, leftEdit, leftPreview, rightEdit, rightPreview, boxTol) {
    global ACTIVE_COLOR_PRESET
    chosen := Trim(presetDropdown.Text)
    if chosen = ""
        return
    ACTIVE_COLOR_PRESET := chosen
    IniWrite(ACTIVE_COLOR_PRESET, A_ScriptDir "\\info.ini", "", "ColorPreset")
    loadPresetIntoControls(getPresetPath(chosen), targetEdit, targetPreview, targetTol, arrowEdit, arrowPreview, arrowTol, leftEdit, leftPreview, rightEdit, rightPreview, boxTol)
    applyColorConfigFromPreset(getPresetPath(chosen))
}

createColorPresetFromControls(presetDropdown, targetEdit, targetTol, arrowEdit, arrowTol, leftEdit, rightEdit, boxTol) {
    global ACTIVE_COLOR_PRESET
    result := InputBox("Enter preset name", "Create Color Preset", "w260")
    if result.Result != "OK"
        return

    name := sanitizePresetName(result.Value)
    if name = ""
        return

    ACTIVE_COLOR_PRESET := name ".ini"
    savePresetFromControls(getPresetPath(ACTIVE_COLOR_PRESET), targetEdit, targetTol, arrowEdit, arrowTol, leftEdit, rightEdit, boxTol)
    IniWrite(ACTIVE_COLOR_PRESET, A_ScriptDir "\\info.ini", "", "ColorPreset")
    presetDropdown.Delete()
    presetDropdown.Add(getPresetNames())
    idx := findItemIndex(getPresetNames(), ACTIVE_COLOR_PRESET)
    if idx > 0
        presetDropdown.Choose(idx)
}

saveCurrentPresetFromControls(presetDropdown, targetEdit, targetTol, arrowEdit, arrowTol, leftEdit, rightEdit, boxTol) {
    global ACTIVE_COLOR_PRESET
    chosen := Trim(presetDropdown.Text)
    if chosen = ""
        chosen := ACTIVE_COLOR_PRESET
    ACTIVE_COLOR_PRESET := chosen
    savePresetFromControls(getPresetPath(ACTIVE_COLOR_PRESET), targetEdit, targetTol, arrowEdit, arrowTol, leftEdit, rightEdit, boxTol)
    applyColorConfigFromPreset(getPresetPath(ACTIVE_COLOR_PRESET))
}

applyColorControls(targetEdit, targetTol, arrowEdit, arrowTol, leftEdit, rightEdit, boxTol) {
    global ACTIVE_COLOR_PRESET
    savePresetFromControls(getPresetPath(ACTIVE_COLOR_PRESET), targetEdit, targetTol, arrowEdit, arrowTol, leftEdit, rightEdit, boxTol)
    applyColorConfigFromPreset(getPresetPath(ACTIVE_COLOR_PRESET))
}

savePresetFromControls(path, targetEdit, targetTol, arrowEdit, arrowTol, leftEdit, rightEdit, boxTol) {
    cfg := Map()
    cfg["TargetLineColor"] := normalizeHexColor(targetEdit.Text, "0x434B5B")
    cfg["TargetLineTolerance"] := normalizeTolerance(targetTol.Text, 4)
    cfg["IndicatorArrowColor"] := normalizeHexColor(arrowEdit.Text, "0x787878")
    cfg["IndicatorArrowTolerance"] := normalizeTolerance(arrowTol.Text, 4)
    cfg["BoxLeftColor"] := normalizeHexColor(leftEdit.Text, "0xF1F1F1")
    cfg["BoxRightColor"] := normalizeHexColor(rightEdit.Text, "0xF1F1F1")
    cfg["BoxTolerance"] := normalizeTolerance(boxTol.Text, 24)
    writeColorPresetFile(path, cfg)
}

loadPresetIntoControls(path, targetEdit, targetPreview, targetTol, arrowEdit, arrowPreview, arrowTol, leftEdit, leftPreview, rightEdit, rightPreview, boxTol) {
    cfg := readColorPresetFile(path)
    targetEdit.Text := cfg["TargetLineColor"]
    targetTol.Text := cfg["TargetLineTolerance"]
    arrowEdit.Text := cfg["IndicatorArrowColor"]
    arrowTol.Text := cfg["IndicatorArrowTolerance"]
    leftEdit.Text := cfg["BoxLeftColor"]
    rightEdit.Text := cfg["BoxRightColor"]
    boxTol.Text := cfg["BoxTolerance"]

    setPreviewColor(targetPreview, cfg["TargetLineColor"])
    setPreviewColor(arrowPreview, cfg["IndicatorArrowColor"])
    setPreviewColor(leftPreview, cfg["BoxLeftColor"])
    setPreviewColor(rightPreview, cfg["BoxRightColor"])
}

pickColorToControl(editControl, previewControl) {
    pickerGui := createColorPickerHud()
    isFrozen := false
    frozenX := 0
    frozenY := 0
    frozenColor := 0

    oldPixelMode := A_CoordModePixel
    oldMouseMode := A_CoordModeMouse
    CoordMode("Pixel", "Screen")
    CoordMode("Mouse", "Screen")

    pickerGui.title.Text := "Color Picker"
    pickerGui.hint.Text := "Move mouse. Left click/Enter/Space = select, Right click/F = freeze, Esc = cancel"
    pickerGui.gui.Show("NoActivate x20 y20")

    try {
        Loop {
            Sleep 25

            if !isFrozen {
                MouseGetPos(&x, &y)
                color := PixelGetColor(x, y, "RGB")
                updateColorPickerHud(pickerGui, x, y, color, false)
            } else {
                updateColorPickerHud(pickerGui, frozenX, frozenY, frozenColor, true)
            }

            if GetKeyState("Escape", "P") {
                KeyWait("Escape")
                return
            }

            if GetKeyState("f", "P") || GetKeyState("RButton", "P") {
                if isFrozen {
                    isFrozen := false
                } else {
                    MouseGetPos(&frozenX, &frozenY)
                    frozenColor := PixelGetColor(frozenX, frozenY, "RGB")
                    isFrozen := true
                }
                if GetKeyState("f", "P")
                    KeyWait("f")
                if GetKeyState("RButton", "P")
                    KeyWait("RButton")
                continue
            }

            if GetKeyState("LButton", "P") || GetKeyState("Space", "P") || GetKeyState("Enter", "P") {
                if isFrozen {
                    color := frozenColor
                } else {
                    MouseGetPos(&x, &y)
                    color := PixelGetColor(x, y, "RGB")
                }
                hex := Format("0x{:06X}", color & 0xFFFFFF)
                editControl.Text := hex
                setPreviewColor(previewControl, hex)

                if GetKeyState("LButton", "P")
                    KeyWait("LButton")
                if GetKeyState("Space", "P")
                    KeyWait("Space")
                if GetKeyState("Enter", "P")
                    KeyWait("Enter")
                return
            }
        }
    } finally {
        try pickerGui.gui.Destroy()
        CoordMode("Pixel", oldPixelMode)
        CoordMode("Mouse", oldMouseMode)
    }
}

createColorPickerHud() {
    guiObj := Gui("+AlwaysOnTop -Caption +ToolWindow +Border", "")
    setGuiDarkBase(guiObj)
    guiObj.SetFont("s9 cEAEAEA", "Segoe UI")

    title := guiObj.AddText("xm ym w360", "Color Picker")
    hint := guiObj.AddText("xm y+2 w360", "")
    coords := guiObj.AddText("xm y+8 w220", "X: 0  Y: 0")
    hexText := guiObj.AddEdit("x+8 yp-2 w130 ReadOnly", "0x000000")
    preview := guiObj.AddText("xm y+8 w120 h40 +0x4", "")
    state := guiObj.AddText("x+10 yp+10 w220", "LIVE")

    applyGuiDarkTheme(guiObj)
    return {gui: guiObj, title: title, hint: hint, coords: coords, hexText: hexText, preview: preview, state: state}
}

updateColorPickerHud(hud, x, y, color, isFrozen) {
    if !IsObject(hud)
        return

    hex := Format("0x{:06X}", color & 0xFFFFFF)
    hud.coords.Text := "X: " x "  Y: " y
    hud.hexText.Text := hex
    hud.state.Text := isFrozen ? "FROZEN" : "LIVE"
    setPreviewColor(hud.preview, hex)
}

applyColorConfigFromPreset(path) {
    cfg := readColorPresetFile(path)
    applyCatchColorConfig(cfg)
}

applyCatchColorConfig(cfg) {
    global CATCH_ARROW_COLOR, CATCH_ARROW_TOLERANCE, CALIBRATION_FISH_COLOR, CALIBRATION_FISH_TOLERANCE
    global HEARTBEAT_MARKER_COLOR, HEARTBEAT_MARKER_TOLERANCE, CATCH_SCAN_COLOR_SET, CATCH_SCAN_COLOR_VARIATION, CATCH_SCAN_DEBUG_ENABLED

    CATCH_ARROW_COLOR := cfg["IndicatorArrowColor"]
    CATCH_ARROW_TOLERANCE := cfg["IndicatorArrowTolerance"]
    CALIBRATION_FISH_COLOR := cfg["TargetLineColor"]
    CALIBRATION_FISH_TOLERANCE := cfg["TargetLineTolerance"]

    ; Use the left box color as the heartbeat marker in catch bar mode.
    HEARTBEAT_MARKER_COLOR := cfg["BoxLeftColor"]
    HEARTBEAT_MARKER_TOLERANCE := cfg["BoxTolerance"]

    CATCH_SCAN_COLOR_SET := [
        cfg["TargetLineColor"],
        cfg["IndicatorArrowColor"],
        cfg["BoxLeftColor"],
        cfg["BoxRightColor"]
    ]
    CATCH_SCAN_COLOR_VARIATION := Max(cfg["TargetLineTolerance"], cfg["IndicatorArrowTolerance"], cfg["BoxTolerance"])
    CATCH_SCAN_DEBUG_ENABLED := StrLower(Trim(getInfoConfigValue("CatchScanDebug", "true"))) = "true"
}

readColorPresetFile(path) {
    cfg := getDefaultColorConfig()
    if !FileExist(path)
        return cfg

    cfg["TargetLineColor"] := normalizeHexColor(IniRead(path, "Colors", "TargetLineColor", cfg["TargetLineColor"]), cfg["TargetLineColor"])
    cfg["TargetLineTolerance"] := normalizeTolerance(IniRead(path, "Colors", "TargetLineTolerance", cfg["TargetLineTolerance"]), cfg["TargetLineTolerance"])
    cfg["IndicatorArrowColor"] := normalizeHexColor(IniRead(path, "Colors", "IndicatorArrowColor", cfg["IndicatorArrowColor"]), cfg["IndicatorArrowColor"])
    cfg["IndicatorArrowTolerance"] := normalizeTolerance(IniRead(path, "Colors", "IndicatorArrowTolerance", cfg["IndicatorArrowTolerance"]), cfg["IndicatorArrowTolerance"])
    cfg["BoxLeftColor"] := normalizeHexColor(IniRead(path, "Colors", "BoxLeftColor", cfg["BoxLeftColor"]), cfg["BoxLeftColor"])
    cfg["BoxRightColor"] := normalizeHexColor(IniRead(path, "Colors", "BoxRightColor", cfg["BoxRightColor"]), cfg["BoxRightColor"])
    cfg["BoxTolerance"] := normalizeTolerance(IniRead(path, "Colors", "BoxTolerance", cfg["BoxTolerance"]), cfg["BoxTolerance"])
    return cfg
}

writeColorPresetFile(path, cfg) {
    IniWrite(cfg["TargetLineColor"], path, "Colors", "TargetLineColor")
    IniWrite(cfg["TargetLineTolerance"], path, "Colors", "TargetLineTolerance")
    IniWrite(cfg["IndicatorArrowColor"], path, "Colors", "IndicatorArrowColor")
    IniWrite(cfg["IndicatorArrowTolerance"], path, "Colors", "IndicatorArrowTolerance")
    IniWrite(cfg["BoxLeftColor"], path, "Colors", "BoxLeftColor")
    IniWrite(cfg["BoxRightColor"], path, "Colors", "BoxRightColor")
    IniWrite(cfg["BoxTolerance"], path, "Colors", "BoxTolerance")
}

getDefaultColorConfig() {
    cfg := Map()
    cfg["TargetLineColor"] := "0x434B5B"
    cfg["TargetLineTolerance"] := 4
    cfg["IndicatorArrowColor"] := "0x787878"
    cfg["IndicatorArrowTolerance"] := 4
    cfg["BoxLeftColor"] := "0xF1F1F1"
    cfg["BoxRightColor"] := "0xF1F1F1"
    cfg["BoxTolerance"] := 24
    return cfg
}

getPresetNames() {
    global COLOR_PRESET_DIR
    names := []
    Loop Files, COLOR_PRESET_DIR "\\*.ini" {
        names.Push(A_LoopFileName)
    }
    if names.Length = 0
        names.Push("default.ini")
    return names
}

getPresetPath(fileName) {
    global COLOR_PRESET_DIR
    return COLOR_PRESET_DIR "\\" fileName
}

sanitizePresetName(name) {
    value := RegExReplace(Trim(name), "[^a-zA-Z0-9_\- ]", "")
    value := Trim(value)
    return value
}

normalizeHexColor(value, fallback) {
    v := Trim("" value)
    if v = ""
        return fallback
    v := StrUpper(v)
    if SubStr(v, 1, 2) != "0X"
        v := "0x" RegExReplace(v, "[^0-9A-F]")
    if !RegExMatch(v, "i)^0x[0-9a-f]{6}$")
        return fallback
    return "0x" SubStr(v, 3)
}

normalizeTolerance(value, fallback) {
    n := Round(parseOptionalNumber(value, fallback))
    if n < 0
        n := 0
    if n > 255
        n := 255
    return n
}

setPreviewColor(ctrl, hexColor) {
    if !IsObject(ctrl)
        return
    colorValue := SubStr(hexColor, 3)
    ctrl.Opt("Background" colorValue)
}

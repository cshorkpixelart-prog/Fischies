#Requires AutoHotkey v2.0

ROD_DATA := Map()
ROD_DATA_LOADED := false
ENCHANT_DATA := Map()
ENCHANT_DATA_LOADED := false

SELECTED_ROD_NAME := ""
SELECTED_ENCHANT_NAME := ""
SELECTED_SECONDARY_ENCHANT_NAME := ""
SELECTED_ROD_STATS := false
SELECTED_ROD_BASE_STATS := false

SETUP_GUI := false
MACRO_SETUP_COMPLETE := false
FEEDBACK_GUI := false
TUTORIAL_GUI := false

ROD_SERVER_URL := ""
ROD_SERVER_TIMEOUT_MS := 2500
LAST_ROD_SERVER_SYNC := ""
SERVER_CATALOG_CACHE := false
SERVER_CATALOG_ATTEMPTED := false
LAST_CATCH_LEARNING_STATUS := ""
LAST_CATCH_LEARNING_AT := 0

openSetupGuiAtRun() {
    global MACRO_SETUP_COMPLETE
    loadRodData()
    loadEnchantData()
    loadServerConfig()
    MACRO_SETUP_COMPLETE := false
    showRodSelectionGui()
}

isMacroSetupComplete() {
    global MACRO_SETUP_COMPLETE
    return MACRO_SETUP_COMPLETE
}

loadServerConfig() {
    global ROD_SERVER_URL, ROD_SERVER_TIMEOUT_MS
    if ROD_SERVER_URL != ""
        return
    serverUrl := getInfoConfigValue("ServerUrl", "http://127.0.0.1:3030")
    ROD_SERVER_URL := normalizeServerUrl(serverUrl)
    timeoutMs := parseOptionalNumber(getInfoConfigValue("ServerTimeoutMs", "12000"), 12000)
    timeoutMs := Round(timeoutMs)
    if timeoutMs < 1500
        timeoutMs := 1500
    if timeoutMs > 30000
        timeoutMs := 30000
    ROD_SERVER_TIMEOUT_MS := timeoutMs
}

getServerBaseUrl() {
    global ROD_SERVER_URL
    if ROD_SERVER_URL = ""
        loadServerConfig()
    return ROD_SERVER_URL
}

loadRodData() {
    global ROD_DATA, ROD_DATA_LOADED
    if ROD_DATA_LOADED
        return

    catalog := fetchServerCatalogData()
    if IsObject(catalog) && catalog.HasOwnProp("rods") && catalog.rods.Count > 0 {
        ROD_DATA := Map()
        for rodName, stats in catalog.rods
            mergeRodStatsEntry(ROD_DATA, rodName, stats)
    } else {
        ; Offline fallback when server is unavailable.
        ROD_DATA := getFallbackRodData()
        mergeRodDataFromLocalCatalog(ROD_DATA)
    }

    ROD_DATA_LOADED := true
}

loadEnchantData() {
    global ENCHANT_DATA, ENCHANT_DATA_LOADED
    if ENCHANT_DATA_LOADED
        return

    catalog := fetchServerCatalogData()
    if IsObject(catalog) && catalog.HasOwnProp("enchants") && catalog.enchants.Count > 0 {
        ENCHANT_DATA := Map()
        for enchantName, stats in catalog.enchants
            ENCHANT_DATA[enchantName] := stats
    } else {
        ENCHANT_DATA := getFallbackEnchantData()
    }

    ENCHANT_DATA_LOADED := true
}

showRodSelectionGui() {
    global MACRO_TITLE, SELECTED_ROD_NAME, SELECTED_ENCHANT_NAME, SELECTED_SECONDARY_ENCHANT_NAME, SETUP_GUI, MACRO_SETUP_COMPLETE

    loadRodData()
    loadEnchantData()

    names := getRodNames()
    if names.Length = 0
        return false

    if IsObject(SETUP_GUI) {
        try SETUP_GUI.Show()
        return true
    }

    selectionItems := buildRodSelectionItems(names)
    if selectionItems.labels.Length = 0
        return false

    selectedLabel := getRodLabelForName(selectionItems, SELECTED_ROD_NAME)
    selectedIndex := findItemIndex(selectionItems.labels, selectedLabel)
    if selectedIndex = 0
        selectedIndex := findItemIndex(selectionItems.labels, getRodLabelForName(selectionItems, "Flimsy Rod"))
    if selectedIndex = 0
        selectedIndex := 1

    primaryEnchantNames := getEnchantNames("primary")
    if primaryEnchantNames.Length = 0
        primaryEnchantNames := getEnchantNames()
    primaryEnchantNames.InsertAt(1, "(None)")
    selectedEnchantIndex := findItemIndex(primaryEnchantNames, SELECTED_ENCHANT_NAME = "" ? "(None)" : SELECTED_ENCHANT_NAME)
    if selectedEnchantIndex = 0
        selectedEnchantIndex := 1

    secondaryEnchantNames := getEnchantNames("secondary")
    secondaryEnchantNames.InsertAt(1, "(None)")
    selectedSecondaryEnchantIndex := findItemIndex(secondaryEnchantNames, SELECTED_SECONDARY_ENCHANT_NAME = "" ? "(None)" : SELECTED_SECONDARY_ENCHANT_NAME)
    if selectedSecondaryEnchantIndex = 0
        selectedSecondaryEnchantIndex := 1

    FischGui := Gui("+AlwaysOnTop +ToolWindow", MACRO_TITLE " - Rod Setup")
    SETUP_GUI := FischGui
    setGuiDarkBase(FischGui)

    FischGui.SetFont("s10 cBDBDBD", "Segoe UI")
    FischGui.AddText("xm ym", "1) Choose rod + enchants")
    FischGui.AddText("xm y+2", "2) Review effective stats")
    FischGui.AddText("xm y+2", "3) Click Finish Setup and press F1")

    FischGui.SetFont("s10 cF0F0F0", "Segoe UI")
    FischGui.AddText("xm y+10", "Rod:")
    rodCombo := FischGui.AddComboBox("xm w380 c000000", selectionItems.labels)
    rodCombo.Choose(selectedIndex)

    FischGui.AddText("xm y+8", "Primary Enchant:")
    enchantDropdown := FischGui.AddDropDownList("xm w380 c000000 Choose" selectedEnchantIndex, primaryEnchantNames)

    FischGui.AddText("xm y+8", "Secondary Enchant:")
    secondaryEnchantDropdown := FischGui.AddDropDownList("xm w380 c000000 Choose" selectedSecondaryEnchantIndex, secondaryEnchantNames)

    statsText := FischGui.AddText("xm w470 r15", "")

    tutorialButton := FischGui.AddButton("xm w120", "Tutorial")
    colorConfigButton := FischGui.AddButton("x+10 w120", "Color Config")
    useButton := FischGui.AddButton("x+10 w120 Default", "Finish Setup")
    cancelButton := FischGui.AddButton("x+10 w90", "Close")

    refreshSetupPreview(statsText, tutorialButton, selectionItems, rodCombo, enchantDropdown, secondaryEnchantDropdown)
    rodCombo.OnEvent("Change", (*) => refreshSetupPreview(statsText, tutorialButton, selectionItems, rodCombo, enchantDropdown, secondaryEnchantDropdown))
    enchantDropdown.OnEvent("Change", (*) => refreshSetupPreview(statsText, tutorialButton, selectionItems, rodCombo, enchantDropdown, secondaryEnchantDropdown))
    secondaryEnchantDropdown.OnEvent("Change", (*) => refreshSetupPreview(statsText, tutorialButton, selectionItems, rodCombo, enchantDropdown, secondaryEnchantDropdown))

    tutorialButton.OnEvent("Click", (*) => showRodTutorialVideo(resolveRodNameFromSelection(rodCombo.Text, selectionItems)))
    colorConfigButton.OnEvent("Click", (*) => showColorConfigGui())
    useButton.OnEvent("Click", (*) => finishSetupSelection(resolveRodNameFromSelection(rodCombo.Text, selectionItems), enchantDropdown.Text, secondaryEnchantDropdown.Text, FischGui))
    cancelButton.OnEvent("Click", (*) => FischGui.Destroy())
    FischGui.OnEvent("Close", (*) => onSetupGuiClosed())
    FischGui.OnEvent("Escape", (*) => FischGui.Destroy())

    applyGuiDarkTheme(FischGui)
    FischGui.Show("AutoSize Center")

    if !MACRO_SETUP_COMPLETE
        updateStatus("Finish setup in GUI, then press F1.")
    return true
}

finishSetupSelection(rodName, enchantName, secondaryEnchantName, FischGui) {
    global MACRO_TITLE, SELECTED_ROD_STATS, SETUP_GUI, MACRO_SETUP_COMPLETE

    if rodName = "" || !setSelectedRod(rodName, enchantName, secondaryEnchantName) {
        MsgBox "Select a valid rod before finishing setup.", MACRO_TITLE, 48
        return false
    }

    if !SELECTED_ROD_STATS {
        MsgBox "Rod stats are unavailable.", MACRO_TITLE, 48
        return false
    }

    configureCatchingForRod(SELECTED_ROD_STATS)
    syncSelectedRodFromServer(false)
    MACRO_SETUP_COMPLETE := true
    SETUP_GUI := false
    updateStatus("Setup complete. Press F1 to start the macro.")
    FischGui.Destroy()
    return true
}

onSetupGuiClosed() {
    global SETUP_GUI, MACRO_SETUP_COMPLETE
    SETUP_GUI := false
    closeTutorialGui()
    if !MACRO_SETUP_COMPLETE
        updateStatus("Finish setup in GUI, then press F1.")
}

refreshSetupPreview(statsControl, tutorialButton, selectionItems, rodCombo, enchantDropdown, secondaryEnchantDropdown) {
    rodName := resolveRodNameFromSelection(rodCombo.Text, selectionItems)
    statsControl.Text := formatRodStatsForDisplay(rodName, enchantDropdown.Text, secondaryEnchantDropdown.Text)
    updateTutorialButtonState(tutorialButton, rodName)
}

updateTutorialButtonState(tutorialButton, rodName) {
    if !IsObject(tutorialButton)
        return
    tutorialButton.Enabled := rodHasTutorial(rodName)
}

rodHasTutorial(rodName) {
    return getRodTutorialUrl(rodName) != ""
}

getRodTutorialUrl(rodName) {
    global ROD_DATA

    canonicalName := canonicalizeRodName(rodName)
    if canonicalName = "" || !ROD_DATA.Has(canonicalName)
        return ""

    rodStats := ROD_DATA[canonicalName]
    if !rodStats.HasOwnProp("tutorialUrl")
        return ""
    return Trim("" rodStats.tutorialUrl)
}

showRodTutorialVideo(rodName) {
    global MACRO_TITLE, TUTORIAL_GUI

    canonicalName := canonicalizeRodName(rodName)
    tutorialUrl := getRodTutorialUrl(canonicalName)
    if tutorialUrl = "" {
        MsgBox "No tutorial URL is configured for this rod yet.", MACRO_TITLE, 48
        return false
    }

    closeTutorialGui()

    tutorialGui := Gui("+AlwaysOnTop +ToolWindow", MACRO_TITLE " - " canonicalName " Tutorial")
    TUTORIAL_GUI := tutorialGui
    setGuiDarkBase(tutorialGui)

    tutorialGui.AddText("xm ym", "Video tutorial for " canonicalName)
    webCtrl := tutorialGui.Add("ActiveX", "xm w520 h300", "Shell.Explorer")
    webView := webCtrl.Value
    closeButton := tutorialGui.AddButton("xm w120", "Close")
    closeButton.OnEvent("Click", (*) => closeTutorialGui())
    tutorialGui.OnEvent("Close", (*) => closeTutorialGui())
    tutorialGui.OnEvent("Escape", (*) => closeTutorialGui())

    applyGuiDarkTheme(tutorialGui)
    tutorialGui.Show("AutoSize Center")

    playbackUrl := resolveTutorialPlaybackUrl(tutorialUrl)
    embedUrl := buildTutorialEmbedUrl(playbackUrl)
    try webView.Navigate(embedUrl)
    catch {
        closeTutorialGui()
        Run playbackUrl
        return true
    }

    return true
}

closeTutorialGui() {
    global TUTORIAL_GUI
    if IsObject(TUTORIAL_GUI) {
        guiToClose := TUTORIAL_GUI
        TUTORIAL_GUI := false
        try guiToClose.Destroy()
        return
    }
    TUTORIAL_GUI := false
}

buildTutorialEmbedUrl(url) {
    cleanUrl := Trim("" url)
    if cleanUrl = ""
        return ""

    youtubeId := extractYouTubeId(cleanUrl)
    if youtubeId != ""
        return "https://www.youtube.com/embed/" youtubeId "?autoplay=1"

    return cleanUrl
}

resolveTutorialPlaybackUrl(url) {
    cleanUrl := Trim("" url)
    if cleanUrl = ""
        return ""

    if RegExMatch(cleanUrl, "i)^[a-z][a-z0-9+\-.]*://")
        return cleanUrl

    baseUrl := getServerBaseUrl()
    if baseUrl = ""
        return cleanUrl

    if SubStr(cleanUrl, 1, 1) = "/"
        return baseUrl cleanUrl

    return baseUrl "/" cleanUrl
}

extractYouTubeId(url) {
    cleanUrl := Trim("" url)
    if cleanUrl = ""
        return ""

    lower := StrLower(cleanUrl)
    if InStr(lower, "youtu.be/") {
        startPos := InStr(lower, "youtu.be/") + StrLen("youtu.be/")
        candidate := SubStr(cleanUrl, startPos)
        return RegExReplace(candidate, "[\?#].*$", "")
    }

    if InStr(lower, "youtube.com/watch") {
        if RegExMatch(cleanUrl, "[\?&]v=([A-Za-z0-9_-]{6,})", &watchMatch)
            return watchMatch[1]
    }

    if InStr(lower, "youtube.com/embed/") {
        startPos := InStr(lower, "youtube.com/embed/") + StrLen("youtube.com/embed/")
        candidate := SubStr(cleanUrl, startPos)
        return RegExReplace(candidate, "[\?#].*$", "")
    }

    return ""
}

setGuiDarkBase(guiObj) {
    guiObj.MarginX := 12
    guiObj.MarginY := 10
    guiObj.BackColor := "1E1E1E"
    guiObj.SetFont("s10 cF0F0F0", "Segoe UI")
}

applyGuiDarkTheme(guiObj) {
    static darkModePrepared := false

    if !darkModePrepared {
        darkModePrepared := true
        try DllCall("uxtheme\#135", "int", 1, "int")
        try DllCall("uxtheme\#136")
    }

    enabled := 1
    try DllCall("dwmapi\DwmSetWindowAttribute", "ptr", guiObj.Hwnd, "int", 20, "int*", enabled, "int", 4)
    catch {
        try DllCall("dwmapi\DwmSetWindowAttribute", "ptr", guiObj.Hwnd, "int", 19, "int*", enabled, "int", 4)
    }

    for ctrl in guiObj
        try DllCall("uxtheme\SetWindowTheme", "ptr", ctrl.Hwnd, "str", "DarkMode_Explorer", "ptr", 0)
}

syncSelectedRodFromServer(showErrorMessage := true) {
    global MACRO_TITLE, SELECTED_ROD_NAME, SELECTED_ENCHANT_NAME, SELECTED_SECONDARY_ENCHANT_NAME, SELECTED_ROD_STATS, SELECTED_ROD_BASE_STATS, LAST_ROD_SERVER_SYNC

    if SELECTED_ROD_NAME = ""
        return false

    if !IsObject(SELECTED_ROD_BASE_STATS) {
        if IsObject(SELECTED_ROD_STATS)
            SELECTED_ROD_BASE_STATS := cloneRodStats(SELECTED_ROD_STATS)
        else
            return false
    }

    statusCode := 0
    response := requestServerText(
        "GET",
        "/api/client/rod-tuning?name=" uriEncode(SELECTED_ROD_NAME),
        "",
        "",
        &statusCode
    )

    if statusCode != 200 || response = "" {
        logErrorCode("SERVER_SYNC_FAILED", "rod=" SELECTED_ROD_NAME " status=" statusCode ".", "WARN")
        if showErrorMessage
            MsgBox "Could not sync rod data from the custom server.`nUsing local rod settings.", MACRO_TITLE, 48
        return false
    }

    data := parseKeyValueBlock(response)
    if !data.Has("status") || data["status"] != "ok" {
        logErrorCode("SERVER_SYNC_INVALID_RESPONSE", "rod=" SELECTED_ROD_NAME " statusKey=" (data.Has("status") ? data["status"] : "missing") ".", "WARN")
        if showErrorMessage
            MsgBox "Server response was invalid for rod sync.`nUsing local rod settings.", MACRO_TITLE, 48
        return false
    }

    applyServerRodData(SELECTED_ROD_BASE_STATS, data)
    SELECTED_ROD_STATS := buildEffectiveRodStatsFromBase(SELECTED_ROD_BASE_STATS, SELECTED_ENCHANT_NAME, SELECTED_SECONDARY_ENCHANT_NAME)
    configureCatchingForRod(SELECTED_ROD_STATS)

    if data.Has("updatedAt")
        LAST_ROD_SERVER_SYNC := data["updatedAt"]
    else
        LAST_ROD_SERVER_SYNC := A_Now

    return true
}

applyServerRodData(rodStats, data) {
    if !IsObject(rodStats)
        return

    if data.Has("lure")
        rodStats.lure := parseOptionalNumber(data["lure"], rodStats.lure)
    if data.Has("luck")
        rodStats.luck := parseOptionalNumber(data["luck"], rodStats.luck)
    if data.Has("control")
        rodStats.control := parseOptionalNumber(data["control"], rodStats.control)
    if data.Has("resilience")
        rodStats.resilience := parseOptionalNumber(data["resilience"], rodStats.resilience)
    if data.Has("maxKg") {
        lowerMaxKg := StrLower(data["maxKg"])
        rodStats.maxKg := lowerMaxKg = "inf" ? "inf" : parseOptionalNumber(data["maxKg"], rodStats.maxKg)
    }
    if data.Has("passiveInfo")
        rodStats.passiveInfo := data["passiveInfo"]
    if data.Has("tutorialUrl")
        rodStats.tutorialUrl := data["tutorialUrl"]

    if !rodStats.HasOwnProp("catching") || !IsObject(rodStats.catching)
        rodStats.catching := {}

    applyCatchingField(rodStats.catching, "centerRatio", data)
    applyCatchingField(rodStats.catching, "lookaheadMs", data)
    applyCatchingField(rodStats.catching, "brakeSpeed", data)
    applyCatchingField(rodStats.catching, "deadzonePx", data)
    applyCatchingField(rodStats.catching, "fishVelocitySmoothing", data)
    applyCatchingField(rodStats.catching, "barVelocitySmoothing", data)
}

applyCatchingField(catchingData, fieldName, data) {
    if data.Has(fieldName)
        catchingData.%fieldName% := parseOptionalNumber(data[fieldName], "")
}

openFeedbackGui() {
    global MACRO_TITLE, FEEDBACK_GUI

    if IsObject(FEEDBACK_GUI) {
        try FEEDBACK_GUI.Show()
        return
    }

    feedbackTypes := ["(Optional)", "Rod Problem", "Custom Input", "Bug", "Suggestion", "Other"]

    Feedbackgui := Gui("+AlwaysOnTop +ToolWindow", MACRO_TITLE " - Feedback")
    FEEDBACK_GUI := Feedbackgui
    setGuiDarkBase(Feedbackgui)

    Feedbackgui.AddText("xm ym", "Category (optional):")
    typeDropdown := Feedbackgui.AddDropDownList("xm w250 Choose1 cF0F0F0", feedbackTypes)
    Feedbackgui.AddText("xm y+8", "Describe your feedback or issue:")
    descriptionEdit := Feedbackgui.AddEdit("xm w430 r8 cF0F0F0 Background2A2A2A")
    statusText := Feedbackgui.AddText("xm w430 cA0A0A0", "")

    sendButton := Feedbackgui.AddButton("xm w120 Default", "Send Feedback")
    closeButton := Feedbackgui.AddButton("x+10 w120", "Close")

    sendButton.OnEvent("Click", (*) => submitFeedbackFromGui(typeDropdown.Text, descriptionEdit.Text, statusText, Feedbackgui))
    closeButton.OnEvent("Click", (*) => Feedbackgui.Destroy())
    Feedbackgui.OnEvent("Close", (*) => onFeedbackGuiClosed())
    Feedbackgui.OnEvent("Escape", (*) => Feedbackgui.Destroy())

    applyGuiDarkTheme(Feedbackgui)
    Feedbackgui.Show("AutoSize Center")
}

submitFeedbackFromGui(feedbackType, description, statusTextControl, Feedbackgui) {
    global MACRO_TITLE

    message := Trim(description)
    if message = "" {
        statusTextControl.Text := "Enter a description before sending."
        return false
    }

    if sendFeedbackToServer(feedbackType, message) {
        statusTextControl.Text := "Feedback sent."
        Sleep 300
        Feedbackgui.Destroy()
        return true
    }

    statusTextControl.Text := "Server unreachable. Saved locally to feedback-local.log."
    logErrorCode("FEEDBACK_SERVER_UNREACHABLE", "feedbackType=" feedbackType ".", "WARN")
    MsgBox "Could not reach the custom server.`nYour feedback was saved locally.", MACRO_TITLE, 48
    return false
}

onFeedbackGuiClosed() {
    global FEEDBACK_GUI
    FEEDBACK_GUI := false
}

sendFeedbackToServer(feedbackType, description) {
    global SELECTED_ROD_NAME, SELECTED_ENCHANT_NAME, SELECTED_SECONDARY_ENCHANT_NAME

    cleanType := feedbackType = "(Optional)" ? "" : feedbackType
    payload := "type=" uriEncode(cleanType)
    payload .= "&description=" uriEncode(description)
    payload .= "&rodName=" uriEncode(SELECTED_ROD_NAME)
    payload .= "&enchantName=" uriEncode(SELECTED_ENCHANT_NAME)
    payload .= "&secondaryEnchantName=" uriEncode(SELECTED_SECONDARY_ENCHANT_NAME)
    payload .= "&clientTitle=" uriEncode(getInfoConfigValue("Title", "Fisch"))
    payload .= "&clientVersion=" uriEncode(getInfoConfigValue("Version", "0.0"))

    statusCode := 0
    response := requestServerText(
        "POST",
        "/api/client/feedback",
        payload,
        "application/x-www-form-urlencoded; charset=UTF-8",
        &statusCode
    )

    if statusCode >= 200 && statusCode < 300
        return true

    appendFeedbackFallback(cleanType, description)
    return false
}

appendFeedbackFallback(feedbackType, description) {
    global SELECTED_ROD_NAME, SELECTED_ENCHANT_NAME, SELECTED_SECONDARY_ENCHANT_NAME

    logPath := A_ScriptDir "\feedback-local.log"
    line := Format(
        "{1}|type={2}|rod={3}|enchant={4}|secondaryEnchant={5}|message={6}`n",
        A_Now,
        feedbackType = "" ? "unspecified" : feedbackType,
        SELECTED_ROD_NAME = "" ? "unknown" : SELECTED_ROD_NAME,
        SELECTED_ENCHANT_NAME = "" ? "none" : SELECTED_ENCHANT_NAME,
        SELECTED_SECONDARY_ENCHANT_NAME = "" ? "none" : SELECTED_SECONDARY_ENCHANT_NAME,
        RegExReplace(description, "\r?\n", " ")
    )
    try FileAppend(line, logPath, "UTF-8")
}

processCatchLearningCycle() {
    global SELECTED_ROD_NAME, SELECTED_ROD_BASE_STATS, SELECTED_ROD_STATS, LAST_CATCH_LEARNING_STATUS, LAST_CATCH_LEARNING_AT

    if SELECTED_ROD_NAME = "" || !IsObject(SELECTED_ROD_BASE_STATS) || !IsObject(SELECTED_ROD_STATS)
        return false

    metrics := getLastCatchLearningMetrics()
    if !IsObject(metrics)
        return false

    if !metrics.HasOwnProp("popupKnown") || !metrics.popupKnown {
        maybeReportLearningStatus("Catch learning: popup detector not configured; skipping sample upload.")
        return false
    }

    success := metrics.outcome = "success"
    if !success
        applyLocalFailureAdjustment()

    payload := buildCatchLearningPayload(metrics, success)
    if payload = ""
        return false

    statusCode := 0
    response := requestServerText(
        "POST",
        "/api/client/catch-learning",
        payload,
        "application/x-www-form-urlencoded; charset=UTF-8",
        &statusCode
    )

    if statusCode >= 200 && statusCode < 300 {
        parsed := parseKeyValueBlock(response)
        if parsed.Has("status") && parsed["status"] = "ok"
            syncSelectedRodFromServer(false)
        maybeReportLearningStatus("Catch learning synced (" (success ? "success" : "failure") ").")
        return true
    }

    maybeReportLearningStatus("Catch learning: server unreachable; kept local tuning.")
    return false
}

buildCatchLearningPayload(metrics, success) {
    global SELECTED_ROD_NAME, SELECTED_ROD_BASE_STATS
    global CATCHING_CENTER_RATIO, CATCHING_LOOKAHEAD_MS, CATCHING_BRAKE_SPEED, CATCHING_DEADZONE_PX, CATCHING_FISH_VELOCITY_SMOOTHING, CATCHING_BAR_VELOCITY_SMOOTHING
    if !IsObject(metrics) || SELECTED_ROD_NAME = ""
        return ""

    catching := {}
    if SELECTED_ROD_BASE_STATS.HasOwnProp("catching") && IsObject(SELECTED_ROD_BASE_STATS.catching)
        catching := SELECTED_ROD_BASE_STATS.catching

    payload := "rodName=" uriEncode(SELECTED_ROD_NAME)
    payload .= "&result=" uriEncode(success ? "success" : "failure")
    payload .= "&popupDetected=" uriEncode(metrics.popupDetected ? "true" : "false")
    payload .= "&frames=" uriEncode(metrics.frames)
    payload .= "&fishDetectedFrames=" uriEncode(metrics.fishDetectedFrames)
    payload .= "&multicolorFrames=" uriEncode(metrics.multicolorBarFrames)
    payload .= "&whiteBarFrames=" uriEncode(metrics.whiteBarFrames)
    payload .= "&avgAbsErrorPx=" uriEncode(metrics.avgAbsErrorPx)
    payload .= "&maxAbsErrorPx=" uriEncode(metrics.maxAbsErrorPx)
    payload .= "&durationMs=" uriEncode(metrics.durationMs)
    payload .= "&centerRatio=" uriEncode(getCatchingValue(catching, "centerRatio", CATCHING_CENTER_RATIO))
    payload .= "&lookaheadMs=" uriEncode(getCatchingValue(catching, "lookaheadMs", CATCHING_LOOKAHEAD_MS))
    payload .= "&brakeSpeed=" uriEncode(getCatchingValue(catching, "brakeSpeed", CATCHING_BRAKE_SPEED))
    payload .= "&deadzonePx=" uriEncode(getCatchingValue(catching, "deadzonePx", CATCHING_DEADZONE_PX))
    payload .= "&fishVelocitySmoothing=" uriEncode(getCatchingValue(catching, "fishVelocitySmoothing", CATCHING_FISH_VELOCITY_SMOOTHING))
    payload .= "&barVelocitySmoothing=" uriEncode(getCatchingValue(catching, "barVelocitySmoothing", CATCHING_BAR_VELOCITY_SMOOTHING))
    payload .= "&clientTitle=" uriEncode(getInfoConfigValue("Title", "Fisch"))
    payload .= "&clientVersion=" uriEncode(getInfoConfigValue("Version", "0.0"))
    payload .= "&clientTimestamp=" uriEncode(A_NowUTC)
    return payload
}

getCatchingValue(catching, fieldName, fallbackValue) {
    if IsObject(catching) && catching.HasOwnProp(fieldName) && catching.%fieldName% != ""
        return catching.%fieldName%
    return fallbackValue
}

applyLocalFailureAdjustment() {
    global SELECTED_ROD_BASE_STATS, SELECTED_ROD_STATS, SELECTED_ENCHANT_NAME, SELECTED_SECONDARY_ENCHANT_NAME
    global CATCHING_CENTER_RATIO, CATCHING_LOOKAHEAD_MS, CATCHING_BRAKE_SPEED, CATCHING_DEADZONE_PX

    if !SELECTED_ROD_BASE_STATS.HasOwnProp("catching") || !IsObject(SELECTED_ROD_BASE_STATS.catching)
        SELECTED_ROD_BASE_STATS.catching := {}
    catching := SELECTED_ROD_BASE_STATS.catching

    center := parseOptionalNumber(catching.HasOwnProp("centerRatio") ? catching.centerRatio : "", CATCHING_CENTER_RATIO)
    lookahead := parseOptionalNumber(catching.HasOwnProp("lookaheadMs") ? catching.lookaheadMs : "", CATCHING_LOOKAHEAD_MS)
    deadzone := parseOptionalNumber(catching.HasOwnProp("deadzonePx") ? catching.deadzonePx : "", CATCHING_DEADZONE_PX)
    brake := parseOptionalNumber(catching.HasOwnProp("brakeSpeed") ? catching.brakeSpeed : "", CATCHING_BRAKE_SPEED)

    catching.centerRatio := clampLearningValue(center + 0.004, 0.15, 0.48, 3)
    catching.lookaheadMs := Round(clampLearningValue(lookahead + 1, 15, 120, 0))
    catching.deadzonePx := Round(clampLearningValue(deadzone + 0.4, 1, 10, 0))
    catching.brakeSpeed := clampLearningValue(brake + 0.01, 0.20, 1.60, 3)

    SELECTED_ROD_STATS := buildEffectiveRodStatsFromBase(SELECTED_ROD_BASE_STATS, SELECTED_ENCHANT_NAME, SELECTED_SECONDARY_ENCHANT_NAME)
    configureCatchingForRod(SELECTED_ROD_STATS)
}

clampLearningValue(value, minValue, maxValue, decimals := 3) {
    value := value < minValue ? minValue : value
    value := value > maxValue ? maxValue : value
    if decimals <= 0
        return Round(value)
    return Round(value, decimals)
}

maybeReportLearningStatus(message) {
    global LAST_CATCH_LEARNING_STATUS, LAST_CATCH_LEARNING_AT
    now := A_TickCount
    if message = LAST_CATCH_LEARNING_STATUS && (now - LAST_CATCH_LEARNING_AT) < 1500
        return
    LAST_CATCH_LEARNING_STATUS := message
    LAST_CATCH_LEARNING_AT := now
    updateStatus(message)
}

requestServerText(method, path, body := "", contentType := "", &statusCode := 0) {
    global ROD_SERVER_TIMEOUT_MS

    baseUrl := getServerBaseUrl()
    if baseUrl = "" {
        statusCode := 0
        logErrorCode("SERVER_BASE_URL_EMPTY", "request path=" path ".", "WARN")
        return ""
    }

    if SubStr(path, 1, 1) != "/"
        path := "/" path
    url := baseUrl path

    try {
        request := ComObject("WinHttp.WinHttpRequest.5.1")
        request.SetTimeouts(1500, 1500, ROD_SERVER_TIMEOUT_MS, ROD_SERVER_TIMEOUT_MS)
        request.Open(method, url, false)
        request.SetRequestHeader("User-Agent", "FischMacroClient/0.4")
        request.SetRequestHeader("Accept", "text/plain,application/json")
        if contentType != ""
            request.SetRequestHeader("Content-Type", contentType)
        request.Send(body)
        statusCode := request.Status
        return request.ResponseText
    } catch as err {
        logErrorFromException("SERVER_REQUEST_EXCEPTION", err, "method=" method " path=" path)
        statusCode := 0
        return ""
    }
}

fetchServerCatalogData() {
    global SERVER_CATALOG_ATTEMPTED, SERVER_CATALOG_CACHE, LAST_ROD_SERVER_SYNC

    if SERVER_CATALOG_ATTEMPTED
        return SERVER_CATALOG_CACHE

    SERVER_CATALOG_ATTEMPTED := true
    statusCode := 0
    response := requestServerText("GET", "/api/client/catalog", "", "", &statusCode)
    if statusCode != 200 || response = "" {
        SERVER_CATALOG_ATTEMPTED := false
        return false
    }

    parsed := parseServerCatalogBlock(response)
    if !IsObject(parsed) || !parsed.HasOwnProp("ok") || !parsed.ok {
        SERVER_CATALOG_ATTEMPTED := false
        return false
    }

    if parsed.HasOwnProp("updatedAt") && parsed.updatedAt != ""
        LAST_ROD_SERVER_SYNC := parsed.updatedAt
    SERVER_CATALOG_CACHE := parsed
    return parsed
}

parseServerCatalogBlock(text) {
    parsed := {
        ok: false,
        updatedAt: "",
        rods: Map(),
        enchants: Map()
    }

    Loop Parse, text, "`n", "`r" {
        line := Trim(A_LoopField)
        if line = "" || SubStr(line, 1, 1) = "#" || SubStr(line, 1, 1) = ";"
            continue

        if InStr(line, "status=") = 1 {
            parsed.ok := StrLower(Trim(SubStr(line, 8))) = "ok"
            continue
        }
        if InStr(line, "updatedAt=") = 1 {
            parsed.updatedAt := Trim(SubStr(line, 11))
            continue
        }

        if InStr(line, "rod|") = 1 {
            record := parsePipeRecordLine(SubStr(line, 5))
            rodStats := createRodStatsFromServerRecord(record)
            if IsObject(rodStats) && rodStats.name != ""
                parsed.rods[rodStats.name] := rodStats
            continue
        }

        if InStr(line, "enchant|") = 1 {
            record := parsePipeRecordLine(SubStr(line, 9))
            enchantStats := createEnchantStatsFromServerRecord(record)
            if IsObject(enchantStats) && enchantStats.name != ""
                parsed.enchants[enchantStats.name] := enchantStats
            continue
        }
    }

    return parsed.ok ? parsed : false
}

parsePipeRecordLine(line) {
    record := Map()
    for _, segment in StrSplit(line, "|") {
        separator := InStr(segment, "=")
        if separator <= 1
            continue
        key := Trim(SubStr(segment, 1, separator - 1))
        value := uriDecode(SubStr(segment, separator + 1))
        record[key] := value
    }
    return record
}

createRodStatsFromServerRecord(record) {
    if !IsObject(record) || !record.Has("name")
        return false

    rodName := canonicalizeRodName(record["name"])
    if rodName = ""
        return false

    rodStats := createRodStatsEntry(rodName, "server")
    rodStats.lure := parseOptionalNumber(record.Has("lure") ? record["lure"] : "", "")
    rodStats.luck := parseOptionalNumber(record.Has("luck") ? record["luck"] : "", "")
    rodStats.control := parseOptionalNumber(record.Has("control") ? record["control"] : "", "")
    rodStats.resilience := parseOptionalNumber(record.Has("resilience") ? record["resilience"] : "", "")

    maxKgText := record.Has("maxKg") ? Trim(record["maxKg"]) : ""
    if StrLower(maxKgText) = "inf"
        rodStats.maxKg := "inf"
    else
        rodStats.maxKg := parseOptionalNumber(maxKgText, "")

    if record.Has("passiveInfo")
        rodStats.passiveInfo := Trim(record["passiveInfo"])
    if record.Has("tutorialUrl")
        rodStats.tutorialUrl := Trim(record["tutorialUrl"])
    rodStats.active := true
    if record.Has("active") {
        activeText := StrLower(Trim(record["active"]))
        rodStats.active := !(activeText = "false" || activeText = "0" || activeText = "off")
    }

    catchingStats := {}
    hasCatching := false
    for _, fieldName in ["centerRatio", "lookaheadMs", "brakeSpeed", "deadzonePx", "fishVelocitySmoothing", "barVelocitySmoothing"] {
        if !record.Has(fieldName)
            continue
        value := parseOptionalNumber(record[fieldName], "")
        if isBlankStatValue(value)
            continue
        catchingStats.%fieldName% := value
        hasCatching := true
    }
    if hasCatching
        rodStats.catching := catchingStats

    rodStats.hasStats := hasKnownRodStats(rodStats)
    return rodStats
}

createEnchantStatsFromServerRecord(record) {
    if !IsObject(record) || !record.Has("name")
        return false

    enchantName := normalizeEnchantName(record["name"])
    if enchantName = ""
        return false

    effectText := record.Has("effect") ? record["effect"] : ""
    enchantStats := parseEnchantEffect(effectText)
    enchantStats.name := enchantName
    enchantStats.rawEffect := effectText
    enchantStats.source := "server"
    enchantStats.type := normalizeEnchantType(record.Has("type") ? record["type"] : "primary")

    enchantStats.lure := parseOptionalNumber(record.Has("lure") ? record["lure"] : "", enchantStats.lure)
    enchantStats.luck := parseOptionalNumber(record.Has("luck") ? record["luck"] : "", enchantStats.luck)
    enchantStats.control := parseOptionalNumber(record.Has("control") ? record["control"] : "", enchantStats.control)
    enchantStats.resilience := parseOptionalNumber(record.Has("resilience") ? record["resilience"] : "", enchantStats.resilience)

    maxKgText := record.Has("maxKg") ? Trim(record["maxKg"]) : ""
    if StrLower(maxKgText) = "inf"
        enchantStats.maxKg := "inf"
    else
        enchantStats.maxKg := parseOptionalNumber(maxKgText, enchantStats.maxKg)

    enchantStats.maxKgPercent := parseOptionalNumber(
        record.Has("maxKgPercent") ? record["maxKgPercent"] : "",
        enchantStats.maxKgPercent
    )
    if record.Has("notes")
        enchantStats.notes := record["notes"]

    enchantStats.hasStatBonus := enchantAffectsRodStats(enchantStats)
    return enchantStats
}

parseKeyValueBlock(text) {
    data := Map()
    Loop Parse, text, "`n", "`r" {
        line := Trim(A_LoopField)
        if line = "" || SubStr(line, 1, 1) = "#" || SubStr(line, 1, 1) = ";"
            continue
        separator := InStr(line, "=")
        if separator <= 1
            continue
        key := Trim(SubStr(line, 1, separator - 1))
        value := Trim(SubStr(line, separator + 1))
        data[key] := value
    }
    return data
}

parseOptionalNumber(value, fallbackValue := "") {
    text := Trim("" value)
    if text = "" || StrLower(text) = "null"
        return fallbackValue
    try return Number(StrReplace(text, ",", ""))
    catch
        return fallbackValue
}

getInfoConfigValue(keyName, defaultValue := "") {
    static cache := Map()
    static loaded := false

    if !loaded {
        configPath := A_ScriptDir "\info.ini"
        if FileExist(configPath) {
            contents := FileRead(configPath, "UTF-8")
            Loop Parse, contents, "`n", "`r" {
                line := Trim(A_LoopField)
                if line = "" || SubStr(line, 1, 1) = ";" || SubStr(line, 1, 1) = "#"
                    continue
                splitPos := InStr(line, "=")
                if splitPos <= 1
                    continue
                key := Trim(SubStr(line, 1, splitPos - 1))
                value := Trim(SubStr(line, splitPos + 1))
                cache[key] := value
            }
        }
        loaded := true
    }

    return cache.Has(keyName) ? cache[keyName] : defaultValue
}

normalizeServerUrl(url) {
    normalized := Trim(url)
    if normalized = ""
        return ""
    while SubStr(normalized, -1) = "/"
        normalized := SubStr(normalized, 1, -1)
    return normalized
}

uriEncode(text) {
    encoded := ""
    Loop Parse, "" text {
        ch := A_LoopField
        code := Ord(ch)
        if (code >= 0x30 && code <= 0x39) || (code >= 0x41 && code <= 0x5A) || (code >= 0x61 && code <= 0x7A) || ch = "-" || ch = "_" || ch = "." || ch = "~"
            encoded .= ch
        else if code <= 0xFF
            encoded .= "%" Format("{:02X}", code)
        else
            encoded .= "%3F"
    }
    return encoded
}

uriDecode(text) {
    decoded := ""
    i := 1
    length := StrLen(text)
    while i <= length {
        ch := SubStr(text, i, 1)
        if ch = "%" && i + 2 <= length {
            hex := SubStr(text, i + 1, 2)
            if RegExMatch(hex, "i)^[0-9a-f]{2}$") {
                decoded .= Chr("0x" hex)
                i += 3
                continue
            }
        } else if ch = "+" {
            decoded .= " "
            i += 1
            continue
        }

        decoded .= ch
        i += 1
    }
    return decoded
}

setSelectedRod(rodName, enchantName := "", secondaryEnchantName := "") {
    global ROD_DATA, SELECTED_ROD_NAME, SELECTED_ENCHANT_NAME, SELECTED_SECONDARY_ENCHANT_NAME, SELECTED_ROD_BASE_STATS, SELECTED_ROD_STATS

    canonicalName := canonicalizeRodName(rodName)
    if !ROD_DATA.Has(canonicalName)
        return false

    selectedEnchant := normalizeSelectedEnchant(enchantName)
    selectedSecondaryEnchant := normalizeSelectedEnchant(secondaryEnchantName, "secondary")
    baseStats := cloneRodStats(ROD_DATA[canonicalName])
    effectiveStats := buildEffectiveRodStatsFromBase(baseStats, selectedEnchant, selectedSecondaryEnchant)

    SELECTED_ROD_NAME := canonicalName
    SELECTED_ENCHANT_NAME := selectedEnchant
    SELECTED_SECONDARY_ENCHANT_NAME := selectedSecondaryEnchant
    SELECTED_ROD_BASE_STATS := baseStats
    SELECTED_ROD_STATS := effectiveStats
    return true
}

getSelectedRodStats() {
    global SELECTED_ROD_STATS
    return SELECTED_ROD_STATS
}

getRodNames() {
    global ROD_DATA

    nameBlob := ""
    for rodName, rodStats in ROD_DATA {
        if !isRodActive(rodStats)
            continue
        nameBlob .= rodName "`n"
    }

    nameBlob := RTrim(nameBlob, "`n")
    if nameBlob = ""
        return []

    sortedBlob := Sort(nameBlob, "D`n")
    return StrSplit(sortedBlob, "`n")
}

getEnchantNames(enchantType := "all") {
    global ENCHANT_DATA

    normalizedType := StrLower(Trim(enchantType))
    if normalizedType = ""
        normalizedType := "all"

    nameBlob := ""
    for enchantName, enchantStats in ENCHANT_DATA {
        typeName := getEnchantType(enchantStats)
        if normalizedType != "all" && typeName != normalizedType
            continue
        nameBlob .= enchantName "`n"
    }

    nameBlob := RTrim(nameBlob, "`n")
    if nameBlob = ""
        return []

    sortedBlob := Sort(nameBlob, "D`n")
    return StrSplit(sortedBlob, "`n")
}

getEnchantType(enchantStats) {
    if !IsObject(enchantStats)
        return "primary"
    if enchantStats.HasOwnProp("type")
        return normalizeEnchantType(enchantStats.type)
    return "primary"
}

buildRodSelectionItems(rodNames) {
    global ROD_DATA

    labels := []
    labelToRod := Map()
    rodToLabel := Map()

    for _, rodName in rodNames {
        if !ROD_DATA.Has(rodName) || !isRodActive(ROD_DATA[rodName]) || !hasKnownRodStats(ROD_DATA[rodName])
            continue
        labels.Push(rodName)
        labelToRod[rodName] := rodName
        rodToLabel[rodName] := rodName
    }

    for _, rodName in rodNames {
        if !ROD_DATA.Has(rodName) || !isRodActive(ROD_DATA[rodName]) || hasKnownRodStats(ROD_DATA[rodName])
            continue
        label := rodName " (stats missing)"
        labels.Push(label)
        labelToRod[label] := rodName
        rodToLabel[rodName] := label
    }

    return {
        labels: labels,
        labelToRod: labelToRod,
        rodToLabel: rodToLabel
    }
}

resolveRodNameFromSelection(selectionText, selectionItems) {
    global ROD_DATA

    text := Trim(selectionText)
    if text = ""
        return ""

    if IsObject(selectionItems) && selectionItems.labelToRod.Has(text)
        return selectionItems.labelToRod[text]

    canonicalName := canonicalizeRodName(text)
    return ROD_DATA.Has(canonicalName) ? canonicalName : ""
}

getRodLabelForName(selectionItems, rodName) {
    if !IsObject(selectionItems) || rodName = ""
        return ""

    canonicalName := canonicalizeRodName(rodName)
    if selectionItems.rodToLabel.Has(canonicalName)
        return selectionItems.rodToLabel[canonicalName]
    return ""
}

formatRodStatsForDisplay(rodName, enchantName := "", secondaryEnchantName := "") {
    global ROD_DATA, ENCHANT_DATA

    if rodName = ""
        return "Select a rod from the list."

    canonicalName := canonicalizeRodName(rodName)
    if !ROD_DATA.Has(canonicalName)
        return "Stats unavailable."

    normalizedEnchant := normalizeSelectedEnchant(enchantName)
    normalizedSecondaryEnchant := normalizeSelectedEnchant(secondaryEnchantName, "secondary")
    baseStats := ROD_DATA[canonicalName]
    effectiveStats := buildEffectiveRodStatsFromBase(baseStats, normalizedEnchant, normalizedSecondaryEnchant)

    line := "Rod: " canonicalName
    line .= "`nPrimary Enchant: " (normalizedEnchant = "" ? "(None)" : normalizedEnchant)
    line .= "`nSecondary Enchant: " (normalizedSecondaryEnchant = "" ? "(None)" : normalizedSecondaryEnchant)
    line .= "`nLure Speed: " formatStatDisplay(baseStats.lure, effectiveStats.lure, "percent")
    line .= "`nLuck: " formatStatDisplay(baseStats.luck, effectiveStats.luck, "percent")
    line .= "`nControl: " formatStatDisplay(baseStats.control, effectiveStats.control, "control")
    line .= "`nResilience: " formatStatDisplay(baseStats.resilience, effectiveStats.resilience, "percent")
    line .= "`nMax Kg: " formatStatDisplay(baseStats.maxKg, effectiveStats.maxKg, "maxKg")

    if normalizedEnchant != "" && ENCHANT_DATA.Has(normalizedEnchant)
        line .= "`nPrimary effect: " formatEnchantEffectSummary(ENCHANT_DATA[normalizedEnchant])
    if normalizedSecondaryEnchant != "" && ENCHANT_DATA.Has(normalizedSecondaryEnchant)
        line .= "`nSecondary effect: " formatEnchantEffectSummary(ENCHANT_DATA[normalizedSecondaryEnchant])

    passiveInfo := baseStats.HasOwnProp("passiveInfo") ? Trim("" baseStats.passiveInfo) : ""
    if passiveInfo != ""
        line .= "`nPassive: " passiveInfo

    tutorialUrl := baseStats.HasOwnProp("tutorialUrl") ? Trim("" baseStats.tutorialUrl) : ""
    if tutorialUrl != ""
        line .= "`nTutorial: Available (click Tutorial button)."

    if !hasKnownRodStats(baseStats) {
        if baseStats.source = "server"
            line .= "`nData source: online database (stats missing)."
        else
            line .= "`nData source: fallback/catalog (missing live stats)."
    }
    else if baseStats.source = "server"
        line .= "`nData source: online database."
    else if baseStats.source = "scraped"
        line .= "`nData source: live scrape."
    else if baseStats.source = "catalog"
        line .= "`nData source: local catalog."
    else
        line .= "`nData source: cached fallback."

    return line
}

formatStatDisplay(baseValue, effectiveValue, statType) {
    baseText := formatStatValue(baseValue, statType)

    if statType = "maxKg" {
        if !isInfinityValue(baseValue) && isInfinityValue(effectiveValue)
            return baseText " -> inf (enchant)"
    }

    if !tryParseFiniteNumber(baseValue, &baseNumber) || !tryParseFiniteNumber(effectiveValue, &effectiveNumber)
        return baseText

    if Abs(effectiveNumber - baseNumber) < 0.0001
        return baseText

    suffix := ""
    if statType = "percent"
        suffix := "%"
    else if statType = "maxKg"
        suffix := " kg"

    return baseText " -> " formatStatValue(effectiveValue, statType) " (" formatSignedNumber(effectiveNumber - baseNumber) suffix ")"
}

formatStatValue(value, statType) {
    if statType = "percent"
        return formatRodPercent(value)
    if statType = "maxKg"
        return formatRodMaxKg(value)
    return formatRodControl(value)
}

formatRodPercent(value) {
    if isBlankStatValue(value)
        return "Unknown"
    return formatCleanNumber(value) "%"
}

formatRodControl(value) {
    if isBlankStatValue(value)
        return "Unknown"
    return formatCleanNumber(value)
}

formatRodMaxKg(value) {
    if isBlankStatValue(value)
        return "Unknown"
    return isInfinityValue(value) ? "inf" : formatCleanNumber(value) " kg"
}

formatCleanNumber(value) {
    if isInfinityValue(value)
        return "inf"

    try number := Number(value)
    catch
        return value

    if Abs(number - Round(number)) < 0.00001
        return Round(number)

    text := Format("{:.3f}", number)
    text := RegExReplace(text, "0+$", "")
    text := RegExReplace(text, "\.$", "")
    return text
}

formatSignedNumber(value) {
    try number := Number(value)
    catch
        return value
    sign := number > 0 ? "+" : ""
    return sign formatCleanNumber(number)
}

formatEnchantEffectSummary(enchantStats) {
    parts := []
    if enchantStats.lure != ""
        parts.Push(formatSignedNumber(enchantStats.lure) "% Lure")
    if enchantStats.luck != ""
        parts.Push(formatSignedNumber(enchantStats.luck) "% Luck")
    if enchantStats.control != ""
        parts.Push(formatSignedNumber(enchantStats.control) " Control")
    if enchantStats.resilience != ""
        parts.Push(formatSignedNumber(enchantStats.resilience) "% Resilience")
    if enchantStats.maxKg = "inf"
        parts.Push("Max Kg -> inf")
    else if enchantStats.maxKg != ""
        parts.Push(formatSignedNumber(enchantStats.maxKg) " Max Kg")
    if enchantStats.maxKgPercent != ""
        parts.Push(formatSignedNumber(enchantStats.maxKgPercent) "% Max Kg")

    if parts.Length > 0
        return joinTextList(parts)

    rawEffect := enchantStats.HasOwnProp("rawEffect") ? Trim(enchantStats.rawEffect) : ""
    return rawEffect = "" ? "No direct rod stat change." : rawEffect
}

joinTextList(values, delimiter := ", ") {
    output := ""
    for index, value in values {
        if index > 1
            output .= delimiter
        output .= value
    }
    return output
}

findItemIndex(items, target) {
    if target = ""
        return 0
    for index, value in items {
        if value = target
            return index
    }
    return 0
}

normalizeSelectedEnchant(enchantName, desiredType := "all") {
    global ENCHANT_DATA

    text := Trim(enchantName)
    targetType := StrLower(Trim(desiredType))
    if targetType = ""
        targetType := "all"
    if text = "" || text = "(None)"
        return ""
    if ENCHANT_DATA.Has(text) {
        if targetType = "all" || getEnchantType(ENCHANT_DATA[text]) = targetType
            return text
        return ""
    }

    lowerText := StrLower(text)
    for name, stats in ENCHANT_DATA {
        if StrLower(name) != lowerText
            continue
        if targetType != "all" && getEnchantType(stats) != targetType
            continue
        return name
    }
    return ""
}

buildEffectiveRodStatsFromBase(baseStats, enchantName := "", secondaryEnchantName := "") {
    global ENCHANT_DATA

    effective := cloneRodStats(baseStats)
    normalizedEnchant := normalizeSelectedEnchant(enchantName)
    normalizedSecondaryEnchant := normalizeSelectedEnchant(secondaryEnchantName, "secondary")
    effective.enchantName := normalizedEnchant
    effective.secondaryEnchantName := normalizedSecondaryEnchant
    effective.enchantStats := false
    effective.secondaryEnchantStats := false

    if normalizedEnchant != "" && ENCHANT_DATA.Has(normalizedEnchant) {
        enchantStats := ENCHANT_DATA[normalizedEnchant]
        effective.enchantStats := enchantStats
        applyEnchantStatsToRod(effective, enchantStats)
    }

    if normalizedSecondaryEnchant != "" && ENCHANT_DATA.Has(normalizedSecondaryEnchant) {
        secondaryStats := ENCHANT_DATA[normalizedSecondaryEnchant]
        effective.secondaryEnchantStats := secondaryStats
        applyEnchantStatsToRod(effective, secondaryStats)
    }

    effective.hasStats := hasKnownRodStats(effective)
    return effective
}

applyEnchantStatsToRod(rodStats, enchantStats) {
    applyEnchantDelta(rodStats, "lure", enchantStats.lure)
    applyEnchantDelta(rodStats, "luck", enchantStats.luck)
    applyEnchantDelta(rodStats, "control", enchantStats.control)
    applyEnchantDelta(rodStats, "resilience", enchantStats.resilience)

    if enchantStats.maxKg = "inf" {
        rodStats.maxKg := "inf"
        return
    }

    if enchantStats.maxKg != "" && tryParseFiniteNumber(rodStats.maxKg, &baseKg) && tryParseFiniteNumber(enchantStats.maxKg, &extraKg)
        rodStats.maxKg := baseKg + extraKg
    if enchantStats.maxKgPercent != "" && tryParseFiniteNumber(rodStats.maxKg, &maxKgNow) && tryParseFiniteNumber(enchantStats.maxKgPercent, &pct)
        rodStats.maxKg := Round(maxKgNow * (1 + (pct / 100)), 2)
}

applyEnchantDelta(rodStats, fieldName, deltaValue) {
    if deltaValue = ""
        return
    if !tryParseFiniteNumber(rodStats.%fieldName%, &baseValue)
        return
    if !tryParseFiniteNumber(deltaValue, &deltaNumber)
        return
    rodStats.%fieldName% := baseValue + deltaNumber
}

cloneRodStats(sourceStats) {
    if !IsObject(sourceStats)
        return createRodStatsEntry("", "")

    clone := {
        name: sourceStats.HasOwnProp("name") ? sourceStats.name : "",
        lure: sourceStats.HasOwnProp("lure") ? sourceStats.lure : "",
        luck: sourceStats.HasOwnProp("luck") ? sourceStats.luck : "",
        control: sourceStats.HasOwnProp("control") ? sourceStats.control : "",
        resilience: sourceStats.HasOwnProp("resilience") ? sourceStats.resilience : "",
        maxKg: sourceStats.HasOwnProp("maxKg") ? sourceStats.maxKg : "",
        passiveInfo: sourceStats.HasOwnProp("passiveInfo") ? sourceStats.passiveInfo : "",
        tutorialUrl: sourceStats.HasOwnProp("tutorialUrl") ? sourceStats.tutorialUrl : "",
        source: sourceStats.HasOwnProp("source") ? sourceStats.source : "",
        hasStats: sourceStats.HasOwnProp("hasStats") ? sourceStats.hasStats : false
    }

    if sourceStats.HasOwnProp("catching") && IsObject(sourceStats.catching) {
        clone.catching := {}
        for key, value in sourceStats.catching.OwnProps()
            clone.catching.%key% := value
    }

    clone.active := sourceStats.HasOwnProp("active") ? sourceStats.active : true

    return clone
}

isRodActive(rodStats) {
    if !IsObject(rodStats)
        return true
    if !rodStats.HasOwnProp("active")
        return true
    value := StrLower(Trim("" rodStats.active))
    return !(value = "false" || value = "0" || value = "off")
}

hasKnownRodStats(rodStats) {
    if !IsObject(rodStats)
        return false

    return !isBlankStatValue(rodStats.lure)
        || !isBlankStatValue(rodStats.luck)
        || !isBlankStatValue(rodStats.control)
        || !isBlankStatValue(rodStats.resilience)
        || !isBlankStatValue(rodStats.maxKg)
}

isBlankStatValue(value) {
    text := Trim("" value)
    return text = "" || StrLower(text) = "null"
}

isInfinityValue(value) {
    return StrLower(Trim("" value)) = "inf"
}

tryParseFiniteNumber(value, &outNumber) {
    outNumber := 0
    text := Trim("" value)
    if text = "" || StrLower(text) = "inf" || StrLower(text) = "null"
        return false
    try {
        outNumber := Number(StrReplace(text, ",", ""))
        return true
    } catch {
        return false
    }
}

normalizeRodName(name) {
    name := RegExReplace(name, "\[[^\]]+\]", "")
    name := RegExReplace(name, "\s+", " ")
    return Trim(name)
}

canonicalizeRodName(rodName) {
    static aliases := Map(
        "kings rod", "Kings Rod",
        "king's rod", "Kings Rod",
        "ice warpers rod", "Ice Warpers Rod",
        "ice warper's rod", "Ice Warpers Rod",
        "ethereal prism", "Ethereal Prism Rod",
        "ethereal prism rod", "Ethereal Prism Rod",
        "great rod of oscar", "Great Rod of Oscar",
        "rod of the depths", "Rod Of The Depths",
        "rod of the exalted one", "Rod Of The Exalted One",
        "crystallized rod", "Crystalized Rod"
    )

    cleaned := normalizeRodName(rodName)
    if cleaned = ""
        return ""

    key := StrLower(cleaned)
    return aliases.Has(key) ? aliases[key] : cleaned
}

normalizeEnchantName(name) {
    name := RegExReplace(name, "\[[^\]]+\]", "")
    name := RegExReplace(name, "\s+", " ")
    return Trim(name)
}

normalizeEnchantType(enchantType) {
    return StrLower(Trim("" enchantType)) = "secondary" ? "secondary" : "primary"
}

parseRodNumber(value) {
    if value = ""
        return ""

    normalized := StrLower("" value)
    normalized := StrReplace(normalized, ",", "")
    normalized := StrReplace(normalized, "%", "")
    normalized := StrReplace(normalized, "kg", "")
    normalized := StrReplace(normalized, "c$", "")
    normalized := RegExReplace(normalized, "[^\d\.\-]+", "")
    if normalized = ""
        return ""

    try return Number(normalized)
    catch
        return ""
}

parseEnchantEffect(effectText) {
    lower := StrLower(effectText)
    result := {
        lure: "",
        luck: "",
        control: "",
        resilience: "",
        maxKg: "",
        maxKgPercent: "",
        rawEffect: effectText,
        source: "",
        type: "primary",
        hasStatBonus: false
    }

    if RegExMatch(lower, "([+\-]?\d[\d,]*(?:\.\d+)?)\s*%?\s*lure(?:\s*speed)?", &lureMatch)
        result.lure := parseRodNumber(lureMatch[1])
    if RegExMatch(lower, "([+\-]?\d[\d,]*(?:\.\d+)?)\s*%?\s*control", &controlMatch)
        result.control := parseRodNumber(controlMatch[1])
    if RegExMatch(lower, "([+\-]?\d[\d,]*(?:\.\d+)?)\s*%?\s*resilience", &resilienceMatch)
        result.resilience := parseRodNumber(resilienceMatch[1])

    cleanLuck := RegExReplace(lower, "([+\-]?\d[\d,]*(?:\.\d+)?)\s*%?\s*mutation luck", "")
    if RegExMatch(cleanLuck, "([+\-]?\d[\d,]*(?:\.\d+)?)\s*%?\s*luck", &luckMatch)
        result.luck := parseRodNumber(luckMatch[1])

    if RegExMatch(lower, "inf\s*max\s*kg")
        result.maxKg := "inf"
    if RegExMatch(lower, "([+\-]?\d[\d,]*(?:\.\d+)?)\s*%\s*max\s*kg", &maxKgPercentMatch)
        result.maxKgPercent := parseRodNumber(maxKgPercentMatch[1])
    if RegExMatch(lower, "([+\-]?\d[\d,]*(?:\.\d+)?)\s*max\s*kg", &maxKgMatch) {
        maxKgValue := parseRodNumber(maxKgMatch[1])
        if result.maxKgPercent = "" || maxKgValue != result.maxKgPercent
            result.maxKg := maxKgValue
    }

    result.hasStatBonus := enchantAffectsRodStats(result)
    return result
}

enchantAffectsRodStats(enchantStats) {
    return enchantStats.lure != ""
        || enchantStats.luck != ""
        || enchantStats.control != ""
        || enchantStats.resilience != ""
        || enchantStats.maxKg != ""
        || enchantStats.maxKgPercent != ""
}

mergeRodDataFromLocalCatalog(rodData) {
    catalogPath := A_ScriptDir "\server-dashboard\data\rods.json"
    if !FileExist(catalogPath)
        return 0

    jsonText := FileRead(catalogPath, "UTF-8")
    if jsonText = ""
        return 0

    count := 0
    pos := 1
    dq := Chr(34)
    entryPattern := "s)" dq "name" dq "\s*:\s*" dq "((?:\\.|[^" dq "\\])*)" dq "\s*,\s*" dq "stats" dq "\s*:\s*\{(.*?)\}(?:\s*,\s*" dq "catching" dq "\s*:\s*\{(.*?)\})?"
    while RegExMatch(jsonText, entryPattern, &match, pos) {
        pos := match.Pos + match.Len
        rodName := canonicalizeRodName(decodeJsonString(match[1]))
        if rodName = ""
            continue

        statsBlock := match[2]
        catchingBlock := match[3]
        catalogStats := {
            name: rodName,
            lure: parseJsonStatField(statsBlock, "lure"),
            luck: parseJsonStatField(statsBlock, "luck"),
            control: parseJsonStatField(statsBlock, "control"),
            resilience: parseJsonStatField(statsBlock, "resilience"),
            maxKg: parseJsonStatField(statsBlock, "maxKg"),
            source: "catalog",
            hasStats: false
        }
        catchingStats := parseJsonCatchingBlock(catchingBlock)
        if IsObject(catchingStats)
            catalogStats.catching := catchingStats
        catalogStats.hasStats := hasKnownRodStats(catalogStats)
        mergeRodStatsEntry(rodData, rodName, catalogStats)
        count += 1
    }

    return count
}

parseJsonStatField(statsBlock, fieldName) {
    dq := Chr(34)
    pattern := "i)" dq fieldName dq "\s*:\s*(null|" dq "(?:\\.|[^" dq "\\])*" dq "|[-]?\d+(?:\.\d+)?)"
    if !RegExMatch(statsBlock, pattern, &match)
        return ""

    token := Trim(match[1])
    if StrLower(token) = "null"
        return ""

    if SubStr(token, 1, 1) = Chr(34) {
        text := decodeJsonString(SubStr(token, 2, -1))
        if StrLower(text) = "inf"
            return "inf"
        return parseOptionalNumber(text, "")
    }

    return parseOptionalNumber(token, "")
}

parseJsonCatchingBlock(catchingBlock) {
    if Trim(catchingBlock) = ""
        return false

    catchingStats := {}
    hasValue := false
    for _, fieldName in ["centerRatio", "lookaheadMs", "brakeSpeed", "deadzonePx", "fishVelocitySmoothing", "barVelocitySmoothing"] {
        value := parseJsonStatField(catchingBlock, fieldName)
        if isBlankStatValue(value)
            continue
        catchingStats.%fieldName% := value
        hasValue := true
    }

    return hasValue ? catchingStats : false
}

decodeJsonString(text) {
    text := StrReplace(text, "\/", "/")
    text := StrReplace(text, "\u0027", "'")
    text := StrReplace(text, "\u2019", "'")
    return text
}

mergeRodStatsEntry(rodData, rodName, incomingStats) {
    canonicalName := canonicalizeRodName(rodName)
    if canonicalName = ""
        return

    if !rodData.Has(canonicalName)
        rodData[canonicalName] := createRodStatsEntry(canonicalName, "fallback")

    target := rodData[canonicalName]
    mergeRodStatField(target, incomingStats, "lure")
    mergeRodStatField(target, incomingStats, "luck")
    mergeRodStatField(target, incomingStats, "control")
    mergeRodStatField(target, incomingStats, "resilience")
    mergeRodStatField(target, incomingStats, "maxKg")
    mergeRodTextField(target, incomingStats, "passiveInfo")
    mergeRodTextField(target, incomingStats, "tutorialUrl")

    if incomingStats.HasOwnProp("catching") && IsObject(incomingStats.catching) {
        target.catching := {}
        for key, value in incomingStats.catching.OwnProps()
            target.catching.%key% := value
    }

    if incomingStats.HasOwnProp("active")
        target.active := incomingStats.active

    target.hasStats := hasKnownRodStats(target)
    if incomingStats.HasOwnProp("source") && incomingStats.source != ""
        target.source := incomingStats.source
}

mergeRodStatField(targetStats, incomingStats, fieldName) {
    if !incomingStats.HasOwnProp(fieldName)
        return
    value := normalizeRodStatValue(incomingStats.%fieldName%)
    if isBlankStatValue(value)
        return
    targetStats.%fieldName% := value
}

mergeRodTextField(targetStats, incomingStats, fieldName) {
    if !incomingStats.HasOwnProp(fieldName)
        return
    value := Trim("" incomingStats.%fieldName%)
    if value = ""
        return
    targetStats.%fieldName% := value
}

normalizeRodStatValue(value) {
    text := Trim("" value)
    if text = "" || StrLower(text) = "null"
        return ""
    if StrLower(text) = "inf"
        return "inf"
    try return Number(StrReplace(text, ",", ""))
    catch
        return value
}

getFallbackRodData() {
    rodData := Map()

    ; Core rods kept locally so setup still works if scraping fails.
    addRodStats(rodData, "Flimsy Rod", 0, 0, 0, 0, 10.4)
    addRodStats(rodData, "Fischer's Rod", 10, 20, 0.05, 5, 150)
    addRodStats(rodData, "Training Rod", -5, 15, 0.2, -5, 200)
    addRodStats(rodData, "Plastic Rod", 10, 5, 0.05, 0, 100)
    addRodStats(rodData, "Carbon Rod", -10, 25, 0.05, 10, 600)
    addRodStats(rodData, "Fast Rod", 45, -15, 0.05, 0, 175)
    addRodStats(rodData, "Lucky Rod", 20, 60, -0.12, 0, 175)
    addRodStats(rodData, "Long Rod", 0, 30, 0.05, 0, 2500)
    addRodStats(rodData, "Stone Rod", -25, 40, 0.05, 5, 2000)
    addRodStats(rodData, "Kings Rod", 55, 55, 0.15, 10, 7500)
    addRodStats(rodData, "Ice Warpers Rod", 65, 85, 0.25, 35, 1000000)
    addRodStats(rodData, "Friendly Rod", 80, 120, 0.25, 50, "inf")
    addRodStats(rodData, "Abyssal Specter Rod", 25, 90, 0.22, 15, 100000)
    addRodStats(rodData, "Rod Of The Depths", 20, 130, 0.15, 8, 30000)
    addRodStats(rodData, "Rod Of The Exalted One", 25, 130, 0.2, 10, 75000)
    addRodStats(rodData, "Heaven's Rod", 30, 225, 0.2, 30, 30000)
    addRodStats(rodData, "No-Life Rod", 90, 105, 0.23, 10, 10000)
    addRodStats(rodData, "Kraken Rod", 55, 185, 0.2, 15, 115000)
    addRodStats(rodData, "Fang of the Eclipse Rod", 95, 220, 0.25, 40, 2000000)
    addRodStats(rodData, "Astralhook Rod", 50, 195, 0.1, 10, 200000)
    addRodStats(rodData, "Sovereign Doombringer Rod", 10, 160, 0.2, 20, 200000)
    addRodStats(rodData, "Clickbait Caster Rod", 35, 60, 0.2, 15, 50000)
    addRodStats(rodData, "View Smasher Rod", 200, 20, 0.15, 0, 200000)
    addRodStats(rodData, "Fish Photographer Rod", 85, 150, 0.08, 15, 500000)
    addRodStats(rodData, "Tryhard Rod", 50, 100, 0.1, 20, 200000)
    addRodStats(rodData, "Paintbrush", 95, 150, -0.1, 10, 1000000)
    addRodStats(rodData, "nilCaster", 0, -10, 0, 0, 1000)

    return rodData
}

getFallbackEnchantData() {
    enchantData := Map()

    addFallbackEnchant(enchantData, "Swift", "+30% Lure Speed")
    addFallbackEnchant(enchantData, "Hasty", "+55% Lure Speed")
    addFallbackEnchant(enchantData, "Lucky", "+20% Luck, +15% Lure Speed")
    addFallbackEnchant(enchantData, "Divine", "+45% Luck, +20% Resilience, +20% Lure Speed")
    addFallbackEnchant(enchantData, "Breezed", "+65% Luck, +10% Lure Speed")
    addFallbackEnchant(enchantData, "Quantum", "+25% Luck")
    addFallbackEnchant(enchantData, "Piercing", "+0.2 Control")
    addFallbackEnchant(enchantData, "Invincible", "Inf Max Kg")
    addFallbackEnchant(enchantData, "Herculean", "+25000 Max Kg, +0.2 Control")
    addFallbackEnchant(enchantData, "Mystical", "+25% Luck, +45% Resilience, +15% Lure Speed")
    addFallbackEnchant(enchantData, "Resilient", "+35% Resilience")
    addFallbackEnchant(enchantData, "Controlled", "+0.05 Control")
    addFallbackEnchant(enchantData, "Abyssal", "+10% Resilience")
    addFallbackEnchant(enchantData, "Quality", "+15% Lure Speed, +15% Luck")
    addFallbackEnchant(enchantData, "Rapid", "+30% Lure Speed")
    addFallbackEnchant(enchantData, "Unbreakable", "+10000 Max Kg")
    addFallbackEnchant(enchantData, "Noir", "Mutation luck bonus.", "secondary")
    addFallbackEnchant(enchantData, "Sea Overlord", "Progress speed bonus.", "secondary")
    addFallbackEnchant(enchantData, "Blessed Song", "Chance to instantly catch fish.", "secondary")
    addFallbackEnchant(enchantData, "Wormhole", "Chance to wormhole fish.", "secondary")

    return enchantData
}

addFallbackEnchant(enchantData, enchantName, effectText, enchantType := "primary") {
    parsed := parseEnchantEffect(effectText)
    parsed.name := enchantName
    parsed.rawEffect := effectText
    parsed.source := "fallback"
    parsed.type := normalizeEnchantType(enchantType)
    parsed.hasStatBonus := enchantAffectsRodStats(parsed)
    enchantData[enchantName] := parsed
}

addRodStats(rodData, name, lure, luck, control, resilience, maxKg) {
    canonicalName := canonicalizeRodName(name)
    rodData[canonicalName] := {
        name: canonicalName,
        lure: lure,
        luck: luck,
        control: control,
        resilience: resilience,
        maxKg: maxKg,
        passiveInfo: "",
        tutorialUrl: "",
        source: "fallback",
        hasStats: true,
        active: true
    }
}

createRodStatsEntry(name, source := "fallback") {
    return {
        name: name,
        lure: "",
        luck: "",
        control: "",
        resilience: "",
        maxKg: "",
        passiveInfo: "",
        tutorialUrl: "",
        source: source,
        hasStats: false,
        active: true
    }
}

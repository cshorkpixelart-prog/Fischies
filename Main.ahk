#Requires AutoHotkey v2.0

; ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
; DIRECTIVES & CONFIGURATIONS
; ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰

#SingleInstance Force
CoordMode "Mouse", "Client"
CoordMode "Pixel", "Client"
SetMouseDelay 10
SendMode "Input"
#NoTrayIcon

; ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
; LIBRARIES
; ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰

#Include <Pin>
#Include <OCR>

#Include "%A_ScriptDir%\Modules"
#Include Casting.ahk
#Include Catching.ahk
#Include ColorConfig.ahk
#Include ChatMenu.ahk
#Include RandomFunctions.ahk
#Include RodData.ahk
#Include Logger.ahk
#Include Shaking.ahk
#Include StatusUpdates.ahk
#Include UserInterface.ahk

; ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
; GLOBAL VARIABLES
; ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰

MACRO_TITLE := "Fisch Mode"
CEREBRA_HANDLER_SCRIPT := "cerebra_handler.py"
CEREBRA_HANDLER_LAUNCHED := false


; ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
; HOTKEYS
; ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰

F1::startMacro()
F2::pauseMacro()
F3::exitMacro()
F4::openFeedbackGui()
F5::reloadMacro()
F7::redoDetectionSetup()
F12::toggleSafePause()

; ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
; MACRO
; ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰

runMacro()

runMacro() {
    initLogger()
    logEvent("Macro bootstrap started.")
    activateRoblox()
    checkDisplayScaling()
    changeGraphicsSettings()
    Sleep "100"
    ZoomInAndZoomOut()
    Sleep "100"
    updateTrayIcon()
    loadColorPresetConfig()
    ;displaySettingsGui()
    ;displayMainGui()
    ensureCatchScanConfigured()
    ensureShakeAreaConfigured()
    openSetupGuiAtRun()
    updateStatus("Finish setup in GUI, then press F1.")
    logEvent("Macro bootstrap complete.")
}

startMacro(*) {
    initLogger()
    logEvent("Start requested (F1).")
    if !isMacroSetupComplete() {
        showRodSelectionGui()
        updateStatus("Finish setup in GUI, then press F1.")
        logErrorCode("SETUP_INCOMPLETE", "Start blocked: setup not complete.", "WARN")
        return
    }

    if syncSelectedRodFromServer(false)
        updateStatus("Rod data synced from server. Starting macro...")
    else
        updateStatus("Using local rod data. Starting macro...")

    if DetectCerebraRod() {
        if launchCerebraHandlerOnce() {
            updateStatus("Cerebra selected: launched cerebra_handler.py and exiting.")
            Sleep 150
            ExitApp
        }
        MsgBox "Cerebra Rod selected, but cerebra_handler.py could not be launched.`nInstall Python and ensure the file exists in: " A_ScriptDir, MACRO_TITLE, 48
        return
    }

    Loop {
        logEvent("Macro cycle start.", "STEP")
        activateRoblox()
        closeChatMenu()
        closeBackpack()
        ;showUserInterface()
        ;equipRod()
        hideUserInterface()
        Sleep 100
        ensureRodEquippedQuick()
        castLine()
        try shakeOk := autoShake()
        catch as err {
            errMsg := formatAhkError("Shake error", err)
            logErrorCode("SHAKE_EXCEPTION", errMsg)
            updateStatus(errMsg)
            Sleep 1200
            continue
        }
        if !shakeOk {
            ; Some rods skip/flash through shake state. Try one catch pass anyway.
            logErrorCode("SHAKE_NO_RESULT", "Shake returned false. Running catch fallback.", "WARN")
            updateStatus("Catch: fallback")
            try {
                catchFish()
            }
            catch as err {
                errMsg := formatAhkError("Catch error", err)
                logErrorCode("CATCH_EXCEPTION", errMsg)
                updateStatus(errMsg)
                Sleep 1200
                continue
            }
            maybeClearSessionLogAfterSuccessfulCatch()
            processCatchLearningCycle()
            Sleep 800
            continue
        }

        getArrowOffsets()

        updateStatus("Catch: init")
        try {
            catchFish()
        }
        catch as err {
            errMsg := formatAhkError("Catch error", err)
            logErrorCode("CATCH_EXCEPTION", errMsg)
            updateStatus(errMsg)
            Sleep 1200
            continue
        }
        maybeClearSessionLogAfterSuccessfulCatch()
        processCatchLearningCycle()



        Sleep 3000
    }

}




pauseMacro(*) {
    if A_IsPaused
        updateStatus("")
    else
        updateStatus("*MACRO PAUSED*")
    logEvent(A_IsPaused ? "Macro resumed (F2)." : "Macro paused (F2).", "STEP")
    Pause -1
}

exitMacro(*) {
    logEvent("Exit requested (F3).", "STEP")
    ExitApp
}

reloadMacro(*) {
    logEvent("Reload requested (F5).", "STEP")
    Reload
}

redoDetectionSetup(*) {
    updateStatus("Re-running detection setup...")
    try {
        redoCatchScanSetup()
        redoShakeAreaSetup()
        updateStatus("Detection setup saved.")
        Sleep 900
        updateStatus("Finish setup in GUI, then press F1.")
    } catch as err {
        errMsg := formatAhkError("Setup redo error", err)
        logErrorCode("SETUP_REDO_EXCEPTION", errMsg)
        updateStatus(errMsg)
    }
}

toggleSafePause(*) {
    if A_IsPaused
        updateStatus("")
    else
        updateStatus("*MACRO PAUSED*")
    logEvent(A_IsPaused ? "Macro resumed (F12)." : "Macro paused (F12).", "STEP")
    Pause -1
}

maybeClearSessionLogAfterSuccessfulCatch() {
    metrics := getLastCatchLearningMetrics()
    if !IsObject(metrics)
        return false
    if !metrics.HasOwnProp("outcome")
        return false
    if metrics.outcome != "success"
        return false
    return clearSessionLog()
}

formatAhkError(prefix, err) {
    message := prefix
    try {
        if err.HasOwnProp("Message") && err.Message != ""
            message .= ": " err.Message
    }
    try {
        if err.HasOwnProp("Line") && err.Line
            message .= " (L" err.Line ")"
    }
    return message
}

DetectCerebraRod() {
    return isHeartbeatControlModeSelected()
}

launchCerebraHandlerOnce() {
    global CEREBRA_HANDLER_SCRIPT, CEREBRA_HANDLER_LAUNCHED
    if CEREBRA_HANDLER_LAUNCHED
        return false

    handlerPath := A_ScriptDir "\" CEREBRA_HANDLER_SCRIPT
    startupLogPath := A_ScriptDir "\logs\cerebra_python_start.log"
    rodName := ""
    controlStat := 0.0
    lureSpeed := 0.0
    clientX := 0
    clientY := 0

    try rodName := SELECTED_ROD_NAME
    try controlStat := CATCHING_SELECTED_CONTROL
    try lureSpeed := getSelectedLureSpeedPercent()
    try WinGetClientPos &clientX, &clientY, , , "ahk_exe RobloxPlayerBeta.exe"

    args := Format(
        '--run-macro --mode auto --rod-name "{1}" --control {2} --lure-speed {3} --client-x {4} --client-y {5} --startup-log "{6}"',
        StrReplace(rodName, '"', ""),
        controlStat,
        lureSpeed,
        clientX,
        clientY,
        startupLogPath
    )
    try {
        Run(Format('py "{1}" {2}', handlerPath, args), A_ScriptDir)
    } catch {
        try Run(Format('python "{1}" {2}', handlerPath, args), A_ScriptDir)
        catch {
            logErrorCode("CEREBRA_HANDLER_LAUNCH_FAILED", "Unable to launch: " handlerPath, "ERROR")
            return false
        }
    }

    CEREBRA_HANDLER_LAUNCHED := true
    logEvent("Cerebra handler launched: " handlerPath, "STEP")
    return true
}

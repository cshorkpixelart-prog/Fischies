#Requires AutoHotkey v2.0

LOGGER_INITIALIZED := false
LOGGER_ENABLED := true
LOGGER_FILE_PATH := ""
LOGGER_ERROR_FILE_PATH := ""
LOGGER_LOG_STATUS_UPDATES := true
LOGGER_SHOW_ERROR_TOOLTIP := true
LOGGER_ERROR_TOOLTIP_ID := 19
LOGGER_ERRORS_ONLY := true

initLogger() {
    global LOGGER_INITIALIZED, LOGGER_ENABLED, LOGGER_FILE_PATH, LOGGER_ERROR_FILE_PATH, LOGGER_LOG_STATUS_UPDATES, LOGGER_SHOW_ERROR_TOOLTIP, LOGGER_ERRORS_ONLY

    if LOGGER_INITIALIZED
        return LOGGER_ENABLED

    LOGGER_INITIALIZED := true
    LOGGER_ENABLED := parseLoggerBool(getLoggerConfigValue("LogEnabled", "true"), true)
    LOGGER_LOG_STATUS_UPDATES := parseLoggerBool(getLoggerConfigValue("LogStatusUpdates", "true"), true)
    LOGGER_SHOW_ERROR_TOOLTIP := parseLoggerBool(getLoggerConfigValue("ShowErrorCodeTooltip", "true"), true)
    LOGGER_ERRORS_ONLY := parseLoggerBool(getLoggerConfigValue("LogErrorsOnly", "true"), true)
    basePath := resolveLoggerPath(getLoggerConfigValue("LogFilePath", "logs\macro.log"))
    errorPath := resolveLoggerPath(getLoggerConfigValue("LogErrorFilePath", "logs\errors.log"))
    LOGGER_FILE_PATH := buildSessionLogPath(basePath)
    LOGGER_ERROR_FILE_PATH := errorPath

    if !LOGGER_ENABLED
        return false

    try {
        dirPath := getParentDirectory(LOGGER_FILE_PATH)
        if dirPath != "" && !DirExist(dirPath)
            DirCreate(dirPath)
        errorDirPath := getParentDirectory(LOGGER_ERROR_FILE_PATH)
        if errorDirPath != "" && !DirExist(errorDirPath)
            DirCreate(errorDirPath)
        OnExit(logMacroExit)
        OnError(logUnhandledException)
        appendLogLine("INFO", "Logger initialized. Path=" LOGGER_FILE_PATH)
    } catch {
        LOGGER_ENABLED := false
        return false
    }

    return true
}

logEvent(message, level := "INFO") {
    global LOGGER_INITIALIZED, LOGGER_ENABLED, LOGGER_ERRORS_ONLY

    if !LOGGER_INITIALIZED
        initLogger()
    if !LOGGER_ENABLED
        return
    if LOGGER_ERRORS_ONLY && !isErrorLevel(level)
        return

    appendLogLine(level, message)
}

logErrorCode(errorKey, details := "", level := "ERROR") {
    global LOGGER_ERRORS_ONLY

    if LOGGER_ERRORS_ONLY
        level := "ERROR"

    code := getErrorCodeValue(errorKey)
    description := getErrorCodeDescription(errorKey)
    message := "[" code "] " description
    if details != ""
        message .= " | " sanitizeLogMessage(details)
    logEvent(message, level)
    appendErrorLine(code, description, details, level)
    showErrorCodeTooltip(code)
}

logErrorFromException(errorKey, err, prefix := "") {
    details := prefix
    try {
        if err.HasOwnProp("Message") && err.Message != "" {
            if details = ""
                details := err.Message
            else
                details := details ": " err.Message
        }
    }
    try {
        if err.HasOwnProp("Line") && err.Line
            details .= " (L" err.Line ")"
    }
    logErrorCode(errorKey, details = "" ? "Exception raised without details." : details)
}

logStatus(message) {
    global LOGGER_LOG_STATUS_UPDATES, LOGGER_ERRORS_ONLY

    if LOGGER_ERRORS_ONLY
        return
    if !LOGGER_LOG_STATUS_UPDATES
        return

    if message = ""
        logEvent("<status-clear>", "STATUS")
    else
        logEvent(message, "STATUS")
}

logMacroExit(exitReason, exitCode) {
    appendLogLine("INFO", "Macro exiting. reason=" exitReason " code=" exitCode)
}

logUnhandledException(err, mode) {
    details := "Unhandled exception."
    try {
        if err.HasOwnProp("Message") && err.Message != ""
            details := err.Message
    }
    try {
        if err.HasOwnProp("Line") && err.Line
            details .= " (L" err.Line ")"
    }
    logErrorCode("UNHANDLED_EXCEPTION", details " mode=" mode)
    return false
}

clearSessionLog() {
    global LOGGER_INITIALIZED, LOGGER_ENABLED, LOGGER_FILE_PATH

    if !LOGGER_INITIALIZED
        initLogger()
    if !LOGGER_ENABLED
        return false

    try {
        file := FileOpen(LOGGER_FILE_PATH, "w", "UTF-8")
        file.Close()
        return true
    } catch {
        return false
    }
}

appendLogLine(level, message) {
    global LOGGER_FILE_PATH

    cleanMessage := sanitizeLogMessage(message)
    stamp := FormatTime(A_Now, "yyyy-MM-dd HH:mm:ss")
    line := stamp " [" level "] " cleanMessage "`n"
    try FileAppend(line, LOGGER_FILE_PATH, "UTF-8")
}

appendErrorLine(code, description, details, level := "ERROR") {
    global LOGGER_ERROR_FILE_PATH

    stamp := FormatTime(A_Now, "yyyy-MM-dd HH:mm:ss")
    message := stamp " [" level "] [" code "] " description
    if details != ""
        message .= " | " sanitizeLogMessage(details)
    message .= "`n"
    try FileAppend(message, LOGGER_ERROR_FILE_PATH, "UTF-8")
}

showErrorCodeTooltip(code) {
    global LOGGER_SHOW_ERROR_TOOLTIP, LOGGER_ERROR_TOOLTIP_ID

    if !LOGGER_SHOW_ERROR_TOOLTIP
        return

    ToolTip("Error " code, 12, 44, LOGGER_ERROR_TOOLTIP_ID)
    SetTimer(clearErrorCodeTooltip, -1800)
}

clearErrorCodeTooltip() {
    global LOGGER_ERROR_TOOLTIP_ID
    ToolTip("", , , LOGGER_ERROR_TOOLTIP_ID)
}

sanitizeLogMessage(text) {
    normalized := "" text
    normalized := StrReplace(normalized, "`r", " ")
    normalized := StrReplace(normalized, "`n", " | ")
    return Trim(normalized)
}

resolveLoggerPath(pathValue) {
    path := Trim(pathValue)
    if path = ""
        path := "logs\macro.log"

    if !isAbsoluteWindowsPath(path)
        path := A_ScriptDir "\" path

    return path
}

buildSessionLogPath(basePath) {
    stamp := FormatTime(A_Now, "yyyyMMdd-HHmmss")
    SplitPath(basePath, &fileName, &dir, &ext, &nameNoExt)

    if dir = ""
        dir := A_ScriptDir "\logs"
    if nameNoExt = ""
        nameNoExt := "macro"
    if ext = ""
        ext := "log"

    return dir "\" nameNoExt "-" stamp "." ext
}

isAbsoluteWindowsPath(path) {
    if RegExMatch(path, "i)^[A-Z]:\\")
        return true
    return SubStr(path, 1, 1) = "\"
}

getParentDirectory(path) {
    splitPos := InStr(path, "\", , -1)
    if splitPos <= 1
        return ""
    return SubStr(path, 1, splitPos - 1)
}

getLoggerConfigValue(keyName, defaultValue := "") {
    try return getInfoConfigValue(keyName, defaultValue)
    catch
        return defaultValue
}

parseLoggerBool(value, fallback := false) {
    text := StrLower(Trim("" value))
    if text = "1" || text = "true" || text = "on" || text = "yes"
        return true
    if text = "0" || text = "false" || text = "off" || text = "no"
        return false
    return fallback
}

isErrorLevel(level) {
    value := StrUpper(Trim("" level))
    return value = "ERROR"
}

getErrorCodeValue(errorKey) {
    static codes := Map(
        "UNHANDLED_EXCEPTION", "E000",
        "ROBLOX_WINDOW_NOT_FOUND", "E100",
        "DISPLAY_SCALING_INVALID", "E101",
        "RESIZE_WINDOW_NOT_FOUND", "E102",
        "DISABLE_RESIZE_WINDOW_NOT_FOUND", "E103",
        "SETUP_INCOMPLETE", "E200",
        "SHAKE_EXCEPTION", "E201",
        "SHAKE_NO_RESULT", "E202",
        "CATCH_EXCEPTION", "E203",
        "ROD_EQUIP_NOT_DETECTED", "E300",
        "ROD_EQUIP_CHECK_EXCEPTION", "E301",
        "SERVER_SYNC_FAILED", "E400",
        "SERVER_SYNC_INVALID_RESPONSE", "E401",
        "SERVER_BASE_URL_EMPTY", "E402",
        "SERVER_REQUEST_EXCEPTION", "E403",
        "FEEDBACK_SERVER_UNREACHABLE", "E404",
        "LOGGER_UNKNOWN", "E999"
    )
    key := StrUpper(Trim("" errorKey))
    if codes.Has(key)
        return codes[key]
    return codes["LOGGER_UNKNOWN"]
}

getErrorCodeDescription(errorKey) {
    static descriptions := Map(
        "UNHANDLED_EXCEPTION", "Unhandled exception.",
        "ROBLOX_WINDOW_NOT_FOUND", "Roblox window was not found.",
        "DISPLAY_SCALING_INVALID", "Display scaling is not 100%.",
        "RESIZE_WINDOW_NOT_FOUND", "Resize failed because Roblox window was not found.",
        "DISABLE_RESIZE_WINDOW_NOT_FOUND", "Disable-resize failed because Roblox window was not found.",
        "SETUP_INCOMPLETE", "Macro start requested before setup was complete.",
        "SHAKE_EXCEPTION", "An exception occurred during shaking.",
        "SHAKE_NO_RESULT", "Shake stage ended without a confirmed shake result.",
        "CATCH_EXCEPTION", "An exception occurred during catching.",
        "ROD_EQUIP_NOT_DETECTED", "Rod equip check did not confirm equipped state.",
        "ROD_EQUIP_CHECK_EXCEPTION", "Rod equip verification threw an exception.",
        "SERVER_SYNC_FAILED", "Server sync request failed or returned empty response.",
        "SERVER_SYNC_INVALID_RESPONSE", "Server sync response was invalid.",
        "SERVER_BASE_URL_EMPTY", "Server base URL was empty.",
        "SERVER_REQUEST_EXCEPTION", "Server request threw an exception.",
        "FEEDBACK_SERVER_UNREACHABLE", "Feedback endpoint was unreachable; fallback was used.",
        "LOGGER_UNKNOWN", "Unknown or uncategorized error."
    )
    key := StrUpper(Trim("" errorKey))
    if descriptions.Has(key)
        return descriptions[key]
    return descriptions["LOGGER_UNKNOWN"]
}

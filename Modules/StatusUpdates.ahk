#Requires AutoHotkey v2.0

updateStatus(message) {
    global LAST_STATUS_MESSAGE
    LAST_STATUS_MESSAGE := message
    logStatus(message)
    try WinSetTitle(message, "ahk_exe RobloxPlayerBeta.exe")
    if message = ""
        ToolTip("", , , 20)
    else
        ToolTip(message, 12, 12, 20)
}

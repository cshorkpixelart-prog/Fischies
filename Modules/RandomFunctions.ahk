#Requires AutoHotkey v2.0

activateRoblox() {
    try {
        WinActivate "ahk_exe RobloxPlayerBeta.exe"
    } catch {
        try logErrorCode("ROBLOX_WINDOW_NOT_FOUND", "activateRoblox() could not find Roblox window.")
        MsgBox "Roblox window not found.", MACRO_TITLE, 16
        ExitApp
    }
    Sleep 10
}

checkDisplayScaling() {
    if A_ScreenDPI == 96
        return

    try logErrorCode("DISPLAY_SCALING_INVALID", "Detected DPI=" A_ScreenDPI ".")
    Msgbox "Display scaling must be 100%.`nUpdate in Windows display settings.", "Rank Quests", 0x30
    ExitApp
}

ZoomInAndZoomOut() {
    activateRoblox()

    Sleep 100

    loop 25 {
        Send "{Wheelup}"
    }
    
    Sleep 50

    loop 1 {
        Send "{Wheeldown}"    
    }
}

changeGraphicsSettings() {
    activateRoblox()
    
    Send "{shift down}"
    Loop 15 {
        Send "{f10}"
        Sleep 100
    }
    Send "{shift up}"

    Loop 4 {
        Send "{f10}"
        Sleep 100
    }
}

disableResizing() {
    ; Get the window handle for the specified title
    hWnd := WinExist("ahk_exe RobloxPlayerBeta.exe")
    if !hWnd {
        try logErrorCode("DISABLE_RESIZE_WINDOW_NOT_FOUND", "disableResizing() could not find Roblox window.", "WARN")
        MsgBox "Roblox window not found!"
        return
    }

    ; Get the current window style
    style := DllCall("GetWindowLongPtr", "Ptr", hWnd, "Int", -16, "Int64")
    
    ; Remove the WS_SIZEBOX, WS_MAXIMIZEBOX, and WS_MINIMIZEBOX styles
    newStyle := style & ~0x00040000  ; WS_SIZEBOX (resizing border)
    newStyle := newStyle & ~0x00010000  ; WS_MAXIMIZEBOX (maximize button)
    newStyle := newStyle & ~0x00020000  ; WS_MINIMIZEBOX (minimize button)

    ; Apply the new style to the window
    DllCall("SetWindowLongPtr", "Ptr", hWnd, "Int", -16, "Int64", newStyle)

    ; Force the window to update and redraw
    DllCall("SetWindowPos", "Ptr", hWnd, "Ptr", 0, "Int", 0, "Int", 0, "Int", 0, "Int", 0, "UInt", 0x27)
}

resizeRobloxWindow() {
    updateStatus("Resizing the Roblox window.")

    try {
        windowHandle := WinGetID("ahk_exe RobloxPlayerBeta.exe")
    } catch {
        try logErrorCode("RESIZE_WINDOW_NOT_FOUND", "resizeRobloxWindow() could not find Roblox window.")
        MsgBox "Roblox window not found.", MACRO_TITLE, 16
        ExitApp
    }

    WinActivate windowHandle
    WinRestore windowHandle
    WinMove , , 800, 600, windowHandle 
    updateStatus("")
}

updateTrayIcon() {
    ;TraySetIcon ICON_FOLDER ICON_MAP["Application"].icon 
}

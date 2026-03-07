#Requires AutoHotkey v2.0

; Pixel checks.
CHAT_MESSAGE_COUNTER_PIXEL := {x: 153, y: 30, colour: "0xffffff"}
CHAT_MESSAGE_ENABLED_PIXEL := {x: 130, y: 35, colour: "0xf8f8f9"}

; Screen clicks.
CHAT_MESSAGE_BUTTON := {x: 137, y: 32}

; Detects if the chat menu is enabled or opened, and disables it.
closeChatMenu() {
    button := CHAT_MESSAGE_BUTTON
    updateStatus("Closing chat menu.")

    if isChatMessageCounter() {
        updateStatus("Closing the chat menu.")
        Loop 25 {
            SendEvent "{Click, " button.x ", " button.y ", 1}"
            Sleep 10
            if !isChatMessageCounter()
                break
        }
        updateStatus("")
    }

    Loop 3 {
        if isChatMessageEnabled() {
            updateStatus("Closing the chat menu.")
            Loop 25 {
                SendEvent "{Click, " button.x ", " button.y ", 1}"
                Sleep 10
                if !isChatMessageEnabled()
                    break
            }        
            updateStatus("")
        }
        Sleep 100
    }
    
    updateStatus("")
}

; Checks if there is a chat menu has a message counter.
isChatMessageCounter() {
    pixel := CHAT_MESSAGE_COUNTER_PIXEL
    activateRoblox()
    return PixelSearch(&X, &Y, pixel.x, pixel.y, pixel.x, pixel.y, pixel.colour, 2)        
}

; Checks if the chat menu is enabled (highlighted white).
isChatMessageEnabled() {
    pixel := CHAT_MESSAGE_ENABLED_PIXEL
    activateRoblox()
    return PixelSearch(&X, &Y, pixel.x, pixel.y, pixel.x, pixel.y, pixel.colour, 2)    
}
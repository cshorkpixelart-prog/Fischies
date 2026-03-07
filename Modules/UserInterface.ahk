#Requires AutoHotkey v2.0

UI_CAMERA_ICON_PIXEL := {x: 771, y: 36, colour: "0xeaecee"}
UI_BACKPACK_PIXEL := {x: 535, y: 266, colour: "0xd1d3d5"}
UI_ROD_PIXEL := {x: 169, y: 564, colour: "0xD9D8DD"}

UI_CAMERA_ICON_BUTTON := {x: 766, y: 34}

hideUserInterface() {
    updateStatus("Hiding user interface.")

    if isUserInterfaceDisplayed() {
        button := UI_CAMERA_ICON_BUTTON
        Loop {
            SendEvent "{Click, " button.x ", " button.y ", 1}"
            Sleep 10
            if !isUserInterfaceDisplayed()
                break
        }
    }  
    
    updateStatus("")
}

showUserInterface() {
    if !isUserInterfaceDisplayed() {
        button := UI_CAMERA_ICON_BUTTON
        Loop {
            SendEvent "{Click, " button.x ", " button.y ", 1}"
            Sleep 10
            if isUserInterfaceDisplayed()
                break
        }
    }    
}

isUserInterfaceDisplayed() {
    pixel := UI_CAMERA_ICON_PIXEL
    activateRoblox()
    return PixelSearch(&X, &Y, pixel.x, pixel.y, pixel.x, pixel.y, pixel.colour, 2)        
}

closeBackpack() {
    updateStatus("Closing backpack.")

    if isBackpackOpen() {
        Loop {
            Send "{~}"
            Sleep 10
            if !isBackpackOpen()
                break
        }
    }

    updateStatus("")
}

isBackpackOpen() {
    pixel := UI_BACKPACK_PIXEL
    activateRoblox()
    return PixelSearch(&X, &Y, pixel.x, pixel.y, pixel.x, pixel.y, pixel.colour, 2)        
}

equipRod() {
    updateStatus("Equipping rod.")

    if !isRodEquipped() {
        Loop {
            Send "{1}"
            Sleep 10
            if isRodEquipped()
                break
        }
    }     

    updateStatus("")
}


isRodEquipped() {
    pixel := UI_ROD_PIXEL
    activateRoblox()
    return PixelSearch(&X, &Y, pixel.x, pixel.y, pixel.x, pixel.y, pixel.colour, 2)     
}

' Silent starter for Kiro Allow Clicker tray app.
' Runs pythonw (no black window). Double-click to start the tool.
' Works from any folder -- it uses its OWN location, so no fixed path.
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = folder
' 0 = hidden window, False = do not wait
shell.Run "pythonw.exe """ & folder & "\tray_app.py""", 0, False

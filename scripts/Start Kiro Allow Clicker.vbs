' Silent starter for Kiro Allow Clicker tray app.
' Runs pythonw (no black window). Double-click to start the tool.
' Works from any folder -- it uses its OWN location, so no fixed path.
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
scriptsDir = fso.GetParentFolderName(WScript.ScriptFullName)
repoRoot = fso.GetParentFolderName(scriptsDir)
srcDir = fso.BuildPath(repoRoot, "src")
shell.CurrentDirectory = srcDir
' 0 = hidden window, False = do not wait
shell.Run "pythonw.exe """ & fso.BuildPath(srcDir, "tray_app.py") & """", 0, False

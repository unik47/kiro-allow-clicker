# Adds a Startup-folder shortcut so the tray app auto-starts at login.
# Works on any machine: it finds its own folder, no fixed path.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbs = Join-Path $here 'Start Kiro Allow Clicker.vbs'

$ws = New-Object -ComObject WScript.Shell
$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startup 'Kiro Allow Clicker.lnk'
$lnk = $ws.CreateShortcut($shortcutPath)
$lnk.TargetPath = 'wscript.exe'
$lnk.Arguments = '"' + $vbs + '"'
$lnk.WorkingDirectory = $here
$lnk.Description = 'Starts Kiro Allow Clicker in the background'
$lnk.Save()

Write-Output ('Shortcut created at: ' + $shortcutPath)
if (Test-Path $shortcutPath) { Write-Output 'VERIFIED: auto-start is set.' } else { Write-Output 'ERROR: shortcut missing.' }

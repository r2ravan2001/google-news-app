Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

currentDir = WshShell.CurrentDirectory

' 1. Check if setup has been done; if not, install requirements quietly
If Not fso.FileExists(currentDir & "\.installed") Then
    WshShell.Run "cmd /c pip install -r requirements.txt", 0, True
    
    ' Create a flag file so setup only runs once
    Set flagFile = fso.CreateTextFile(currentDir & "\.installed", True)
    flagFile.WriteLine("installed")
    flagFile.Close
End If

' 2. Silently start Python backend in the background
WshShell.Run "cmd /c python app.py", 0, False

' 3. Wait 2 seconds for Flask server to initialize
WScript.Sleep 2000

' 4. Open index.html directly inside Google Chrome
WshShell.Run "chrome.exe " & Chr(34) & currentDir & "\index.html" & Chr(34)
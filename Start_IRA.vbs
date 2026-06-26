Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d C:\Users\hp\IRA\frontend && npm run desktop -- --start-minimized", 0, False

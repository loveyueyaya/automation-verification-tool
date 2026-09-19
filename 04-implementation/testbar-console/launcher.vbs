Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
cmd = """C:\Program Files\Python313\pythonw.exe"" """ & dir & "\testbar.py"""
ws.Run cmd, 0, False

Set WshShell = CreateObject("WScript.Shell")
' Obter o diretório onde este ficheiro VBS reside
strPath = WshShell.CurrentDirectory

' Executar pythonw.exe sem abrir qualquer janela de consola (janela oculta = 0)
WshShell.Run "pythonw.exe run.py --daemon", 0, False

Set WshShell = CreateObject("WScript.Shell") 
WshShell.Run "cmd /c cd /d ""C:\Users\stitch77\Desktop\Project\nba-predict-algorithm"" && python scripts\daily_update.py >> logs\daily_update.log 2>&1", 0, False 

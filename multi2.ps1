# start_distributed_servers.ps1 (Versión Final Explícita)

# Obtiene la ruta absoluta de la carpeta donde está este script .ps1
$basePath = (Get-Item -Path ".\" -Verbose).FullName

# --- Definimos explícitamente la ruta al script principal ---
$distributedScript = Join-Path $basePath 'server_distributed.py'

# --- Lanzamos cada proceso con su argumento específico ---
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$distributedScript`" SERVER1"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$distributedScript`" SERVER_MARCO"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$distributedScript`" server_dan"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$distributedScript`" server_gus"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$distributedScript`" server_christian"

Write-Host "Lanzados los servidores distribuidos."
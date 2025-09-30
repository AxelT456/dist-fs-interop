# start_dns_servers.ps1 (Versión Final Corregida)

# Obtiene la ruta absoluta de la carpeta donde está este script .ps1
$basePath = (Get-Item -Path ".\" -Verbose).FullName

# --- Definimos explícitamente cada script y cada carpeta ---
$dnsGeneralScript = Join-Path $basePath 'dns_general.py'

$serverNombresScript = Join-Path $basePath 'servidor_nombres.py'
$folderServer1 = Join-Path $basePath 'archivos_server1'

$serverDanScript = Join-Path $basePath 'servidor_dan.py'

# --- CAMBIO PARA MARCO: Definimos su carpeta ---
$serverMarcoScript = Join-Path $basePath 'server_marco.py'
$folderMarco = Join-Path $basePath 'archivos_server_marco'

# --- CAMBIO PARA CHRISTIAN: Corregimos el nombre de su carpeta a 'archivos_server2' ---
$serverChristianScript = Join-Path $basePath 'servidor_christian.py'
$folderChristian = Join-Path $basePath 'archivos_server_christian'

$serverGusScript = Join-Path $basePath 'servidor_gus.py'
$folderGus = Join-Path $basePath 'archivos_server_gus'


# --- Lanzamos cada proceso con su comando específico ---
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$dnsGeneralScript`""
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$serverNombresScript`" `"$folderServer1`""
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$serverDanScript`""
# --- CAMBIO: Le pasamos la ruta a Marco como argumento ---
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$serverMarcoScript`" `"$folderMarco`""
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$serverChristianScript`" `"$folderChristian`""
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python `"$serverGusScript`" `"$folderGus`""

Write-Host "Lanzados los servidores DNS."
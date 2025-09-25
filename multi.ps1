# Obtiene la ruta absoluta de la carpeta donde está este script .ps1
$basePath = Split-Path -Parent $MyInvocation.MyCommand.Definition

$commands = @(
  "python $(Join-Path $basePath 'dns_general.py')",
  "python $(Join-Path $basePath 'servidor_nombres.py')",
  "python $(Join-Path $basePath 'servidor_dan.py')",
  "python $(Join-Path $basePath 'server_marco.py')",
  "cmd /c echo $(Join-Path $basePath 'archivos_server2') | python $(Join-Path $basePath 'servidor_christian.py')",
  "cmd /c echo $(Join-Path $basePath 'archivos_server_gus') | python $(Join-Path $basePath 'servidor_gus.py')"
)

foreach ($c in $commands) {
  Start-Process -FilePath 'powershell.exe' -ArgumentList "-NoExit","-Command",$c
}

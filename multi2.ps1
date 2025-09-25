# Carpeta donde está este script .ps1 (tu repo dist-fs-interop)
$basePath = Split-Path -Parent $MyInvocation.MyCommand.Definition

$commands = @(
  "python $(Join-Path $basePath 'server_distributed.py') server1",
  "python $(Join-Path $basePath 'server_distributed.py') server2",
  "python $(Join-Path $basePath 'server_distributed.py') server_dan",
  "python $(Join-Path $basePath 'server_distributed.py') server_gus",
  "python $(Join-Path $basePath 'server_distributed.py') server_marco"
)

foreach ($c in $commands) {
  Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$c
}

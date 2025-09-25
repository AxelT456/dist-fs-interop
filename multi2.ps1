$commands = @(
  "python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\server_distributed.py server1",
  "python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\server_distributed.py server2",
  "python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\server_distributed.py server_dan",
  "python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\server_distributed.py server_gus",
  "python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\server_distributed.py server_marco"
)

foreach ($c in $commands) {
  Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$c
}

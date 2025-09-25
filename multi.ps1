$commands = @(
  "python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\dns_general.py",
  "python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\servidor_nombres.py",
  "python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\servidor_dan.py",
  "python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\server_marco.py",
  "cmd /c echo C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\archivos_server2 | python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\servidor_christian.py",
  "cmd /c echo C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\archivos_server_gus | python C:\Users\marco\OneDrive\Desktop\Archivosv1\gits\dist-fs-interop\servidor_gus.py"
)

foreach ($c in $commands) {
  Start-Process -FilePath 'powershell.exe' -ArgumentList "-NoExit","-Command",$c
}

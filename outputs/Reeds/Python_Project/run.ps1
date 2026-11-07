$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m pip install -r requirements.txt
New-Item -ItemType Directory -Force tools,plugins | Out-Null
if (!(Test-Path tools/python32/python.exe)) {
 Invoke-WebRequest https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-win32.zip -OutFile tools/python32.zip
 Expand-Archive tools/python32.zip tools/python32 -Force
}
foreach($name in @('Mini_DiZi','Mini_ErHu')) {
 if (!(Test-Path ('plugins/'+$name+'.dll'))) {
  Invoke-WebRequest ('https://www.chineekong.com/free/'+$name+'.rar') -OutFile ('tools/'+$name+'.rar')
  & C:/Windows/System32/tar.exe -xf ('tools/'+$name+'.rar') -C plugins
 }
}
python arrange_reeds.py
& tools/python32/python.exe vst_host.py plugins/Mini_DiZi.dll xiao_plan.json xiao.wav
& tools/python32/python.exe vst_host.py plugins/Mini_ErHu.dll erhu_plan.json erhu.wav
python render_reeds.py

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
python arrange_fusion.py
$plans=Get-Content native_plans.json -Raw | ConvertFrom-Json
foreach($plan in $plans) {
 $dll=if($plan.kind -eq 'wind'){'plugins/Mini_DiZi.dll'}else{'plugins/Mini_ErHu.dll'}
 & tools/python32/python.exe vst_host.py $dll ($plan.name+'.json') ($plan.name+'.wav')
}
python render_fusion.py

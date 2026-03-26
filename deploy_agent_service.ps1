$ErrorActionPreference = "Stop"
$NSSM_ZIP = "nssm-2.24.zip"
$NSSM_URL = "https://nssm.cc/release/nssm-2.24.zip"
$PWD = Get-Location

If (-Not (Test-Path "$PWD\nssm-2.24")) {
    Write-Host "Descargando NSSM desde $NSSM_URL ..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $NSSM_URL -OutFile $NSSM_ZIP
    Write-Host "Descomprimiendo NSSM..."
    Expand-Archive -Path $NSSM_ZIP -DestinationPath $PWD -Force
}

$NSSM_EXE = "$PWD\nssm-2.24\win64\nssm.exe"
$PYTHON_EXE = "$PWD\venv\Scripts\python.exe"
$SCRIPT_PATH = "$PWD\agent_sync.py"
$SERVICE_NAME = "RestBarSyncAgent_BAR_LOVE"

Write-Host "Instalando servicio de Windows: $SERVICE_NAME ..."
# Si el servicio ya existe, lo quitamos para reinstalarlo
$serviceExists = Get-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue
if ($serviceExists) {
    Write-Host "El servicio ya existe. Deteniendo y actualizando..."
    Stop-Service $SERVICE_NAME -ErrorAction SilentlyContinue
    & $NSSM_EXE stop $SERVICE_NAME
    & $NSSM_EXE remove $SERVICE_NAME confirm
}

& $NSSM_EXE install $SERVICE_NAME $PYTHON_EXE $SCRIPT_PATH
& $NSSM_EXE set $SERVICE_NAME AppDirectory $PWD
& $NSSM_EXE set $SERVICE_NAME AppStdout "$PWD\agent_stdout.log"
& $NSSM_EXE set $SERVICE_NAME AppStderr "$PWD\agent_sync_error.log"
& $NSSM_EXE set $SERVICE_NAME Start SERVICE_AUTO_START

Write-Host "========================================="
Write-Host "¡Servicio instalado correctamente!"
Write-Host "Para iniciar el Agente ejecuta:"
Write-Host "Start-Service $SERVICE_NAME"
Write-Host "========================================="

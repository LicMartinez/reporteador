#define MyAppName "Dashboard Sync SW"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "Swiss Tools"
#define MyAppURL "https://github.com/LicMartinez/reporteador"
#define MyAppExeName "DashboardSyncSW.exe"

[Setup]
AppId={{A1E8F5B2-8C4D-4E6A-9B1C-2D3E4F506172}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppComments=Sincroniza ventas locales (DBF RestBar) con el API del dashboard: detalles con costo (COSVEN), propinas (TIPS), pagos y meseros. No incluye conexion directa a Supabase.
DefaultDirName={autopf64}\{#MyAppName}
DisableProgramGroupPage=no
OutputDir=..\..\output_installer
OutputBaseFilename=DashboardSyncSW-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; x64compatible: 64-bit Windows (recomendado Inno Setup 6.7+; x64 está deprecado)
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\icono_sincronizador.ico
SetupIconFile=assets\icono_sincronizador.ico
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Instalador {#MyAppName}
VersionInfoProductName={#MyAppName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Icono en el escritorio publico (todos los usuarios) — Configuracion"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "..\..\dist\DashboardSyncSW.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\DashboardSyncSWConfig.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\icono_sincronizador.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}\Configuracion {#MyAppName}"; Filename: "{app}\DashboardSyncSWConfig.exe"; IconFilename: "{app}\icono_sincronizador.ico"
Name: "{autoprograms}\{#MyAppName}\Carpeta datos (config y logs)"; Filename: "{sys}\explorer.exe"; Parameters: """{commonappdata}\DashboardSyncSW"""; IconFilename: "{app}\icono_sincronizador.ico"
Name: "{autoprograms}\{#MyAppName}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\icono_sincronizador.ico"
; Escritorio común: coherente con instalación en {autopf64} (admin) y evita UsedUserAreasWarning
Name: "{commondesktop}\{#MyAppName} Config"; Filename: "{app}\DashboardSyncSWConfig.exe"; IconFilename: "{app}\icono_sincronizador.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\DashboardSyncSWConfig.exe"; Description: "Abrir configuracion al terminar"; Flags: nowait postinstall skipifsilent


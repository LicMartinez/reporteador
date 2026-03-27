#define MyAppName "Dashboard Sync SW"
#define MyAppVersion "1.0.0"
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
AppComments=Sincroniza ventas locales (DBF RestBar) con el API del dashboard. No incluye conexion directa a Supabase.
DefaultDirName={autopf64}\{#MyAppName}
DisableProgramGroupPage=no
OutputDir=..\..\output_installer
OutputBaseFilename=DashboardSyncSW-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\icono_sincronizador.ico
SetupIconFile=assets\icono_sincronizador.ico
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Instalador {#MyAppName}
VersionInfoProductName={#MyAppName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear icono en el escritorio (Configuracion)"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "..\..\dist\DashboardSyncSW.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\DashboardSyncSWConfig.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\icono_sincronizador.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}\Configuracion {#MyAppName}"; Filename: "{app}\DashboardSyncSWConfig.exe"; IconFilename: "{app}\icono_sincronizador.ico"
Name: "{autoprograms}\{#MyAppName}\Carpeta datos (config y logs)"; Filename: "{sys}\explorer.exe"; Parameters: """{commonappdata}\DashboardSyncSW"""; IconFilename: "{app}\icono_sincronizador.ico"
Name: "{autoprograms}\{#MyAppName}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\icono_sincronizador.ico"
Name: "{userdesktop}\{#MyAppName} Config"; Filename: "{app}\DashboardSyncSWConfig.exe"; IconFilename: "{app}\icono_sincronizador.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\DashboardSyncSWConfig.exe"; Description: "Abrir configuracion al terminar"; Flags: nowait postinstall skipifsilent


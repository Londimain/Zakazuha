; Скрипт установщика для программы "Заказуха"
; Создан для сборки, выполненной через PyInstaller (файл Zakazuha.exe в папке dist)

#define MyAppName "Заказуха"
#define MyAppVersion "2.1.3"
#define MyAppPublisher "Энергослужба"
; ВАЖНО: Имя файла на английском, как его собрал PyInstaller
#define MyAppExeName "Zakazuha.exe" 

[Setup]
AppId={{B2C3D4E5-F6A7-8901-2345-6789ABCDEF01}
AppName={#MyAppName}
VersionInfoVersion={#MyAppVersion}.0
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
CloseApplications=force
RestartApplications=no
CloseApplicationsFilter={#MyAppExeName}


DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

OutputDir=installer_output
OutputBaseFilename=Zakazuha_Setup_v{#MyAppVersion}
SetupIconFile=ico\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=admin

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "ico\app.ico"; DestDir: "{app}\ico"; Flags: ignoreversion
Source: "version.json"; DestDir: "{app}"; Flags: ignoreversion  ;

[Dirs]
Name: "{app}"; Permissions: users-modify

[Icons]
; Ярлыки будут называться по-русски ({#MyAppName}), но ссылаться на английский файл ({#MyAppExeName})
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
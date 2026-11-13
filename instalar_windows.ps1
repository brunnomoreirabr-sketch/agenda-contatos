$ErrorActionPreference = 'Stop'
$source = $PSScriptRoot
$destination = Join-Path $env:LOCALAPPDATA 'Programs\AgendaContatos'
New-Item -ItemType Directory -Path $destination -Force | Out-Null
$exe = Join-Path $source 'AgendaContatos.exe'
if (Test-Path $exe) {
    Copy-Item $exe (Join-Path $destination 'AgendaContatos.exe') -Force
    $target = Join-Path $destination 'AgendaContatos.exe'
    $arguments = ''
} else {
    $python = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if (-not $python) { $python = Get-Command pyw.exe -ErrorAction SilentlyContinue }
    if (-not $python) {
        throw 'Instale o Python 3.10 ou superior em python.org ou baixe o pacote Windows com executavel na pagina Releases.'
    }
    Copy-Item (Join-Path $source 'agenda.py') $destination -Force
    Copy-Item (Join-Path $source 'agenda') $destination -Recurse -Force
    $target = $python.Source
    $arguments = '"' + (Join-Path $destination 'agenda.py') + '"'
}
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = $shell.CreateShortcut((Join-Path $desktop 'Agenda de Contatos.lnk'))
$shortcut.TargetPath = $target
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $destination
$shortcut.Description = 'Abrir a agenda de contatos'
$shortcut.Save()
Write-Host 'Agenda instalada. O atalho Agenda de Contatos foi criado na sua area de trabalho.'

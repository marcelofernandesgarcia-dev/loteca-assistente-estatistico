# Cria o atalho "Loteca - Assistente Estatistico" na Area de Trabalho e no Menu Iniciar
# do usuario atual, apontando para iniciar.pyw (abre sem janela preta).
# Nao mexe no registro e nao faz o app iniciar com o Windows. Para remover, apague os
# dois atalhos. Uso (na pasta do projeto):
#   powershell -ExecutionPolicy Bypass -File scripts\criar_atalhos.ps1
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $raiz '.venv\Scripts\pythonw.exe'
$lancador = Join-Path $raiz 'iniciar.pyw'
$icone = Join-Path $raiz 'app\icone.ico'
if (-not (Test-Path $pythonw)) { throw "Ambiente .venv nao encontrado em $raiz. Veja a secao 'Instalacao' do README." }

$shell = New-Object -ComObject WScript.Shell
$destinos = @(
    [Environment]::GetFolderPath('Desktop'),
    (Join-Path ([Environment]::GetFolderPath('Programs')) '')
)
foreach ($pasta in $destinos) {
    $caminho = Join-Path $pasta 'Loteca - Assistente Estatistico.lnk'
    $atalho = $shell.CreateShortcut($caminho)
    $atalho.TargetPath = $pythonw
    $atalho.Arguments = '"' + $lancador + '"'
    $atalho.WorkingDirectory = $raiz
    $atalho.Description = 'Loteca - Assistente Estatistico (uso pessoal, so neste computador)'
    if (Test-Path $icone) { $atalho.IconLocation = $icone }
    $atalho.Save()
    Write-Output "Atalho criado: $caminho"
}

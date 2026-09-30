# Espera a janela do app (Edge com o perfil proprio do Loteca) aparecer e, depois,
# todas as janelas desse perfil fecharem. Usado pelo iniciar.pyw: o Edge relanca o
# proprio processo ao abrir, entao esperar o processo iniciado nao serve (achado no
# teste de 30/09/2026). Saida: 0 = janelas fechadas; 2 = a janela nao apareceu a tempo.
param(
    [Parameter(Mandatory = $true)][string]$Perfil,
    [int]$SegundosParaAparecer = 60,
    [int]$Intervalo = 3
)
$ErrorActionPreference = 'Stop'
$marca = '*' + $Perfil + '*'

function Contar-Janelas {
    @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" |
        Where-Object { $_.CommandLine -like $marca -and $_.CommandLine -notlike '*--type=*' }).Count
}

$limite = (Get-Date).AddSeconds($SegundosParaAparecer)
while ((Contar-Janelas) -eq 0) {
    if ((Get-Date) -gt $limite) { exit 2 }
    Start-Sleep -Seconds 1
}
while ((Contar-Janelas) -gt 0) {
    Start-Sleep -Seconds $Intervalo
}
exit 0

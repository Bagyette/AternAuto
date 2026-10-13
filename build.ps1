param([string]$JdkDirectory = $env:JAVA_HOME)

$ErrorActionPreference = 'Stop'
if (-not $JdkDirectory -or -not (Test-Path -LiteralPath (Join-Path $JdkDirectory 'bin\javac.exe'))) {
    throw 'Indique le dossier du JDK 25 avec -JdkDirectory.'
}
$env:JAVA_HOME = $JdkDirectory
$env:PATH = (Join-Path $JdkDirectory 'bin') + ';' + $env:PATH
$env:JAVA_TOOL_OPTIONS = '-Djdk.net.unixdomain.tmpdir=C:/Windows/Temp'
Push-Location $PSScriptRoot
try {
    python tools/prepare_versions.py
    if ($LASTEXITCODE -ne 0) { throw 'Préparation échouée.' }
    & .\gradlew.bat formatJava assembleDistributions --console=plain --no-daemon
    if ($LASTEXITCODE -ne 0) { throw 'Compilation ou tests échoués.' }
    python tools/verify_compatibility.py
    if ($LASTEXITCODE -ne 0) { throw 'Vérification des versions échouée.' }
} finally {
    Pop-Location
}

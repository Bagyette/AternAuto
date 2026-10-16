param(
    [string]$JdkDirectory = $env:JAVA_HOME,
    [string[]]$Tasks = @('buildAll')
)

$ErrorActionPreference = 'Stop'
if (-not $JdkDirectory -or -not (Test-Path -LiteralPath (Join-Path $JdkDirectory 'bin\javac.exe'))) {
    throw 'Indique le dossier du JDK 25 avec -JdkDirectory.'
}
$previousJavaHome = $env:JAVA_HOME
$previousPath = $env:PATH
$previousOptions = $env:JAVA_TOOL_OPTIONS
Push-Location $PSScriptRoot
try {
    $env:JAVA_HOME = $JdkDirectory
    $env:PATH = (Join-Path $JdkDirectory 'bin') + ';' + $env:PATH
    $socketDirectory = Join-Path $PSScriptRoot '.tools\sockets'
    New-Item -ItemType Directory -Force -Path $socketDirectory | Out-Null
    $env:JAVA_TOOL_OPTIONS = '-Djdk.net.unixdomain.tmpdir=' + $socketDirectory.Replace('\', '/')
    $logPath = Join-Path $PSScriptRoot ('.tools\build-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
    & python -B (Join-Path $PSScriptRoot 'tools\run_bounded_build.py') --jdk $JdkDirectory --log $logPath @Tasks
    if ($LASTEXITCODE -ne 0) { throw 'Compilation ou verification incomplete.' }
} finally {
    $env:JAVA_HOME = $previousJavaHome
    $env:PATH = $previousPath
    $env:JAVA_TOOL_OPTIONS = $previousOptions
    Pop-Location
}

param(
    [Parameter(Mandatory=$true)]
    [string]$ConfigDir
)

$env:CLAUDE_CONFIG_DIR = (Resolve-Path $ConfigDir).Path
claude

param(
    [string]$cmd
)

if (-not $cmd) {
    Write-Error "Command parameter is empty."
    exit 1
}

# 1. Calculate SHA256 of the command (lowercase hex)
$cleanCmd = $cmd.TrimEnd("`r", "`n")
$bytes = [System.Text.Encoding]::UTF8.GetBytes($cleanCmd)
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$hashBytes = $sha256.ComputeHash($bytes)
$computedHash = [System.BitConverter]::ToString($hashBytes).Replace("-", "").ToLower()

# Write computed hash to a temporary log file in the global scratch directory
try {
    Set-Content -Path "C:\Users\Zaki\.gemini\antigravity\scratch\hash_log.txt" -Value "CMD: $cleanCmd | HASH: $computedHash" -ErrorAction Stop
} catch {
    # Ignore logging errors
}

$logPath = "C:\Users\Zaki\.gemini\antigravity\scratch\approved_commands.json"
if (-not (Test-Path $logPath)) {
    Write-Error "Approved commands log file not found at: $logPath"
    exit 1
}

# Patch process: load and convert timestamp to local JST (+09:00)
try {
    $json = Get-Content -Raw -Path $logPath -ErrorAction Stop
    $data = ConvertFrom-Json $json -ErrorAction Stop
} catch {
    Write-Error "Failed to load or parse JSON from $logPath : $_"
    exit 1
}

$now = [DateTimeOffset]::Now
$updated = $false

if ($data -and $data.approved_commands) {
    foreach ($item in $data.approved_commands) {
        if ($item.timestamp) {
            # Skip if already JST (+09:00)
            if ($item.timestamp -like "*+09:00*") {
                continue
            }
            try {
                $parsedTime = [DateTimeOffset]::Parse($item.timestamp)
                $jstTimeZone = [TimeZoneInfo]::FindSystemTimeZoneById("Tokyo Standard Time")
                $jstTime = [TimeZoneInfo]::ConvertTime($parsedTime, $jstTimeZone)
                
                # Safety check: skip if the converted time is in the future
                if ($jstTime -gt $now.AddMinutes(5)) {
                    continue
                }
                
                $newTimestamp = $jstTime.ToString("yyyy-MM-ddTHH:mm:ss.fffzzz")
                
                if ($item.timestamp -ne $newTimestamp) {
                    $item.timestamp = $newTimestamp
                    $updated = $true
                }
            } catch {
                # Skip parse error
            }
        }
    }
}

if ($updated) {
    try {
        $newJson = ConvertTo-Json $data -Depth 100
        Set-Content -Path $logPath -Value $newJson -ErrorAction Stop
    } catch {
        Write-Warning "Failed to save patched JSON to $logPath : $_"
    }
}

# 2. Check approved_commands list
$foundAndValid = $false

if ($data -and $data.approved_commands) {
    foreach ($item in $data.approved_commands) {
        $itemHash = $item.hash
        if (-not $itemHash) {
            $itemHash = $item.sha256
        }
        
        if ($itemHash -eq $computedHash) {
            if ($item.timestamp) {
                try {
                    $itemTime = [DateTimeOffset]::Parse($item.timestamp)
                    $diff = $now - $itemTime
                    $elapsedSeconds = $diff.TotalSeconds
                    
                    # Check if timestamp is within 5 minutes
                    if ($elapsedSeconds -ge -30 -and $elapsedSeconds -le 300) {
                        $foundAndValid = $true
                        break
                    }
                } catch {
                    Write-Warning "Failed to parse timestamp '$($item.timestamp)' for hash '$itemHash': $_"
                }
            }
        }
    }
}

# 3. Exit 0 if approved and valid, else exit 1
if ($foundAndValid) {
    Write-Host "Validation passed for command (hash: $computedHash)"
    exit 0
} else {
    Write-Error "Command validation failed: The command (hash: $computedHash) has not been approved or the approval has expired (exceeded 5 minutes)."
    exit 1
}

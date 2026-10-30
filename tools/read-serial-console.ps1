# Copy the phone's USB gadget serial console (ttyGS0) into a log file, and type
# commands into it: anything written to <logfile>.cmd is sent to the port and
# the file is deleted. Opens the COM port the moment it enumerates (output
# written before the port is open is lost) and reconnects across reboots.
# usage: powershell -File read-serial-console.ps1 <logfile> [timeoutSeconds]
param([string]$Log, [int]$Timeout = 900)

$cmdFile = "$Log.cmd"
$w = New-Object System.IO.StreamWriter($Log, $true)
$w.AutoFlush = $true
$w.WriteLine("=== reader start $(Get-Date -Format HH:mm:ss)")
$deadline = (Get-Date).AddSeconds($Timeout)

while ((Get-Date) -lt $deadline) {
    $port = [System.IO.Ports.SerialPort]::GetPortNames() | Select-Object -First 1
    if (-not $port) { Start-Sleep -Milliseconds 50; continue }

    $sp = New-Object System.IO.Ports.SerialPort $port, 115200, 'None', 8, 'One'
    $sp.DtrEnable = $true
    $sp.RtsEnable = $true
    $sp.NewLine = "`n"
    $sp.ReadBufferSize = 1048576
    try { $sp.Open() } catch { Start-Sleep -Milliseconds 50; continue }
    $w.WriteLine("`n=== OPENED $port at $(Get-Date -Format HH:mm:ss.fff)")
    try {
        while ((Get-Date) -lt $deadline) {
            if (Test-Path $cmdFile) {
                $cmd = Get-Content -Raw $cmdFile
                Remove-Item $cmdFile
                $sp.Write(($cmd -replace "`r", ""))
                $w.WriteLine("`n=== SENT: $($cmd.Trim())")
            }
            $data = $sp.ReadExisting()
            if ($data) { $w.Write($data) } else { Start-Sleep -Milliseconds 20 }
        }
    } catch {
        $w.WriteLine("`n=== CLOSED $port at $(Get-Date -Format HH:mm:ss.fff): $($_.Exception.Message)")
    }
    try { $sp.Close() } catch {}
}
$w.WriteLine("=== reader end $(Get-Date -Format HH:mm:ss)")
$w.Close()

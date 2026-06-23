Add-Type -AssemblyName System.Speech

function Write-IraSpeechEvent {
  param(
    [Parameter(Mandatory = $true)]
    [hashtable] $Event
  )

  $json = $Event | ConvertTo-Json -Compress
  [Console]::Out.WriteLine($json)
  [Console]::Out.Flush()
}

try {
  $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
  $grammar = New-Object System.Speech.Recognition.DictationGrammar
  $recognizer.LoadGrammar($grammar)
  $recognizer.SetInputToDefaultAudioDevice()
  $recognizer.BabbleTimeout = [TimeSpan]::FromSeconds(3)
  $recognizer.InitialSilenceTimeout = [TimeSpan]::FromSeconds(8)
  $recognizer.EndSilenceTimeout = [TimeSpan]::FromMilliseconds(900)
  $recognizer.EndSilenceTimeoutAmbiguous = [TimeSpan]::FromMilliseconds(1400)

  Write-IraSpeechEvent @{
    type = "status"
    status = "NATIVE LISTENING"
  }

  while ($true) {
    $result = $recognizer.Recognize([TimeSpan]::FromSeconds(12))

    if ($null -eq $result) {
      Write-IraSpeechEvent @{
        type = "status"
        status = "NATIVE LISTENING"
      }
      continue
    }

    $text = ""
    if ($null -ne $result.Text) {
      $text = $result.Text.Trim()
    }
    if ($text.Length -eq 0) {
      continue
    }

    Write-IraSpeechEvent @{
      type = "transcript"
      text = $text
      confidence = [Math]::Round($result.Confidence, 3)
    }
  }
}
catch {
  Write-IraSpeechEvent @{
    type = "error"
    error = $_.Exception.Message
  }
  exit 1
}
finally {
  if ($null -ne $recognizer) {
    $recognizer.Dispose()
  }
}

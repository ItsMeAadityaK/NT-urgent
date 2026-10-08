# Adds what pptxgenjs cannot: slide transitions, entrance and emphasis animations, clickable navigation and
# demo links, and the hidden backup slides. Run after build_deck.js:
#   powershell -ExecutionPolicy Bypass -File presentation\polish_deck.ps1
param(
  [string]$Raw = (Join-Path $PSScriptRoot "NT-Triage-Deck.raw.pptx"),
  [string]$Out = (Join-Path $PSScriptRoot "NT-Triage-Deck.pptx"),
  [string]$Shots = ""
)
$ErrorActionPreference = "Stop"
$plan = Get-Content (Join-Path $PSScriptRoot "animations.json") -Raw | ConvertFrom-Json
$base = "http://127.0.0.1:5050/"

$effects = @{ fade = 10; wipe = 22; zoom = 23; pulse = 59 }       # msoAnimEffect ids
$triggers = @{ click = 1; with = 2; after = 3 }                    # msoAnimTrigger ids

$app = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open($Raw, 0, 0, 0)
$problems = @()

# ---- transitions: a soft fade on every slide
foreach ($sl in $pres.Slides) {
  $sl.SlideShowTransition.EntryEffect = 3849          # ppEffectFadeSmoothly
  $sl.SlideShowTransition.Duration = 0.6
  $sl.SlideShowTransition.AdvanceOnClick = -1
}

# ---- animations from the plan
foreach ($prop in $plan.PSObject.Properties) {
  $idx = [int]$prop.Name
  $sl = $pres.Slides.Item($idx)
  $seq = $sl.TimeLine.MainSequence
  foreach ($e in $prop.Value) {
    try {
      $shape = $sl.Shapes.Item($e.name)
      $trig = $triggers[$e.trigger]
      $eff = $seq.AddEffect($shape, $effects[$e.effect], 0, $trig)
      $eff.Timing.Duration = [single]$e.dur
      $eff.Timing.TriggerDelayTime = [single]$e.delay
      if ($e.effect -eq "wipe" -and ($e.name -like "Arrow*" -or $e.name -eq "Results chart" -or $e.name -eq "Raise arrow")) {
        $eff.EffectParameters.Direction = 4              # from the left (arrows) / bottom (the rest keeps its default)
        if ($e.name -eq "Raise arrow") { $eff.EffectParameters.Direction = 1 }
      }
    } catch {
      $problems += "slide $idx '$($e.name)' $($e.effect): $($_.Exception.Message)"
    }
  }
}

# ---- navigation dots jump to their slide
for ($i = 1; $i -le 7; $i++) {
  $target = $pres.Slides.Item($i)
  $sub = "{0},{1},{2}" -f $target.SlideID, $target.SlideIndex, "Slide $i"
  foreach ($sl in $pres.Slides) {
    if ($sl.SlideIndex -gt 7) { continue }
    try {
      $sh = $sl.Shapes.Item("Nav $i")
      $sh.ActionSettings.Item(1).Hyperlink.Address = ""
      $sh.ActionSettings.Item(1).Hyperlink.SubAddress = $sub
    } catch { $problems += "nav $i on slide $($sl.SlideIndex): $($_.Exception.Message)" }
  }
}

# ---- the demo slide: every step and the big button open the console on the right tab
$links = @(
  "$($base)?t=60#queue", "$($base)?t=90&msg=L003#journey", "$($base)#try", "$($base)?t=240#queue", "$($base)?t=480#compare"
)
$demo = $pres.Slides.Item(6)
for ($i = 1; $i -le 5; $i++) {
  foreach ($nm in @("Step $i", "Step $i text", "Step $i dot", "Step $i number")) {
    try {
      $demo.Shapes.Item($nm).ActionSettings.Item(1).Hyperlink.Address = $links[$i - 1]
      $demo.Shapes.Item($nm).ActionSettings.Item(1).Hyperlink.ScreenTip = "Opens the console in your browser"
    } catch { $problems += "demo link $nm : $($_.Exception.Message)" }
  }
}
foreach ($nm in @("Open button", "Open button text", "Console preview")) {
  try { $demo.Shapes.Item($nm).ActionSettings.Item(1).Hyperlink.Address = "$($base)?t=60#queue" } catch { $problems += "demo link $nm : $($_.Exception.Message)" }
}

# ---- small jump links between main and backup slides
function Add-Jump($slide, $label, $x, $y, $w, $toIndex) {
  $tb = $slide.Shapes.AddTextbox(1, $x, $y, $w, 20)
  $tb.Name = "Jump to $toIndex"
  $tb.TextFrame.TextRange.Text = $label
  $tb.TextFrame.TextRange.Font.Name = "Calibri"
  $tb.TextFrame.TextRange.Font.Size = 11
  $tb.TextFrame.TextRange.Font.Bold = -1
  $tb.TextFrame.TextRange.Font.Color.RGB = (0xF2 + 0xB8 * 256 + 0x4B * 65536)   # amber
  $tb.TextFrame.TextRange.ParagraphFormat.Alignment = 3
  $tb.TextFrame.WordWrap = -1
  $t = $pres.Slides.Item($toIndex)
  $tb.ActionSettings.Item(1).Hyperlink.SubAddress = "{0},{1},{2}" -f $t.SlideID, $t.SlideIndex, "Slide $toIndex"
}
Add-Jump $pres.Slides.Item(5) "Fairness, language and the floor  >" 400 342 300 9
Add-Jump $pres.Slides.Item(6) "If the demo fails  >" 400 342 300 8
Add-Jump $pres.Slides.Item(7) "Likely questions  >" 400 355 290 10
foreach ($k in 8, 9, 10) {
  Add-Jump $pres.Slides.Item($k) "<  Back to the close" 560 18 150 7
  $pres.Slides.Item($k).SlideShowTransition.Hidden = -1
}

$pres.SaveAs($Out, 24)
if ($Shots -ne "") { $pres.Export($Shots, "PNG", 1600, 900) }
$pres.SaveCopyAs((Join-Path $PSScriptRoot "NT-Triage-Deck-handout.pdf"), 32)
$count = 0
foreach ($sl in $pres.Slides) { $count += $sl.TimeLine.MainSequence.Count }
Write-Host "slides: $($pres.Slides.Count); animation effects: $count"
$pres.Close()
$app.Quit()
if ($problems.Count -gt 0) { Write-Host "PROBLEMS:"; $problems | ForEach-Object { Write-Host "  $_" } } else { Write-Host "no problems" }

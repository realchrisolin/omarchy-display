import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import "LayoutModel.js" as LayoutModel

// Always-on layout host, parented by DisplayPanel (bar widget).
// Not a separate plugin service: Qt reports "File name case mismatch" when
// createComponent loads through the realchrisolin.display symlink.
// Keeps physical monitors in the saved left-to-right order. Miracast virtual
// heads (persistent-miracast / HEADLESS*) are skipped in LayoutModel.isArrangeable.
// Holds apply during P2P/RTSP handshake. After each apply, re-places or parks
// the Extend head via miracast-ctl place-virtual-head.
Item {
  id: root

  // Must not participate in the Display bar-slot size. A non-zero host here
  // stretches the widget and steals drops on the left of the bar.
  width: 0
  height: 0
  implicitWidth: 0
  implicitHeight: 0
  // visible must stay true so Hyprland Connections and FileView still run.
  clip: true

  property var shell: null
  property var manifest: null
  property bool singletonOwner: true

  readonly property string orderPath: Quickshell.env("HOME") + "/.config/omarchy/monitor-layout.json"
  readonly property string statusPath: Quickshell.env("HOME") + "/.local/state/omarchy-miracast/status.json"
  readonly property string lockPath: Quickshell.env("HOME") + "/.local/state/omarchy-miracast/connecting.lock"
  readonly property string layoutNudgePath: Quickshell.env("HOME") + "/.local/state/omarchy-miracast/layout.nudge"
  readonly property string pluginDir: {
    var s = String(Qt.resolvedUrl("./"))
    if (s.indexOf("file://") === 0)
      s = decodeURIComponent(s.substring(7))
    while (s.length > 1 && s.charAt(s.length - 1) === "/")
      s = s.substring(0, s.length - 1)
    return s
  }
  readonly property string ctl: pluginDir + "/bin/miracast-ctl"

  function parseStatus() {
    try {
      return JSON.parse(statusFile.text() || "{}")
    } catch (e) {
      return {}
    }
  }

  // Last hl.device chunk applied. Same plan is not eval'd again.
  property string touchLuaApplied: ""
  property string touchLuaPending: ""
  property string touchLuaQueued: ""
  property bool touchReadPending: false
  property bool touchRetried: false

  function bindTouch() {
    if (!root.singletonOwner) return
    if (touchRead.running) {
      touchReadPending = true
      return
    }
    touchRead.running = true
  }

  function startTouchEval(lua) {
    if (!lua || lua === root.touchLuaApplied) return
    if (touchEval.running) {
      touchLuaQueued = lua
      return
    }
    touchLuaPending = lua
    touchEval.command = ["hyprctl", "eval", lua]
    touchEval.running = true
  }

  LayoutApplier {
    id: applier
    orderPath: root.orderPath
    manageExternalMode: true
    onApplied: {
      if (!placeProc.running)
        placeProc.running = true
    }
  }

  Timer {
    id: settle
    interval: 300
    repeat: false
    onTriggered: {
      if (!root.singletonOwner)
        return
      var st = root.parseStatus()
      if (LayoutModel.shouldHoldLayout(st, lockFile.loaded))
        return
      applier.apply()
    }
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (!root.singletonOwner) return
      if (!event || !event.name) return
      switch (String(event.name)) {
      case "monitoradded":
      case "monitoraddedv2":
      case "monitorremoved":
      case "monitorremovedv2":
      case "configreloaded":
        root.touchRetried = false
        root.bindTouch()
        settle.restart()
        break
      }
    }
  }

  FileView {
    path: root.orderPath
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: settle.restart()
  }

  FileView {
    id: statusFile
    path: root.statusPath
    watchChanges: true
    printErrors: false
    onFileChanged: {
      reload()
      // Handshake hold ends when phase becomes streaming. Without this, a
      // connect that parked the head never comes back to move eDP.
      settle.restart()
    }
  }

  FileView {
    id: lockFile
    path: root.lockPath
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
  }

  FileView {
    path: root.layoutNudgePath
    watchChanges: true
    printErrors: false
    onFileChanged: settle.restart()
  }

  Process {
    id: placeProc
    command: [root.ctl, "place-virtual-head"]
    stdout: StdioCollector { waitForEnd: true }
  }

  // HID nodes often appear just after the DRM connector.
  Timer {
    id: touchRetry
    interval: 2000
    repeat: false
    onTriggered: root.bindTouch()
  }

  Process {
    id: touchRead
    command: [root.pluginDir + "/bin/bind-touchscreens"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var plan = {}
        try { plan = JSON.parse(String(text || "")) } catch (e) { plan = {} }
        root.startTouchEval(String(plan.lua || ""))
        if (plan.retry === true && !root.touchRetried) {
          root.touchRetried = true
          touchRetry.restart()
        }
        if (root.touchReadPending) {
          root.touchReadPending = false
          root.bindTouch()
        }
      }
    }
  }

  // hl.device only. Does not move outputs.
  Process {
    id: touchEval
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        root.touchLuaApplied = root.touchLuaPending
        if (root.touchLuaQueued && root.touchLuaQueued !== root.touchLuaApplied) {
          var next = root.touchLuaQueued
          root.touchLuaQueued = ""
          root.startTouchEval(next)
        }
      }
    }
  }

  Component.onCompleted: {
    settle.restart()
    root.bindTouch()
  }
}

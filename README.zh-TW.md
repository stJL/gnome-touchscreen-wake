# GNOME 觸控喚醒（Linux）

一個事件驅動的小工具：當 GNOME 螢幕熄滅時，輕觸觸控螢幕即可喚醒畫面，同時保留 GNOME 原本的自動熄屏行為。

**已實測環境：** ASUS T101HA、Fedora Linux 43、GNOME Wayland，觸控裝置名稱為 `SIS0457:00 0457:11ED`。在這台設備上，觸控可以喚醒畫面，而且 GNOME 原本的 60 秒自動熄屏仍正常運作。

目前只在一台設備上驗證成功；其他裝置或 GNOME/Mutter 版本可能需要調整。

[English README](README.md)

## 運作方式

1. 直接讀取 Linux `evdev` 觸控事件，並依裝置名稱尋找 event 節點，不假設裝置永遠是 `/dev/input/event4`。
2. 收到 `BTN_TOUCH` 按下事件時，透過使用者工作階段的 D-Bus 查詢 Mutter `org.gnome.Mutter.DisplayConfig` 的 `PowerSaveMode`。
3. 只有當 Mutter 回報 `3`（顯示器關閉）時，才透過 `/dev/uinput` 建立暫時虛擬輸入裝置，送出 `KEY_WAKEUP` 按下及放開事件。
4. **不會呼叫 `org.gnome.ScreenSaver.SetActive false`**。在已測試的設備上，這個呼叫會導致自動熄屏停止，直到重新啟用螢幕保護狀態。

程式會阻塞等待輸入事件，不會不斷輪詢。只使用 Python 標準函式庫和 `gdbus`，不需要安裝 `evtest`、`python-evdev` 或 `ydotool`。

## 需求

- Linux，且 `/dev/uinput` 可用。
- Python 3、`gdbus`。
- GNOME/Mutter 工作階段在 session D-Bus 公開 `org.gnome.Mutter.DisplayConfig`。
- 觸控裝置會送出 `EV_KEY / BTN_TOUCH` 事件，且名稱符合預設值（或自行修改設定）。
- 登入桌面的使用者可以讀取觸控事件裝置，並寫入 `/dev/uinput`。

## 安裝（已測試的 Fedora/GNOME 環境）

在專案資料夾中，以一般桌面使用者身分執行；不要對整個指令加 `sudo`：

```bash
./install.sh
```

安裝程式會：

- 將程式安裝至 `~/.local/bin/touchscreen-wake`。
- 安裝 udev 規則，透過 `uaccess` 授予作用中的本機使用者工作階段存取指定觸控裝置與 `/dev/uinput` 的權限。
- 重新載入 udev 規則，並建立 GNOME 自動啟動項目 `~/.config/autostart/`。
- **不會安裝其他套件**。

自動啟動會在**下一次登入 GNOME 時**生效。要立即手動測試：

```bash
~/.local/bin/touchscreen-wake
```

手動以前景方式執行時，可按 `Ctrl+C` 停止。記錄寫在：

```text
~/.local/state/touchscreen-wake.log
```

## 檢查裝置權限

登入本機 GNOME 桌面後，以一般使用者執行（不要加 `sudo`）：

```bash
python3 - <<'PY'
import glob
import os
from pathlib import Path

touch = None
for entry in sorted(glob.glob('/sys/class/input/event*')):
    try:
        name = Path(entry, 'device', 'name').read_text().strip()
    except OSError:
        continue
    if name == 'SIS0457:00 0457:11ED':
        touch = '/dev/input/' + Path(entry).name
        break
if touch is None:
    raise SystemExit('找不到觸控裝置；請檢查 touchscreen-wake.py 的 TOUCH_DEVICE_NAME。')
for path, flags in ((touch, os.O_RDONLY | os.O_NONBLOCK), ('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)):
    fd = os.open(path, flags)
    os.close(fd)
    print('OK:', path)
PY
```

兩個裝置都應顯示 `OK`。若出現 `Permission denied`，確認你已登入本機 GNOME 桌面，並檢查 udev 規則的裝置名稱是否相符。`uaccess` ACL 是為作用中的本機工作階段授權；單靠 SSH 工作階段可能不會取得相同權限。

## 修改以支援其他觸控裝置

預設裝置名稱在 `touchscreen-wake.py` 的 `TOUCH_DEVICE_NAME`，以及 `udev/70-touchscreen-wake.rules` 中設定。可以這樣查看系統上的名稱：

```bash
for f in /sys/class/input/event*/device/name; do printf '%s: ' "$f"; cat "$f"; done
```

若要移植到其他裝置，請同時修改這兩處，再執行 `./install.sh`。是否成功仍取決於裝置驅動程式、Mutter 版本、顯示器電源狀態，以及系統是否接受 `KEY_WAKEUP`。

## 卸載

在專案資料夾以一般使用者執行：

```bash
./uninstall.sh
```

程式會在找到該使用者正在執行的 helper 時嘗試停止它，移除自動啟動項目及已安裝的程式，移除本專案的 udev 規則並重新載入規則。它會保留記錄檔，也不會卸載其他套件。

## 排錯

- **程式沒有顯示 Ready，或立即結束：** 查看 `~/.local/state/touchscreen-wake.log`。
- **`Permission denied`：** 以一般使用者執行上方權限檢查，確認 udev 規則和本機 GNOME 工作階段。
- **Mutter D-Bus 錯誤：** 確認程式是在 GNOME 使用者工作階段內執行，而不是以 root 執行；它需要使用者 session bus。
- **偵測到觸控但沒有喚醒：** 螢幕熄滅時，確認 `PowerSaveMode` 回報 `3`，並在目標設備上獨立測試 `KEY_WAKEUP`。此按鍵事件不保證能喚醒所有硬體和桌面環境。
- **喚醒後不再自動熄屏：** 確認沒有舊的測試腳本仍在執行並呼叫 `org.gnome.ScreenSaver.SetActive false`。本專案刻意避免此呼叫。

## 安全與隱私

程式會讀取觸控事件並建立虛擬輸入裝置，不會存取網路或傳送資料。udev 規則只針對指定名稱的觸控裝置及 `/dev/uinput`，使用 `uaccess`，而不是將使用者加入權限更廣的 `input` 群組。請在其他系統使用前先審閱程式碼與權限。

## 開發協作與 AI 協助

本專案在專案維護者與 OpenAI 的 ChatGPT 協助下完成。ChatGPT 協助研究可行的技術方案、撰寫與除錯 Python 主程式及相關設定／安裝腳本，並整理專案文件。

專案維護者提出問題與需求、提供硬體和系統資訊、在實體 ASUS T101HA 上執行指令與測試、回報錯誤及實際觀察結果，並驗證觸控喚醒與 GNOME 的 60 秒自動熄屏能在上述測試環境中正常共存。這段說明是為了透明揭露 AI 輔助開發的過程，並不表示所有程式碼都是由維護者獨立編寫。

目前只在上方描述的單一環境完成實機驗證。其他使用者請先審閱原始碼，並在自己的設備上調整及測試。OpenAI 與 ChatGPT 並非本 repository 的維護者，也不代表其認可或背書本專案。

## 參考資料

- [Linux 核心：uinput 模組](https://docs.kernel.org/input/uinput.html)
- [Linux 核心：輸入事件代碼（`KEY_WAKEUP`）](https://docs.kernel.org/input/event-codes.html)
- [GNOME：自動啟動應用程式](https://help.gnome.org/system-admin-guide/autostart-applications.html)

## 授權

MIT，詳見 [LICENSE](LICENSE)。

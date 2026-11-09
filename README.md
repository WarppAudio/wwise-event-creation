💡 Note: This instruction applies to source code only. If you prefer to use the pre-compiled .exe without setting up Python, grab the ready-to-use version from the [Releases page](https://github.com/WarppAudio/wwise-event-creation/releases/tag/Event-Creation-v2.0.0).

# 🎮 Wwise Event Creation Tool

Creates Play / Stop / Seek events for the objects selected in Wwise (via WAAPI),
optionally together with a new Work Unit or virtual folder, in a single operation.

## 📋 Requirements

- Windows with Wwise 2022.1 or newer (WAAPI enabled in *Project > User Preferences > Enable Wwise Authoring API*)
- Python 3.10 or newer, with the `py` launcher (installed by default with the python.org installer)

## 📦 Installation

1. Install the dependencies:

   ```
   py -3 -m pip install -r requirements.txt
   ```

2. If you want the tools to be available in every Wwise installation and project open the Wwise Add-ons folder: `%APPDATA%\Audiokinetic\Wwise\Add-ons` (create it if it does not exist). For other installation methods, watch [this video](https://youtu.be/7LpANxZD1cE?si=pCo8zNlsRYKFv5zi&t=60) or read [this document](https://www.audiokinetic.com/fr/library/edge/?source=SDK&id=defining_custom_commands.html)

3. Copy the files from this repository:

   - the `event-creation` folder into `Add-ons`,
   - `Event_Creation_Command.json` into `Add-ons\Commands` (create the `Commands` folder if needed).

   ![Installation](https://github.com/user-attachments/assets/1c020bc5-be76-4f5e-b0a1-acb6dc8acde5)

4. Restart Wwise.

## 🚀  Quick start

1. In Wwise, select the sounds / containers you want events for.
2. Right-click them and choose **WAAPI Tools > Event Creation**. The dot in the bottom-left corner of the tool turns green and shows the project name.
3. Pick the destination Work Unit or folder from the list (optionally create a new one with **+**).
4. Check the status bar (it tells you exactly what will be created and where) and click **Create Events**.
5. Review the log, then click **OK** to accept or **Undo** to revert the operation.

## 🧱  Project structure

```
Event_Creation_Command.json    Wwise command (goes to Add-ons\Commands)
event-creation/                the tool (goes to Add-ons)
  __main__.py                  entry point
  event_creation/core/         WAAPI + naming logic (no GUI imports)
  event_creation/ui/           PySide6 interface (theme, browser, settings panel‚Ä¶)
  resources/                   icons
  settings.json                tool settings
requirements.txt               Python dependencies
```

## ‚✨What's new in v2.0

- Full UI redesign (PySide6)
- Better browser: multi-word search matches names **and** paths
- **Undo** button that reverts the last operation (does not apply to newly created Work Units)

> **Note**: All settings are saved automatically whenever you change them in the tool's interface.

## 🖥️ Tool Documentation

### 🎯Main Interface

![Main window](https://github.com/user-attachments/assets/0f5044d1-98e8-42b2-a206-1d7297c7956f)

1. **Settings**

- Opens the Settings Panel (it slides in from the right), where you configure naming conventions, loop behaviour, fade and seek values, and the WAAPI connection.

2. **Filter**

- Narrows the destination list as you type.

- The filter text and the selected row are kept after a refresh and after creating events.

3. **Refresh Button**

- Reloads the list of Work Units and folders from Wwise. Use it after adding, renaming or deleting Work Units / folders directly in Wwise. If the tool is not connected (e.g. Wwise was started after the tool), it also connects to Wwise.

4. **List of Work Units and Folders**

- Shows every Work Unit and virtual folder from the **Events** hierarchy as one flat list: the name on top, the parent path below.

- Click a row to choose where the new events (or a new Work Unit / folder) will be created. The selected row is marked with a blue bar.

5. **+ (Create new work unit or folder)**

- Becomes active once a destination is selected.

- Opens a small menu with **Work unit** and **Folder**. See [Creating a new Work Unit or Folder](#-creating-a-new-work-unit-or-folder).

6. **Results Area**

- Empty until the first operation. After **Create Events** it shows the summary and the full log. See [After Create Events](#-after-create-events).

7. **Status Bar**

- **Connection dot**: green when connected to Wwise, red when not.

- **Project name**: the name of the connected Wwise project (`TEST_Wwise_2026` on the screenshot).

- **Live status**: describes exactly what will happen when you click Create Events, e.g. `5 events →  \Events\Default Work Unit\Weapons`. The event count follows your selection in Wwise in real time and already includes the extra Stop events for loops.

- When something is missing, a yellow hint tells you what to do:

  - `start Wwise and press ⟳ to connect`
  - `! select a destination in the list`
  - `! fix the highlighted fields in Settings`
  - `! fix the container name`
  - `no playable objects selected in Wwise`

- Errors from Wwise are shown here for a few seconds.

8. **Create Events**

- The main button. Creates events for the objects currently selected in Wwise (playable objects only: sounds, containers, ‚Ä¶; not events) inside the selected destination.

- Active only when the tool is connected, a destination is selected and all Settings fields are valid.

- What gets created for each selected object:

  | Selected object | Result |
  | --- | --- |
  | Regular sound | **Play** event (Play prefix + name) |
  | Loop (name contains a *Loop keyword*) | **Play** event with the loop suffix and a fade-in |
  | Loop + *Seek Action Loops* | the Play event also gets a **Seek** action (random start position) |
  | Loop + *Stop Events Loops* | an extra **Stop** event with a fade-out |

- Events whose name already exists anywhere in the project are skipped (and reported in the summary).

### ➕  Creating a new Work Unit or Folder

![New work unit or folder: menu](https://github.com/user-attachments/assets/9b9d084b-f130-4498-9abe-8a6d4b0605a0)

1. **Parent**

- Select the Work Unit or folder in which the new one should be created.

2. **+ Button**

- Click it to open the creation menu.

3. **Work unit / Folder**

- Choose what to create. The menu header shows the parent (`CREATE IN WEAPONS`).

![New work unit or folder: form](https://github.com/user-attachments/assets/236620d5-3523-4cf7-857d-5dd2c2be0e15)

1. **Parent Marker**

- The parent row turns green and shows `parent of new work unit` / `parent of new folder`.

- Click another row to change the parent while the card is open.

2. **New work unit / New folder Card**

- **‚úï** (or **Esc**) cancels.

- Nothing is created in Wwise yet: the Work Unit / folder is created together with the events when you click **Create Events**.

3. **Name**

- Pre-filled with `New_Work_Unit` / `New_Folder` and selected, so you can type over it right away.

- Checked live: the field turns red and an error appears below it when the name:

  - is empty,
  - contains a character Wwise does not accept: `\ / : * ? " < > |`,
  - is already taken (Work Unit names must be unique in the whole Events hierarchy; folder names must be unique within their parent).

- Create Events stays disabled until the name is valid.

4. **Will be created in**

- Preview of the full path of the new Work Unit / folder.

### ✅  After Create Events

![After Create Events](https://github.com/user-attachments/assets/2af7cc2e-6c0b-4ab3-b4a5-6470f14e2def)

1. **Summary**

- How many items were created and where (`3 created in \Events\Combat`).

- If needed, a yellow line below it reports:

  - `N skipped (already exist)`: events with names that already exist in the project,
  - `N sources without an expected keyword`: see *Expected source keywords* in Settings.

2. **Undo**

- Reverts the last operation in Wwise in one step (the created events and a new folder) and removes it from the log.

- Undo does not apply to newly created Work Units.

- It uses Wwise's own undo history, so use it **before** making other changes in Wwise; otherwise it reverts your latest change in Wwise instead.

3. **OK**

- Accepts the result and clears the log (back to the empty results area).

4. **Full Log**

- Lists every created item, marked by type:

  - `E` (blue): event
  - `W` (green): Work Unit
  - `F` (grey): folder

- **Click an entry to select it in the Wwise Project Explorer.**

### ⚙️ Settings Panel

> **Note**: Settings are stored in `event-creation/settings.json` (settings files from v1 keep working). Every change is saved immediately. An invalid value outlines the field in red and disables Create Events until it is fixed.

![Settings panel](https://github.com/user-attachments/assets/9eaf78b1-80a4-40db-a10b-c4d65352af51)

**NAMING**

1. **Capitalize Events / Lowercase Events**

- Letter case of event names (mutually exclusive; with both off, names keep their original case).

- Prefixes, the loop suffix (5) and words from the *Case change ignore list* (9) are never changed.

2. **Inherit name from parent**

- Inserts the name of the destination Work Unit / folder (or of the new one being created) right after the prefix: `Play_Weapons_Rifle_Shot`.

- Skipped when the prefix already uses the **$parent** wildcard.

3. **Play Events Prefix**

- Prefix for Play events, e.g. `Play` → `Play_Rifle_Shot` (the `_` is added automatically). Leave empty for no prefix.

- You can use the **$parent** wildcard to put the name of the destination Work Unit / folder anywhere in the prefix: `Play_$parent` → `Play_Weapons_Rifle_Shot`.

4. **Stop Events Prefix**

- Prefix for Stop events (created for loops only, see 10), e.g. `Stop` →  `Stop_Rain_Loop`.

- Same rules and **$parent** wildcard as the Play prefix. Use a different prefix than for Play events, otherwise the Stop event would get the same name and be skipped.

5. **Loop event suffix**

- Added at the end of event names created for loops.

- Loop keywords (7) found in the sound name are removed first, so `Rain_lp` becomes `Rain_Loop` (not `Rain_lp_Loop`).

6. **Expected source keywords**

- Comma-separated list of naming conventions that audio source file names should follow, e.g. `SFX, AMB, VO`.

- If a source file name contains none of them (case-sensitive), a warning is shown in the summary. Events are still created.

- Leave empty to skip the check.

7. **Loop keywords**

- Comma-separated list of keywords that mark a sound as a loop (case sensitive), e.g. `Loop, lp, Lp`. A keyword must be a separate part of the name (between `_` / `-` or at the start / end).

8. **Text to remove**

- Comma-separated list of text fragments removed from event names wherever they appear, even inside a word (case-sensitive), e.g. `SFX` turns `SFX_Rifle_Shot` into `Rifle_Shot`.

9. **Case change ignore list**

- Words that keep their letter case when Capitalize / Lowercase is on, e.g. `AMB, CMB` →  `CMB_Attack_Magic`.

- Use `#` for any number: `SFX#` matches `SFX1`, `SFX123`, etc.

**LOOPS**

10. **Stop Events Loops**

- Creates a Stop event for every loop, using the Stop prefix (4) and the Stop fade (13).

11. **Seek Action Loops**

- Adds a Seek action to the Play event of every loop, so the loop starts from a random position (14) instead of from the beginning.

12. **Play fade loop [s]**

- Fade-in time (in seconds) of the Play action for loops.

13. **Stop fade loop [s]**

- Fade-out time (in seconds) of the Stop action for loops.

14. **Seek values (Seek %, Min %, Max %)**

- Start position of the loop in percent (Seek %) and the random range around it (Min % / Max %).

**CONNECTION**

15. **Wwise WAAPI URL**

- Address of the Wwise Authoring API server. Leave empty to use the default `ws://127.0.0.1:8080/waapi`.

## 📄  License

MIT, see [LICENSE](LICENSE).

import os
import subprocess
import questionary
from prompt_toolkit import Application
from prompt_toolkit.application.run_in_terminal import in_terminal
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
import re


def choose_directory(start_dir: str | None = None) -> str:
    """Simple interactive browser to choose a directory."""
    current = os.path.abspath(start_dir or os.getcwd())
    while True:
        subdirs = sorted(
            d
            for d in os.listdir(current)
            if os.path.isdir(os.path.join(current, d))
        )
        choices = [
            questionary.Choice("[Diesen Ordner verwenden]", "__select__"),
            questionary.Choice("[..]", "__up__"),
        ] + [questionary.Choice(d + os.sep, d) for d in subdirs]

        selection = questionary.select(
            f"Ordner wählen: {current}", choices=choices
        ).ask()

        if selection == "__select__":
            return current
        if selection == "__up__":
            parent = os.path.dirname(current)
            current = parent if parent else current
        else:
            current = os.path.join(current, selection)


def select_files_with_segments(files):
    """Interactive selection of files with optional time ranges."""
    time_pattern = re.compile(r"^(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2}|\d+)$")
    entries = [
        {"file": f, "selected": False, "start": None, "end": None}
        for f in files
    ]
    index = 0

    async def ask_time(prompt: str) -> str:
        """Prompt for a time value and validate the format."""
        return await questionary.text(
            prompt,
            validate=lambda t: True
            if (not t.strip() or time_pattern.match(t.strip()))
            else "Format: HH:MM:SS or seconds",
        ).ask_async()

    def format_entry(e):
        mark = "[x]" if e["selected"] else "[ ]"
        segment = f"{e['start']} - {e['end']}" if e["start"] or e["end"] else "full"
        return f"{mark} {e['file']:<20} {segment}"

    def get_text():
        lines = [
            "Use ↑↓ to navigate, Space to select, 's' to set time, 'a' to select all, 'i' to invert, Enter to convert",
            "Times may be given in seconds or as HH:MM:SS",
            "",
        ]
        for i, e in enumerate(entries):
            prefix = "➜" if i == index else " "
            lines.append(f"{prefix} {format_entry(e)}")
        return "\n".join(lines)

    bindings = KeyBindings()

    @bindings.add("up")
    def _up(event):
        nonlocal index
        index = (index - 1) % len(entries)
        event.app.invalidate()

    @bindings.add("down")
    def _down(event):
        nonlocal index
        index = (index + 1) % len(entries)
        event.app.invalidate()

    @bindings.add("space")
    def _toggle(event):
        entries[index]["selected"] = not entries[index]["selected"]
        event.app.invalidate()

    @bindings.add("a")
    def _select_all(event):
        for e in entries:
            e["selected"] = True
        event.app.invalidate()

    @bindings.add("i")
    def _invert(event):
        for e in entries:
            e["selected"] = not e["selected"]
        event.app.invalidate()

    @bindings.add("s")
    def _set_time(event):
        async def ask():
            async with in_terminal():
                start = await ask_time(
                    "Startzeit (Sekunden oder HH:MM:SS, leer = Anfang):"
                )
                end = await ask_time(
                    "Endzeit (Sekunden oder HH:MM:SS, leer = Ende):"
                )
            entries[index]["start"] = start.strip() or None
            entries[index]["end"] = end.strip() or None
            event.app.invalidate()

        event.app.create_background_task(ask())

    @bindings.add("enter")
    def _done(event):
        event.app.exit(result=entries)

    body = Window(content=FormattedTextControl(get_text), always_hide_cursor=True)
    layout = Layout(body)
    app = Application(layout=layout, key_bindings=bindings, full_screen=False)
    return app.run()


if __name__ == "__main__":
    input_directory = choose_directory()
    output_directory = os.path.join(input_directory, "mp3")
    os.makedirs(output_directory, exist_ok=True)

    mkv_files = [f for f in os.listdir(input_directory) if f.lower().endswith(".mkv")]
    if not mkv_files:
        print("❌ Keine .mkv-Dateien gefunden.")
        raise SystemExit

    selections = select_files_with_segments(mkv_files)
    chosen = [s for s in selections if s["selected"]]
    if not chosen:
        print("❌ Keine Dateien ausgewählt. Abbruch.")
        raise SystemExit

    for entry in chosen:
        input_path = os.path.join(input_directory, entry["file"])
        output_filename = os.path.splitext(entry["file"])[0] + ".mp3"
        output_path = os.path.join(output_directory, output_filename)

        command = ["ffmpeg", "-i", input_path]
        if entry["start"]:
            command += ["-ss", entry["start"]]
        if entry["end"]:
            command += ["-to", entry["end"]]
        command += ["-vn", "-acodec", "libmp3lame", "-q:a", "2", output_path]

        print(f"🎵 Konvertiere: {entry['file']} → mp3/{output_filename}")
        subprocess.run(command)

    print(f"\n✅ Fertig. MP3-Dateien gespeichert in: {output_directory}")

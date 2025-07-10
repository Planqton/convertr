import os
import subprocess
import questionary

input_directory = os.getcwd()
output_directory = os.path.join(input_directory, "mp3")
os.makedirs(output_directory, exist_ok=True)

# Liste aller .mkv-Dateien
mkv_files = [f for f in os.listdir(input_directory) if f.lower().endswith(".mkv")]

if not mkv_files:
    print("❌ Keine .mkv-Dateien gefunden.")
    exit()

# Erste Auswahl: Dateien ankreuzen
selected_files = questionary.checkbox(
    "Welche Dateien möchtest du konvertieren?",
    choices=mkv_files
).ask()

if not selected_files:
    print("❌ Keine Dateien ausgewählt. Abbruch.")
    exit()

# Optional: Für jede ausgewählte Datei Zeitsegment angeben
file_segments = {}  # filename → (start, end)

for f in selected_files:
    use_segment = questionary.confirm(
        f"Möchtest du bei '{f}' ein Zeitsegment eingeben?"
    ).ask()

    if use_segment:
        start = questionary.text("Startzeit (z. B. 00:00:30):").ask().strip()
        end = questionary.text("Endzeit (z. B. 00:01:45):").ask().strip()
        file_segments[f] = (start, end)
    else:
        file_segments[f] = (None, None)

# Konvertieren
for filename in selected_files:
    input_path = os.path.join(input_directory, filename)
    output_filename = os.path.splitext(filename)[0] + ".mp3"
    output_path = os.path.join(output_directory, output_filename)

    start_time, end_time = file_segments.get(filename, (None, None))

    command = ["ffmpeg", "-i", input_path]

    if start_time:
        command += ["-ss", start_time]
    if end_time:
        command += ["-to", end_time]

    command += ["-vn", "-acodec", "libmp3lame", "-q:a", "2", output_path]

    print(f"🎵 Konvertiere: {filename} → mp3/{output_filename}")
    subprocess.run(command)

print("\n✅ Fertig. MP3-Dateien gespeichert in: ./mp3/")

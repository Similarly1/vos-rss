import sys
import io

path = r"C:\Users\adrie\.gemini\antigravity\brain\8417975a-acf0-4985-be42-1d561eedce66\task.md"

with io.open(path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("`[ ]` Mettre à jour `articles`", "`[x]` Mettre à jour `articles`")
content = content.replace("`[ ]` Mettre à jour `clustering.py`", "`[x]` Mettre à jour `clustering.py`")

with io.open(path, "w", encoding="utf-8") as f:
    f.write(content)

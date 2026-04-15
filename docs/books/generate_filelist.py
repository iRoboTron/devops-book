#!/usr/bin/env python3
"""
Генерирует files.json со списком .md файлов.

Локальный запуск (из docs/books/):
    python3 generate_filelist.py

Папки с курсами ищутся прямо в директории скрипта (linux-for-devops, docker-devops и т.д.).
На сервере структура: devops/books/linux-for-devops/ — скрипт запускается из devops/books/.
"""
import os
import sys
import json

# Директория, в которой лежат папки курсов
base = os.path.dirname(os.path.abspath(__file__))

# Можно передать путь явно: python3 generate_filelist.py /path/to/courses
scan_dir = sys.argv[1] if len(sys.argv) > 1 else base

courses = {}
for entry in sorted(os.listdir(scan_dir)):
    course_path = os.path.join(scan_dir, entry)
    if not os.path.isdir(course_path):
        continue
    files = sorted(
        [f for f in os.listdir(course_path) if f.endswith('.md')],
        key=lambda x: [int(c) if c.isdigit() else c
                       for c in x.replace('.', ' ').split()]
    )
    if files:
        courses[entry] = files

out = os.path.join(base, "files.json")
with open(out, 'w', encoding='utf-8') as f:
    json.dump({"courses": courses}, f, ensure_ascii=False, indent=2)

print(f"OK: {out}")
for k, v in courses.items():
    print(f"  {k}: {len(v)} файлов")

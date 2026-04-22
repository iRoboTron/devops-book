#!/usr/bin/env python3
import os
import json

print("Content-Type: application/json")
print("Access-Control-Allow-Origin: *")
print()

base = os.path.dirname(os.path.abspath(__file__))
books_dir = os.path.join(base, "books")

courses = {}
if os.path.isdir(books_dir):
    for course in sorted(os.listdir(books_dir)):
        course_path = os.path.join(books_dir, course)
        if os.path.isdir(course_path):
            files = sorted(
                [f for f in os.listdir(course_path) if f.endswith('.md')],
                key=lambda x: [int(c) if c.isdigit() else c for c in x.replace('.', ' ').split()]
            )
            if files:
                courses[course] = files

print(json.dumps({"courses": courses}))

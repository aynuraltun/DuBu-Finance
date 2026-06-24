import os
import re

# Emoji regex pattern
emoji_pattern = re.compile(
    r'[\U00010000-\U0010ffff\u2600-\u27bf]',
    re.UNICODE
)

project_dir = "/Users/aynuraltun/Desktop/dubu haziran"
exempt_dirs = {".venv", ".git", ".gemini"}

def scan():
    results = []
    for root, dirs, files in os.walk(project_dir, followlinks=True):
        # filter out hidden/system dirs
        dirs[:] = [d for d in dirs if d not in exempt_dirs and not d.startswith('.')]
        for file in files:
            if file.endswith(('.html', '.py', '.js', '.css', '.md')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    for idx, line in enumerate(lines, 1):
                        matches = emoji_pattern.findall(line)
                        if matches:
                            clean_matches = [m for m in matches if ord(m) > 1000 or ord(m) in (9728, 9729, 9742, 9745, 9749, 9757, 9824, 9827, 9829, 9830, 9889, 9917, 9918, 9924, 9925, 9934, 9940, 9962, 9970, 9971, 9973, 9978, 9981, 9986, 9989, 9992, 9993, 9994, 9995, 9996, 9999, 10002, 10004, 10006, 10024, 10060, 10067, 10068, 10069, 10071, 10084, 10133, 10134, 10135, 10145, 10160, 10175, 10548, 10549, 11088, 11093, 12336, 12349, 12951, 12953)]
                            if clean_matches:
                                results.append(f"{os.path.relpath(filepath, project_dir)}:{idx}: {''.join(clean_matches)} -> {line.strip()}")
                except Exception as e:
                    pass
    
    with open(os.path.join(project_dir, "scratch/emojis_found.txt"), "w", encoding="utf-8") as out:
        out.write("\n".join(results))

if __name__ == "__main__":
    scan()

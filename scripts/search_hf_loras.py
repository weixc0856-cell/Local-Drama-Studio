import urllib.request
import json

queries = ["flux+amateur", "flux+film", "flux+photo", "flux+raw"]
for q in queries:
    req = urllib.request.Request(
        f"https://huggingface.co/api/models?search={q}&limit=5&sort=downloads",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"--- Query: {q} ---")
            for d in data[:5]:
                print(f"{d['id']} | downloads: {d.get('downloads', 0)} | likes: {d.get('likes', 0)}")
    except Exception as e:
        print("Error:", e)

import json
import docx2txt
import sys

def read_json_summary(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("=== JSON Summary ===")
    if isinstance(data, dict):
        for k, v in data.items():
            print(f"Key: {k}, Type: {type(v).__name__}")
            if isinstance(v, list) and len(v) > 0:
                print(f"  First element type in {k}: {type(v[0]).__name__}")
                if isinstance(v[0], dict):
                    print(f"  Keys in first element: {list(v[0].keys())}")
    
def dict2text(path):
    text = docx2txt.process(path)
    with open("docx_content.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("Wrote docx_content.txt")

if __name__ == "__main__":
    if sys.argv[1] == 'docx':
        dict2text(sys.argv[2])
    elif sys.argv[1] == 'json':
        read_json_summary(sys.argv[2])

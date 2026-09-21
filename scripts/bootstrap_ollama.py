"""Optional Windows CPU-only Ollama bootstrap from the official release archive.

Run: python -m pip install remotezip; python scripts/bootstrap_ollama.py
Extracts selected original ZIP entries (CRC checked by zipfile), without GPU libraries.
No system installation, PATH changes, or services. Start with start_ollama.ps1.
"""
from pathlib import Path
from remotezip import RemoteZip, RemoteFetcher

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '.cache/ollama-runtime'
URL = 'https://github.com/ollama/ollama/releases/download/v0.34.2/ollama-windows-amd64.zip'
SIZE = 1460928014

class Fetcher(RemoteFetcher):
    # GitHub HEAD without redirects reports the redirect body's length.
    def get_file_size(self):
        return SIZE

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    with RemoteZip(URL, fetcher=Fetcher, support_suffix_range=False, timeout=120) as archive:
        for item in archive.infolist():
            if item.is_dir() or any(x in item.filename.lower() for x in ('cuda_v', 'vulkan')):
                continue
            target = (DEST / item.filename).resolve()
            if not target.is_relative_to(DEST.resolve()):
                raise ValueError('Archive path leaves runtime directory')
            if target.exists() and target.stat().st_size == item.file_size:
                continue
            archive.extract(item, DEST)
            print('Extracted', item.filename, flush=True)
    print('CPU runtime ready at', DEST)

if __name__ == '__main__':
    main()

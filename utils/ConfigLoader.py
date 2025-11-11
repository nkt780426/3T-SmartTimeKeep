import yaml
import os

class ConfigLoader:
    def __init__(self, path: str):
        self.path = path
        self.data = {}

        # Nếu file tồn tại, load nó
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.data = yaml.safe_load(f) or {}

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value
        self.save_config()

    def save_config(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.data, f, allow_unicode=True)

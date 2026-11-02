# runtime/

本目录存放**本机生成引擎**，不进入 Git（见 `.gitignore`）。

```text
runtime/
└─ ComfyUI/
   ├─ .venv/                 # PyTorch XPU + ComfyUI + GGUF 节点（独立于根 .venv）
   ├─ custom_nodes/
   │  └─ ComfyUI-GGUF/
   ├─ extra_model_paths.yaml # 由 setup.ps1 从 config/ 复制
   └─ main.py
```

创建：

```powershell
scripts\setup.ps1 -WithComfyUI
```

不要在这里放业务代码、模型权重或短剧产物。模型统一在 `D:\AI\models`。

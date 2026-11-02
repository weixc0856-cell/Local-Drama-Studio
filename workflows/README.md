# ComfyUI 工作流

这里只放 **API 格式** 工作流（ComfyUI 菜单 `Workflow → Export (API)`），不放 UI 格式。

## 命名

| 文件 | 用途 | 阶段 |
|---|---|---|
| `flux_character_api.json` | 人物定妆参考图 | R1 |
| `flux_scene_api.json` | 场景 / 道具参考图 | R1 |
| `flux_keyframe_api.json` | 分镜首帧（可带参考图） | R1/R5 |
| `wan_t2v_api.json` | 文生视频 | R2 |
| `wan_i2v_api.json` | 首帧图生视频 | R2 |

## 占位符

调度层对工作流 JSON 做**树遍历替换**，只替换字符串值，不拼接 JSON 文本。

约定占位符：

```text
{{positive_prompt}}   {{negative_prompt}}   {{seed}}
{{width}}             {{height}}            {{frames}}
{{steps}}             {{cfg}}               {{fps}}
{{input_image}}       {{filename_prefix}}
```

示例：

```json
{
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "seed": "{{seed}}",
      "steps": "{{steps}}",
      "cfg": "{{cfg}}",
      "positive": ["6", 0]
    }
  }
}
```

数值占位符在替换时会转成 JSON number，不是字符串。

## 版本登记

每个工作流旁放一个同名 `.meta.json`，记录：

```json
{
  "comfyui_commit": "…",
  "custom_nodes": { "ComfyUI-GGUF": "…" },
  "models": {
    "unet": "flux-2-klein-4b-Q4_K_M.gguf",
    "unet_sha256": "…",
    "text_encoder": "qwen_3_4b.safetensors",
    "vae": "flux2-vae.safetensors"
  },
  "verified_at": "2026-11-02",
  "status": "PASS_VERIFIED"
}
```

模型或节点升级后，旧工作流必须重新走 R0/R1 验收；未验证的工作流不得进入流水线。
